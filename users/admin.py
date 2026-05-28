from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import TherapeuticUser
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.urls import path
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.contrib.admin import SimpleListFilter
from django.db import models

@admin.register(TherapeuticUser)
class TherapeuticUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'emotional_profile', 'gentle_mode', 'current_stress_level', 'is_online', 'is_staff')
    list_filter = ('emotional_profile', 'gentle_mode', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Therapeutic Settings', {
            'fields': ('emotional_profile', 'learning_style', 'daily_time_limit', 
                      'gentle_mode', 'hide_progress', 'allow_anonymous',
                      'current_stress_level', 'avatar_color', 'custom_affirmation')
        }),
        ('Progress Tracking', {
            'fields': ('total_learning_minutes', 'consecutive_days', 
                      'breakthrough_moments', 'preferred_learning_hours')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Therapeutic Settings', {
            'fields': ('emotional_profile', 'gentle_mode', 'daily_time_limit'),
        }),
    )

    actions = ['unlock_accounts']

    def is_online(self, obj):
        """Check whether the user has an active session."""
        # Cache the set of online user ids for the admin instance to avoid N+1 session decoding
        online_ids = getattr(self, '_cached_online_user_ids', None)
        if online_ids is None:
            online_ids = set()
            sessions = Session.objects.filter(expire_date__gte=timezone.now())[:2000]
            for session in sessions:
                try:
                    data = session.get_decoded()
                    uid = data.get('_auth_user_id')
                    if uid:
                        online_ids.add(int(uid))
                except Exception:
                    continue
            self._cached_online_user_ids = online_ids

        return obj.id in online_ids
    is_online.boolean = True
    is_online.short_description = 'Online'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('online-users/', self.admin_site.admin_view(self.online_users_view), name='users_online'),
        ]
        return custom_urls + urls

    def online_users_view(self, request):
        """Admin view that lists currently online users."""
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_ids = set()
        for session in sessions:
            try:
                data = session.get_decoded()
                uid = data.get('_auth_user_id')
                if uid:
                    user_ids.add(int(uid))
            except Exception:
                continue

        users = TherapeuticUser.objects.filter(id__in=user_ids)

        context = dict(
            self.admin_site.each_context(request),
            users=users,
            title='Online users',
        )
        return TemplateResponse(request, 'admin/online_users.html', context)

    def unlock_accounts(self, request, queryset):
        """Admin action to clear therapeutic account locks for selected users."""
        # Restrict unlock action to superusers only
        if not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('Only superusers may unlock accounts')

        updated = queryset.update(account_locked_until=None)
        self.message_user(request, f"Unlocked {updated} accounts.")

        # Audit log for unlock action
        try:
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType

            ct = ContentType.objects.get_for_model(TherapeuticUser)
            for user in queryset:
                LogEntry.objects.log_action(
                    user_id=request.user.pk,
                    content_type_id=ct.pk,
                    object_id=user.pk,
                    object_repr=str(user),
                    action_flag=CHANGE,
                    change_message='Unlocked account via admin action'
                )
        except Exception:
            pass
    unlock_accounts.short_description = 'Unlock selected user accounts'


class AccountLockedFilter(SimpleListFilter):
    title = 'Account locked'
    parameter_name = 'account_locked'

    def lookups(self, request, model_admin):
        return (
            ('locked', 'Locked'),
            ('unlocked', 'Unlocked'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'locked':
            return queryset.filter(account_locked_until__isnull=False).filter(account_locked_until__gt=timezone.now())
        if self.value() == 'unlocked':
            return queryset.filter(models.Q(account_locked_until__isnull=True) | models.Q(account_locked_until__lte=timezone.now()))
        return queryset


class OnlineFilter(SimpleListFilter):
    title = 'Online'
    parameter_name = 'is_online'

    def lookups(self, request, model_admin):
        return (
            ('online', 'Online'),
            ('offline', 'Offline'),
        )

    def queryset(self, request, queryset):
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_ids = set()
        for session in sessions:
            try:
                data = session.get_decoded()
                uid = data.get('_auth_user_id')
                if uid:
                    user_ids.add(int(uid))
            except Exception:
                continue

        if self.value() == 'online':
            return queryset.filter(id__in=user_ids)
        if self.value() == 'offline':
            return queryset.exclude(id__in=user_ids)
        return queryset

# Add filters to TherapeuticUserAdmin
TherapeuticUserAdmin.list_filter = list(TherapeuticUserAdmin.list_filter) + [AccountLockedFilter, OnlineFilter]