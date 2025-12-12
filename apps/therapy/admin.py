from django.contrib import admin
from .models import EmotionalCheckIn, CopingStrategy

@admin.register(EmotionalCheckIn)
class EmotionalCheckInAdmin(admin.ModelAdmin):
    list_display = ('user', 'primary_emotion', 'intensity', 'created_at')
    list_filter = ('primary_emotion', 'intensity', 'created_at')
    search_fields = ('user__username', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'primary_emotion', 'secondary_emotions', 'intensity')
        }),
        ('Physical & Context', {
            'fields': ('physical_symptoms', 'trigger_description', 'context_tags')
        }),
        ('Coping & Reflection', {
            'fields': ('coping_strategies_used', 'coping_effectiveness', 'notes', 'key_insight')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CopingStrategy)
class CopingStrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'strategy_type', 'difficulty_level', 'estimated_minutes', 'is_active')
    list_filter = ('strategy_type', 'difficulty_level', 'coding_integration', 'is_active')
    search_fields = ('name', 'description', 'target_emotions')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'strategy_type', 'target_emotions')
        }),
        ('Implementation', {
            'fields': ('estimated_minutes', 'difficulty_level', 'coding_integration')
        }),
        ('Coding Integration', {
            'fields': ('coding_language', 'coding_template'),
            'classes': ('collapse',)
        }),
        ('Guidance', {
            'fields': ('instructions', 'tips_for_success', 'common_challenges')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )