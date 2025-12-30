# chat/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import *

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'safety_level', 'is_active', 'participant_count', 'created_at']
    list_filter = ['room_type', 'safety_level', 'is_private', 'is_archived']
    search_fields = ['name', 'description']
    filter_horizontal = ['moderators', 'therapists']
    readonly_fields = ['created_at', 'updated_at']
    
    def participant_count(self, obj):
        return obj.participant_count
    participant_count.short_description = 'Participants'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['truncated_content', 'user', 'room', 'message_type', 'created_at', 'is_vulnerable_share']
    list_filter = ['message_type', 'is_vulnerable_share', 'requires_moderation', 'room']
    search_fields = ['content', 'user__username', 'room__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def truncated_content(self, obj):
        return obj.safe_content_preview
    truncated_content.short_description = 'Content'

@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'role', 'comfort_level', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'comfort_level']
    search_fields = ['user__username', 'room__name']

@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'reaction_type', 'message_preview', 'created_at']
    list_filter = ['reaction_type', 'is_supportive']
    
    def message_preview(self, obj):
        return obj.message.content[:50]
    message_preview.short_description = 'Message'

@admin.register(ChatSessionAnalytics)
class ChatSessionAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'session_start', 'session_duration', 'stress_change']
    list_filter = ['room', 'session_start']  # CHANGED: Removed '__date'
    readonly_fields = ['session_duration_minutes', 'therapeutic_engagement_score']
    
    def session_duration(self, obj):
        duration = obj.session_duration_minutes
        return f"{duration:.1f} min" if duration else "Ongoing"
    
    def stress_change(self, obj):
        change = obj.stress_change
        if change is not None:
            if change < 0:
                return format_html('<span style="color: green;">↓ {}</span>', abs(change))
            elif change > 0:
                return format_html('<span style="color: red;">↑ {}</span>', change)
            else:
                return "No change"
        return "N/A"
@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'is_urgent']
    search_fields = ['user__username', 'title', 'message']

@admin.register(TherapeuticChatSettings)
class TherapeuticChatSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'auto_trigger_warnings', 'gentle_notification_sounds', 'updated_at']
    search_fields = ['user__username']