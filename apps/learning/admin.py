from django.contrib import admin
from .models import LearningPath, MicroActivity, UserProgress

class MicroActivityInline(admin.TabularInline):
    model = MicroActivity
    extra = 0
    fields = ('title', 'difficulty_level', 'estimated_minutes', 'order_position')
    show_change_link = True

@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ('name', 'difficulty_level', 'target_language', 'estimated_total_hours', 'is_active')
    list_filter = ('difficulty_level', 'target_language', 'is_active')
    search_fields = ('name', 'description')
    inlines = [MicroActivityInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'difficulty_level', 'target_language')
        }),
        ('Therapeutic Design', {
            'fields': ('recommended_for_profiles', 'estimated_total_hours', 'max_daily_minutes')
        }),
        ('Structure', {
            'fields': ('modules',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ('slug', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(MicroActivity)
class MicroActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'activity_type', 'difficulty_level', 'estimated_minutes', 'is_published')
    list_filter = ('activity_type', 'therapeutic_focus', 'difficulty_level', 'primary_language', 'is_published')
    search_fields = ('title', 'description', 'learning_objectives')
    readonly_fields = ('slug', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slug', 'short_description', 'full_description')
        }),
        ('Classification', {
            'fields': ('activity_type', 'therapeutic_focus', 'difficulty_level', 'primary_language', 'tech_stack')
        }),
        ('Time & Access', {
            'fields': ('estimated_minutes', 'no_time_limit', 'infinite_retries', 'skip_allowed', 'gentle_feedback')
        }),
        ('Content', {
            'fields': ('learning_objectives', 'prerequisites', 'starter_code', 'solution_code', 'test_cases')
        }),
        ('Therapeutic Support', {
            'fields': ('therapeutic_instructions', 'coping_suggestions', 'success_affirmations')
        }),
        ('Media & Resources', {
            'fields': ('video_url', 'documentation_url', 'additional_resources'),
            'classes': ('collapse',)
        }),
        ('Organization', {
            'fields': ('learning_path', 'order_position')
        }),
        ('Status', {
            'fields': ('validation_type', 'is_published', 'created_at', 'updated_at')
        }),
    )
    prepopulated_fields = {'slug': ('title',)}

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'status', 'completion_time', 'self_assessment')
    list_filter = ('status', 'activity__difficulty_level', 'completion_time')
    search_fields = ('user__username', 'activity__title', 'reflection_notes')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Progress', {
            'fields': ('user', 'activity', 'status', 'start_time', 'completion_time', 'time_spent_seconds')
        }),
        ('Attempts', {
            'fields': ('attempts', 'successful_attempts', 'submitted_code', 'code_output', 'errors')
        }),
        ('Emotional Tracking', {
            'fields': ('emotional_state_before', 'emotional_state_after',
                      'stress_level_before', 'stress_level_after',
                      'confidence_before', 'confidence_after')
        }),
        ('Reflection', {
            'fields': ('self_assessment', 'reflection_notes', 'what_went_well', 'challenges_faced')
        }),
        ('Therapeutic', {
            'fields': ('coping_strategies_used', 'breakthrough_notes', 'therapist_feedback')
        }),
        ('Metrics', {
            'fields': ('code_quality_score', 'efficiency_score'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )