# social/admin.py
"""
Admin configuration for therapeutic social app
"""

from django.contrib import admin
from .models import (
    GentleInteraction, Achievement, UserAchievement,
    SupportCircle, CircleMembership
)


@admin.register(GentleInteraction)
class GentleInteractionAdmin(admin.ModelAdmin):
    list_display = ['title', 'interaction_type', 'sender', 'visibility', 'created_at']
    list_filter = ['interaction_type', 'visibility', 'created_at']
    search_fields = ['title', 'message', 'sender__username']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {
            'fields': ('sender', 'recipient', 'title', 'message')
        }),
        ('Therapeutic Info', {
            'fields': ('interaction_type', 'therapeutic_intent', 'therapeutic_impact_score')
        }),
        ('Visibility & Settings', {
            'fields': ('visibility', 'allow_replies', 'is_pinned', 'anonymous')
        }),
        ('Stats', {
            'fields': ('likes_count', 'views_count', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'is_active', 'total_earners']
    list_filter = ['tier', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['total_earners']


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'earned_at', 'shared_publicly']
    list_filter = ['achievement__tier', 'shared_publicly', 'earned_at']
    search_fields = ['user__username', 'achievement__name']
    readonly_fields = ['earned_at']


@admin.register(SupportCircle)
class SupportCircleAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_public', 'active_members', 'max_members']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'description', 'focus_areas']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CircleMembership)
class CircleMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'circle', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__username', 'circle__name']
    readonly_fields = ['joined_at']