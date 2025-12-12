from django.contrib import admin
from .models import EmotionalCheckIn, CopingStrategy

@admin.register(EmotionalCheckIn)
class EmotionalCheckInAdmin(admin.ModelAdmin):
    list_display = ['user', 'primary_emotion', 'intensity', 'created_at']
    list_filter = ['primary_emotion', 'intensity', 'created_at', 'physical_symptoms']
    search_fields = ['user__username', 'notes', 'trigger_description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Emotional State', {
            'fields': ('user', 'primary_emotion', 'secondary_emotions', 'intensity')
        }),
        ('Physical Symptoms', {
            'fields': ('physical_symptoms',)
        }),
        ('Context & Triggers', {
            'fields': ('trigger_description', 'context_tags')
        }),
        ('Coping & Reflection', {
            'fields': ('coping_strategies_used', 'coping_effectiveness', 'notes', 'key_insight')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(CopingStrategy)
class CopingStrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy_type', 'difficulty_level', 'estimated_minutes']
    list_filter = ['strategy_type', 'difficulty_level', 'coding_integration']
    search_fields = ['name', 'description', 'target_emotions']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'strategy_type', 'target_emotions')
        }),
        ('Implementation', {
            'fields': ('estimated_minutes', 'difficulty_level')
        }),
        ('Coding Integration', {
            'fields': ('coding_integration', 'coding_language', 'coding_template')
        }),
        ('Therapeutic Guidance', {
            'fields': ('instructions', 'tips_for_success', 'common_challenges')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )