from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import TherapeuticUser

@admin.register(TherapeuticUser)
class TherapeuticUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'emotional_profile', 'gentle_mode', 'current_stress_level', 'is_staff')
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