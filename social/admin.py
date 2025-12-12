from django.contrib import admin
from .models import GentleInteraction, Achievement, UserAchievement, SupportCircle, CircleMembership

@admin.register(GentleInteraction)
class GentleInteractionAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'interaction_type', 'visibility', 'likes_count', 'created_at', 'is_moderated')
    list_filter = ('interaction_type', 'visibility', 'is_pinned', 'is_moderated', 'created_at')
    search_fields = ('message', 'sender__username', 'recipient__username')
    readonly_fields = ('uuid', 'likes_count', 'replies_count', 'shares_count', 'created_at', 'updated_at')
    fieldsets = (
        ('Content', {
            'fields': ('uuid', 'interaction_type', 'sender', 'recipient', 'title', 'message')
        }),
        ('Settings', {
            'fields': ('visibility', 'is_pinned', 'allow_replies', 'therapeutic_intent', 'expected_response_time')
        }),
        ('Engagement', {
            'fields': ('likes_count', 'replies_count', 'shares_count'),
            'classes': ('collapse',)
        }),
        ('Moderation', {
            'fields': ('is_moderated', 'moderator_notes', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class UserAchievementInline(admin.TabularInline):
    model = UserAchievement
    extra = 0
    readonly_fields = ('earned_at',)
    can_delete = False

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'requirement_type', 'requirement_value', 'is_active')
    list_filter = ('tier', 'requirement_type', 'is_active')
    search_fields = ('name', 'description')
    inlines = [UserAchievementInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'tier', 'icon_name', 'color')
        }),
        ('Requirements', {
            'fields': ('requirement_type', 'requirement_value', 'requirement_data')
        }),
        ('Therapeutic Content', {
            'fields': ('therapeutic_message', 'reflection_prompt')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )
    readonly_fields = ('created_at',)

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at', 'shared_publicly')
    list_filter = ('achievement__tier', 'shared_publicly', 'earned_at')
    search_fields = ('user__username', 'achievement__name', 'reflection_notes')
    readonly_fields = ('earned_at',)
    fieldsets = (
        (None, {
            'fields': ('user', 'achievement', 'earned_at')
        }),
        ('Context', {
            'fields': ('context_data', 'reflection_notes')
        }),
        ('Sharing', {
            'fields': ('shared_publicly',)
        }),
    )

class CircleMembershipInline(admin.TabularInline):
    model = CircleMembership
    extra = 0
    readonly_fields = ('joined_at', 'last_active')
    can_delete = False

@admin.register(SupportCircle)
class SupportCircleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_public', 'active_members', 'max_members', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'description', 'focus_areas')
    inlines = [CircleMembershipInline]
    readonly_fields = ('total_interactions', 'active_members', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'max_members', 'is_public', 'join_code')
        }),
        ('Focus & Guidelines', {
            'fields': ('focus_areas', 'community_guidelines', 'meeting_schedule')
        }),
        ('Statistics', {
            'fields': ('total_interactions', 'active_members'),
            'classes': ('collapse',)
        }),
        ('Management', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

@admin.register(CircleMembership)
class CircleMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'circle', 'role', 'joined_at', 'support_given')
    list_filter = ('role', 'circle', 'joined_at')
    search_fields = ('user__username', 'circle__name')
    readonly_fields = ('joined_at', 'last_active')
    fieldsets = (
        (None, {
            'fields': ('circle', 'user', 'role')
        }),
        ('Activity', {
            'fields': ('joined_at', 'last_active', 'support_given', 'support_received')
        }),
        ('Preferences', {
            'fields': ('notification_preferences',),
            'classes': ('collapse',)
        }),
    )