# learning/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
import json
from .models import LearningPath, MicroActivity, UserProgress

class MicroActivityInline(admin.TabularInline):
    """Inline for activities in learning paths"""
    model = MicroActivity
    extra = 1
    fields = ['title', 'activity_type', 'difficulty_level', 'order_position', 'is_published']
    ordering = ['order_position']


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    """Admin interface for learning paths"""
    list_display = ['name', 'difficulty_level_display', 'target_language', 
                    'activity_count', 'is_active', 'created_at']
    list_filter = ['difficulty_level', 'target_language', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ['name']}
    inlines = [MicroActivityInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'difficulty_level')
        }),
        ('Technical Details', {
            'fields': ('target_language', 'estimated_total_hours', 'max_daily_minutes')
        }),
        ('Therapeutic Design', {
            'fields': ('recommended_for_profiles', 'modules'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_active',),
            'classes': ('collapse',)
        }),
    )
    
    def difficulty_level_display(self, obj):
        """Display difficulty with emoji"""
        emoji_map = {
            1: '🌱', 2: '🌿', 3: '🌳', 4: '🏔️', 5: '🚀'
        }
        return f"{emoji_map.get(obj.difficulty_level, '')} {obj.get_difficulty_level_display()}"
    difficulty_level_display.short_description = 'Difficulty'
    
    def activity_count(self, obj):
        """Count activities in this path"""
        return obj.activities.count()
    activity_count.short_description = 'Activities'


@admin.register(MicroActivity)
class MicroActivityAdmin(admin.ModelAdmin):
    """Admin interface for micro activities"""
    list_display = ['title', 'activity_type', 'therapeutic_focus', 
                    'difficulty_display', 'estimated_minutes', 
                    'learning_path_link', 'is_published']
    list_filter = ['activity_type', 'therapeutic_focus', 'difficulty_level', 
                   'primary_language', 'is_published', 'learning_path']
    search_fields = ['title', 'short_description', 'full_description']
    prepopulated_fields = {'slug': ['title']}
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'short_description', 'full_description')
        }),
        ('Therapeutic Design', {
            'fields': ('activity_type', 'therapeutic_focus', 'difficulty_level')
        }),
        ('Technical Details', {
            'fields': ('primary_language', 'tech_stack', 'estimated_minutes')
        }),
        ('Therapeutic Features', {
            'fields': ('no_time_limit', 'infinite_retries', 'skip_allowed', 'gentle_feedback'),
            'classes': ('collapse',)
        }),
        ('Learning Content', {
            'fields': ('learning_objectives', 'prerequisites', 'starter_code', 
                      'solution_code', 'test_cases', 'validation_type')
        }),
        ('Multimedia Resources', {
            'fields': ('video_url', 'documentation_url', 'additional_resources'),
            'classes': ('collapse',)
        }),
        ('Therapeutic Content', {
            'fields': ('therapeutic_instructions', 'coping_suggestions', 
                      'success_affirmations'),
            'classes': ('collapse',)
        }),
        ('Structure', {
            'fields': ('learning_path', 'order_position'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_published', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def difficulty_display(self, obj):
        """Display difficulty with stars"""
        return '★' * obj.difficulty_level + '☆' * (5 - obj.difficulty_level)
    difficulty_display.short_description = 'Difficulty'
    
    def learning_path_link(self, obj):
        """Display learning path as link"""
        if obj.learning_path:
            return format_html(
                '<a href="{}">{}</a>',
                f'/admin/learning/learningpath/{obj.learning_path.id}/change/',
                obj.learning_path.name
            )
        return '-'
    learning_path_link.short_description = 'Learning Path'


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    """Admin interface for user progress"""
    list_display = ['user', 'activity_title', 'status_display', 
                    'completion_time', 'time_spent_display', 'emotional_impact']
    list_filter = ['status', 'completion_time', 'activity__difficulty_level']
    search_fields = ['user__username', 'activity__title', 'reflection_notes']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    
    fieldsets = (
        ('Progress Tracking', {
            'fields': ('user', 'activity', 'status', 'start_time', 'completion_time')
        }),
        ('Technical Details', {
            'fields': ('time_spent_seconds', 'attempts', 'successful_attempts', 
                      'submitted_code', 'code_output', 'errors'),
            'classes': ('collapse',)
        }),
        ('Emotional Tracking', {
            'fields': ('emotional_state_before', 'emotional_state_after',
                      'stress_level_before', 'stress_level_after',
                      'confidence_before', 'confidence_after'),
            'classes': ('collapse',)
        }),
        ('Reflection', {
            'fields': ('self_assessment', 'reflection_notes', 'what_went_well',
                      'challenges_faced', 'coping_strategies_used'),
            'classes': ('collapse',)
        }),
        ('Therapeutic Insights', {
            'fields': ('breakthrough_notes', 'therapist_feedback'),
            'classes': ('collapse',)
        }),
    )
    
    def activity_title(self, obj):
        return obj.activity.title if obj.activity else '-'
    activity_title.short_description = 'Activity'
    
    def status_display(self, obj):
        """Display status with colors"""
        status_colors = {
            'not_started': 'gray',
            'in_progress': 'orange',
            'completed': 'green',
            'skipped': 'lightgray',
            'retry_later': 'blue',
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def time_spent_display(self, obj):
        """Format time spent"""
        if not obj.time_spent_seconds:
            return '-'
        
        hours = obj.time_spent_seconds // 3600
        minutes = (obj.time_spent_seconds % 3600) // 60
        seconds = obj.time_spent_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    time_spent_display.short_description = 'Time Spent'
    
    def emotional_impact(self, obj):
        """Calculate and display emotional impact"""
        impact = obj.calculate_emotional_impact()
        impact_text = impact.get('overall_impact', 'neutral')
        
        impact_icons = {
            'highly_positive': '💚',
            'positive': '💚',
            'neutral': '💛',
            'challenging': '🧡',
        }
        
        return format_html(
            '{} {}',
            impact_icons.get(impact_text, '💛'),
            impact_text.replace('_', ' ').title()
        )
    emotional_impact.short_description = 'Emotional Impact'