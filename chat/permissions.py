# chat/permissions.py
from rest_framework import permissions
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from .models import (
    ChatRoom, RoomMembership, ChatMessage,
    MessageReaction, TherapeuticChatSettings
)

User = get_user_model()


class IsTherapeuticUser(permissions.BasePermission):
    """
    Base permission that requires user to be authenticated 
    and using the TherapeuticUser model
    """
    message = 'Authentication required with therapeutic user account.'
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            isinstance(request.user, User)
        )


class IsInGentleMode(permissions.BasePermission):
    """
    Permission that checks if user is in gentle mode
    (for actions that should be gentler or have additional safeguards)
    """
    message = 'This action requires gentle mode to be enabled.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Some actions are only allowed in gentle mode
        # For others, gentle mode might trigger different behavior
        gentle_required = getattr(view, 'requires_gentle_mode', False)
        
        if gentle_required:
            return request.user.gentle_mode
        return True
    
    def has_object_permission(self, request, view, obj):
        # Object-level gentle mode checks
        if hasattr(obj, 'requires_gentle_mode'):
            return request.user.gentle_mode or not obj.requires_gentle_mode
        return True


class StressLevelPermission(permissions.BasePermission):
    """
    Permission based on user's current stress level
    Some actions may be restricted when stress is too high
    """
    message = 'Your current stress level is too high for this action.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get stress level threshold from view or default
        max_stress_level = getattr(view, 'max_allowed_stress', 8)
        
        return request.user.current_stress_level <= max_stress_level


class RoomAccessPermission(permissions.BasePermission):
    """
    Permission to access a therapeutic chat room
    Checks stress level, membership, and therapeutic settings
    """
    message = 'You do not have permission to access this therapeutic space.'
    
    def has_permission(self, request, view):
        # Check if user can access rooms in general
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Users with very high stress may need to take a break
        if request.user.current_stress_level >= 9:
            self.message = 'Your stress level is very high. Please practice self-care before joining conversations.'
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check access to specific room"""
        if not isinstance(obj, ChatRoom):
            return False
        
        # Check if room is archived
        if obj.is_archived:
            self.message = 'This therapeutic space has been archived.'
            return False
        
        # Check if room is scheduled
        if obj.scheduled_open and obj.scheduled_close:
            now = timezone.now()
            if now < obj.scheduled_open:
                self.message = f'This space opens at {obj.scheduled_open.strftime("%Y-%m-%d %H:%M")}.'
                return False
            if now > obj.scheduled_close:
                self.message = f'This space closed at {obj.scheduled_close.strftime("%Y-%m-%d %H:%M")}.'
                return False
        
        # Check stress level limit
        if request.user.current_stress_level > obj.max_stress_level:
            self.message = f'Your current stress level ({request.user.current_stress_level}/10) is too high for this space (max: {obj.max_stress_level}/10).'
            return False
        
        # Check if user is a member
        try:
            membership = RoomMembership.objects.get(
                user=request.user,
                room=obj,
                is_active=True
            )
            
            # Check if user is muted
            if membership.is_muted:
                self.message = 'You are currently muted in this space and cannot participate.'
                return False
            
            return True
            
        except RoomMembership.DoesNotExist:
            # User is not a member
            self.message = 'You are not a member of this therapeutic space.'
            return False


class RoomMembershipPermission(permissions.BasePermission):
    """
    Permission for room membership actions
    """
    message = 'You do not have permission to manage memberships in this space.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # POST - joining a room
        if request.method == 'POST':
            return self.can_join_room(request, view)
        
        # GET, PUT, DELETE - managing memberships
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check permissions on specific membership"""
        if not isinstance(obj, RoomMembership):
            return False
        
        # User can always view/update their own membership
        if obj.user == request.user:
            # Users can leave rooms (DELETE) or update their own settings
            if request.method in ['GET', 'PUT', 'PATCH', 'DELETE']:
                return True
        
        # Room moderators/therapists can manage memberships
        if obj.room.moderators.filter(id=request.user.id).exists():
            return request.method in permissions.SAFE_METHODS + ['PUT', 'PATCH', 'DELETE']
        
        # Room therapists have full permissions
        if obj.room.therapists.filter(id=request.user.id).exists():
            return True
        
        return False
    
    def can_join_room(self, request, view):
        """Check if user can join a room"""
        room_id = request.data.get('room') or view.kwargs.get('room_id')
        
        if not room_id:
            return True  # Will be validated in serializer
        
        try:
            room = ChatRoom.objects.get(id=room_id)
            
            # Check stress level
            if request.user.current_stress_level > room.max_stress_level:
                self.message = f'Your stress level is too high to join this space (max: {room.max_stress_level}/10).'
                return False
            
            # Check if room is at capacity
            current_members = RoomMembership.objects.filter(
                room=room,
                is_active=True
            ).count()
            
            if current_members >= room.max_participants:
                self.message = 'This therapeutic space is at full capacity.'
                return False
            
            # Check if room requires consent
            if room.requires_consent and not request.data.get('consent_given'):
                self.message = 'Consent is required to join this therapeutic space.'
                return False
            
            # Check if room is gated (requires emotional readiness)
            if room.is_gated and request.user.emotional_profile in ['ANXIOUS', 'OVERWHELMED']:
                self.message = 'This space requires emotional readiness preparation.'
                return False
            
            return True
            
        except ChatRoom.DoesNotExist:
            return True  # Will be validated elsewhere


class MessagePermission(permissions.BasePermission):
    """
    Permission for therapeutic chat messages
    """
    message = 'You do not have permission to perform this action on messages.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check stress level for sending messages
        if request.method == 'POST':
            # Users with very high stress should take a break
            if request.user.current_stress_level >= 9:
                self.message = 'Your stress level is very high. Please practice self-care before sending messages.'
                return False
            
            # Check if user is in a room that allows messaging
            room_id = request.data.get('room') or view.kwargs.get('room_id')
            if room_id:
                try:
                    room = ChatRoom.objects.get(id=room_id)
                    membership = RoomMembership.objects.get(
                        user=request.user,
                        room=room,
                        is_active=True
                    )
                    
                    if membership.is_muted:
                        self.message = 'You are muted in this space and cannot send messages.'
                        return False
                    
                except (ChatRoom.DoesNotExist, RoomMembership.DoesNotExist):
                    pass
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check permissions on specific message"""
        if not isinstance(obj, ChatMessage):
            return False
        
        # Check if message is deleted
        if obj.deleted and request.method != 'GET':
            self.message = 'Cannot perform actions on deleted messages.'
            return False
        
        # User can always view messages they have permission to see
        if request.method == 'GET':
            return self.can_view_message(request.user, obj)
        
        # User can edit their own messages within time limit
        if request.method in ['PUT', 'PATCH']:
            return self.can_edit_message(request.user, obj)
        
        # User can delete their own messages
        if request.method == 'DELETE':
            return self.can_delete_message(request.user, obj)
        
        return False
    
    def can_view_message(self, user, message):
        """Check if user can view a message based on visibility settings"""
        # User can always view their own messages
        if message.user == user:
            return True
        
        # Check visibility settings
        if message.visibility == 'public':
            # Check if user is a member of the room
            try:
                RoomMembership.objects.get(
                    user=user,
                    room=message.room,
                    is_active=True
                )
                return True
            except RoomMembership.DoesNotExist:
                return False
        
        elif message.visibility == 'private':
            # Private messages are only visible to sender and recipient
            # (implementation depends on how private messages are handled)
            return False
        
        elif message.visibility == 'therapist_only':
            # Only therapists in the room can see these
            return message.room.therapists.filter(id=user.id).exists()
        
        elif message.visibility == 'moderators_only':
            # Only moderators can see these
            return message.room.moderators.filter(id=user.id).exists()
        
        elif message.visibility == 'self_reflection':
            # Only the sender can see these
            return message.user == user
        
        elif message.visibility == 'anonymous':
            # Anonymous messages are visible to room members
            try:
                RoomMembership.objects.get(
                    user=user,
                    room=message.room,
                    is_active=True
                )
                return True
            except RoomMembership.DoesNotExist:
                return False
        
        return False
    
    def can_edit_message(self, user, message):
        """Check if user can edit a message"""
        # User can edit their own messages within 15 minutes
        if message.user == user:
            time_since_creation = timezone.now() - message.created_at
            return time_since_creation.total_seconds() < 900  # 15 minutes
        
        # Moderators can edit any message within 1 hour
        if message.room.moderators.filter(id=user.id).exists():
            time_since_creation = timezone.now() - message.created_at
            return time_since_creation.total_seconds() < 3600  # 1 hour
        
        # Therapists can edit any message
        if message.room.therapists.filter(id=user.id).exists():
            return True
        
        return False
    
    def can_delete_message(self, user, message):
        """Check if user can delete a message"""
        # User can always delete their own messages
        if message.user == user:
            return True
        
        # Moderators can delete messages
        if message.room.moderators.filter(id=user.id).exists():
            return True
        
        # Therapists can delete messages
        if message.room.therapists.filter(id=user.id).exists():
            return True
        
        return False


class VulnerableSharePermission(permissions.BasePermission):
    """
    Special permission for vulnerable shares
    Additional safeguards for emotionally sensitive content
    """
    message = 'Additional safeguards apply to vulnerable shares.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if this is a vulnerable share
        is_vulnerable = request.data.get('is_vulnerable_share', False)
        
        if not is_vulnerable:
            return True
        
        # Additional checks for vulnerable shares
        
        # Check stress level - don't share when highly stressed
        if request.user.current_stress_level >= 8:
            self.message = 'Your stress level is too high for vulnerable sharing. Please practice self-care first.'
            return False
        
        # Check if user has vulnerability timeout enabled
        chat_settings = getattr(request.user, 'chat_settings', None)
        if chat_settings and chat_settings.vulnerability_timeout > 0:
            # In a real implementation, you might check last vulnerable share time
            pass
        
        # Check for trigger warnings if required
        room_id = request.data.get('room')
        if room_id:
            try:
                room = ChatRoom.objects.get(id=room_id)
                if room.trigger_warnings_required and not request.data.get('trigger_warning'):
                    self.message = 'Trigger warning is required for vulnerable shares in this space.'
                    return False
            except ChatRoom.DoesNotExist:
                pass
        
        return True


class ReactionPermission(permissions.BasePermission):
    """
    Permission for therapeutic message reactions
    """
    message = 'You do not have permission to react to this message.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check stress level for reactions
        if request.user.current_stress_level >= 9:
            self.message = 'Your stress level is very high. Please take a break before interacting.'
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check permissions on specific reaction or message for reaction"""
        if isinstance(obj, MessageReaction):
            # User can delete their own reactions
            if request.method == 'DELETE':
                return obj.user == request.user
            return False
        
        elif isinstance(obj, ChatMessage):
            # Check if user can react to this message
            return self.can_react_to_message(request.user, obj)
        
        return False
    
    def can_react_to_message(self, user, message):
        """Check if user can react to a message"""
        # Can't react to deleted messages
        if message.deleted:
            self.message = 'Cannot react to deleted messages.'
            return False
        
        # Check if user can view the message
        if not MessagePermission().can_view_message(user, message):
            self.message = 'You cannot see this message.'
            return False
        
        # Check message visibility for reactions
        if message.visibility == 'self_reflection':
            self.message = 'Cannot react to private reflection messages.'
            return False
        
        # Check if user is muted in the room
        try:
            membership = RoomMembership.objects.get(
                user=user,
                room=message.room,
                is_active=True
            )
            if membership.is_muted:
                self.message = 'You are muted in this space and cannot react to messages.'
                return False
        except RoomMembership.DoesNotExist:
            self.message = 'You are not a member of this space.'
            return False
        
        return True


class ModerationPermission(permissions.BasePermission):
    """
    Permission for therapeutic moderation actions
    """
    message = 'You do not have moderation permissions for this space.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Moderation actions require specific permissions
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Check if user is a moderator in any room
            moderated_rooms = ChatRoom.objects.filter(
                moderators=request.user
            ).exists()
            
            therapist_rooms = ChatRoom.objects.filter(
                therapists=request.user
            ).exists()
            
            if not moderated_rooms and not therapist_rooms:
                self.message = 'You do not have moderation privileges.'
                return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check moderation permissions on specific object"""
        if isinstance(obj, ChatRoom):
            # Check if user is a moderator/therapist in this room
            is_moderator = obj.moderators.filter(id=request.user.id).exists()
            is_therapist = obj.therapists.filter(id=request.user.id).exists()
            
            if not is_moderator and not is_therapist:
                self.message = 'You are not a moderator in this therapeutic space.'
                return False
            
            # Different permissions for moderators vs therapists
            if is_moderator:
                # Moderators can perform safe methods and some modifications
                if request.method in permissions.SAFE_METHODS + ['PUT', 'PATCH']:
                    return True
                # Only therapists can delete rooms
                elif request.method == 'DELETE':
                    return is_therapist
            
            elif is_therapist:
                # Therapists have full permissions
                return True
        
        elif isinstance(obj, ChatMessage):
            # Check moderation permissions for messages
            is_moderator = obj.room.moderators.filter(id=request.user.id).exists()
            is_therapist = obj.room.therapists.filter(id=request.user.id).exists()
            
            if not is_moderator and not is_therapist:
                return False
            
            # Moderators can flag, request edits, remove messages
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                return True
        
        elif isinstance(obj, RoomMembership):
            # Check moderation permissions for memberships
            is_moderator = obj.room.moderators.filter(id=request.user.id).exists()
            is_therapist = obj.room.therapists.filter(id=request.user.id).exists()
            
            if not is_moderator and not is_therapist:
                return False
            
            # Moderators can update roles, mute users
            if request.method in ['PUT', 'PATCH']:
                return True
            
            # Only therapists can remove moderators
            if request.method == 'DELETE' and obj.role == 'moderator':
                return is_therapist
            
            return True
        
        return False


class TherapeuticSettingsPermission(permissions.BasePermission):
    """
    Permission for therapeutic chat settings
    """
    message = 'You do not have permission to modify these settings.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Users can only manage their own settings
        user_id = view.kwargs.get('user_id') or view.kwargs.get('pk')
        
        if user_id and str(user_id) != str(request.user.id):
            # Therapists might view patient settings (optional)
            if request.user.is_therapist and request.method == 'GET':
                return True
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check permissions on specific settings"""
        if not isinstance(obj, TherapeuticChatSettings):
            return False
        
        # User can manage their own settings
        if obj.user == request.user:
            return True
        
        # Therapists can view patient settings
        if request.user.is_therapist and request.method == 'GET':
            return True
        
        return False


class AnonymousPostingPermission(permissions.BasePermission):
    """
    Permission for anonymous posting based on user settings
    """
    message = 'Anonymous posting is not enabled for your account.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if anonymous posting is requested
        is_anonymous = request.data.get('is_anonymous', False)
        visibility = request.data.get('visibility', '')
        
        if is_anonymous or visibility == 'anonymous':
            # Check user settings
            if not request.user.allow_anonymous:
                self.message = 'You have disabled anonymous posting in your therapeutic settings.'
                return False
            
            # Check room settings if applicable
            room_id = request.data.get('room') or view.kwargs.get('room_id')
            if room_id:
                try:
                    room = ChatRoom.objects.get(id=room_id)
                    # Some rooms might not allow anonymous posting
                    if room.room_type == 'therapy_session':
                        self.message = 'Anonymous posting is not allowed in therapy sessions.'
                        return False
                except ChatRoom.DoesNotExist:
                    pass
        
        return True


class EmotionalCheckInPermission(permissions.BasePermission):
    """
    Permission for emotional check-ins
    """
    message = 'You do not have permission to perform emotional check-ins.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check stress level for check-ins
        if request.user.current_stress_level >= 10:
            self.message = 'Your stress level is at maximum. Please seek immediate support.'
            return False
        
        return True


class SafetyPlanPermission(permissions.BasePermission):
    """
    Permission for safety plan related actions
    """
    message = 'Safety plan actions require therapeutic authorization.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Safety plan activation requires moderate stress level
        if request.method == 'POST' and 'activate_safety_plan' in request.data:
            if request.user.current_stress_level < 7:
                self.message = 'Safety plans are typically activated at stress level 7 or higher.'
                return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check safety plan permissions"""
        # User can always activate their own safety plan
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Therapists can manage safety plans for their patients
        if request.user.is_therapist:
            return True
        
        return False


class ExportPermission(permissions.BasePermission):
    """
    Permission for exporting therapeutic chat data
    """
    message = 'You do not have permission to export therapeutic data.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Exporting requires explicit consent
        if not request.data.get('export_consent'):
            self.message = 'Export consent is required for therapeutic data export.'
            return False
        
        # Check if user has export permissions in their settings
        chat_settings = getattr(request.user, 'chat_settings', None)
        if chat_settings and hasattr(chat_settings, 'allow_data_export'):
            if not chat_settings.allow_data_export:
                self.message = 'Data export is disabled in your therapeutic settings.'
                return False
        
        return True


class TherapeuticInsightPermission(permissions.BasePermission):
    """
    Permission for therapeutic insight generation and viewing
    """
    message = 'You do not have permission to access therapeutic insights.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Therapeutic insights require moderate emotional stability
        if request.user.current_stress_level >= 8:
            self.message = 'Your stress level is too high for therapeutic insight review.'
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check insight permissions"""
        # User can view insights about themselves
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Therapists can view insights for their patients
        if request.user.is_therapist and hasattr(obj, 'user'):
            # Check if request.user is obj.user's therapist
            # This would require additional therapist-patient relationship model
            return True
        
        return False


class RoomTemplatePermission(permissions.BasePermission):
    """
    Permission for creating rooms from therapeutic templates
    """
    message = 'You do not have permission to create rooms from templates.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Users with certain emotional profiles might not be ready for room creation
        if request.user.emotional_profile in ['OVERWHELMED', 'AVOIDANT']:
            self.message = 'Consider joining existing spaces before creating new ones.'
            return False
        
        # Check stress level
        if request.user.current_stress_level >= 7:
            self.message = 'Your stress level is too high for room creation.'
            return False
        
        return True


class BulkActionPermission(permissions.BasePermission):
    """
    Permission for bulk therapeutic actions
    """
    message = 'You do not have permission to perform bulk therapeutic actions.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Bulk actions require additional safeguards
        if request.method == 'POST':
            # Check confirmation
            if not request.data.get('confirmation_text'):
                self.message = 'Confirmation is required for bulk therapeutic actions.'
                return False
            
            # Users with high stress shouldn't perform bulk actions
            if request.user.current_stress_level >= 7:
                self.message = 'Bulk actions are not recommended when stress levels are high.'
                return False
        
        return True


# Permission classes for specific therapeutic roles
class IsTherapist(permissions.BasePermission):
    """
    Permission for therapeutic professionals
    """
    message = 'Therapeutic professional privileges required.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is marked as a therapist
        # This assumes your User model has an is_therapist field
        # If not, you can check room therapist relationships
        return getattr(request.user, 'is_therapist', False) or \
               ChatRoom.objects.filter(therapists=request.user).exists()
    
    def has_object_permission(self, request, view, obj):
        # Therapists have broader permissions
        if isinstance(obj, ChatRoom):
            return obj.therapists.filter(id=request.user.id).exists()
        elif isinstance(obj, ChatMessage):
            return obj.room.therapists.filter(id=request.user.id).exists()
        return True


class IsModerator(permissions.BasePermission):
    """
    Permission for room moderators
    """
    message = 'Moderator privileges required for this space.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a moderator in any room
        return ChatRoom.objects.filter(moderators=request.user).exists()
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ChatRoom):
            return obj.moderators.filter(id=request.user.id).exists()
        elif isinstance(obj, ChatMessage):
            return obj.room.moderators.filter(id=request.user.id).exists()
        elif isinstance(obj, RoomMembership):
            return obj.room.moderators.filter(id=request.user.id).exists()
        return False


class IsRoomCreator(permissions.BasePermission):
    """
    Permission for room creators
    """
    message = 'Only the room creator can perform this action.'
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if isinstance(obj, ChatRoom):
            return obj.created_by == request.user
        return False


# Composite permission classes
class TherapeuticAccessPermission(permissions.BasePermission):
    """
    Composite permission combining multiple therapeutic checks
    """
    message = 'Therapeutic access requirements not met.'
    
    def has_permission(self, request, view):
        # Check all base permissions
        permissions_to_check = [
            IsTherapeuticUser(),
            StressLevelPermission(),
        ]
        
        for permission in permissions_to_check:
            if not permission.has_permission(request, view):
                self.message = permission.message
                return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        # Combine relevant object permissions
        if isinstance(obj, ChatRoom):
            return RoomAccessPermission().has_object_permission(request, view, obj)
        elif isinstance(obj, ChatMessage):
            return MessagePermission().has_object_permission(request, view, obj)
        elif isinstance(obj, RoomMembership):
            return RoomMembershipPermission().has_object_permission(request, view, obj)
        
        return True


class GentleModeCompositePermission(permissions.BasePermission):
    """
    Special permission for actions in gentle mode
    """
    message = 'Gentle mode restrictions apply.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # If user is in gentle mode, apply additional checks
        if request.user.gentle_mode:
            gentle_permissions = [
                StressLevelPermission(),
                VulnerableSharePermission(),
            ]
            
            for permission in gentle_permissions:
                if not permission.has_permission(request, view):
                    self.message = permission.message
                    return False
        
        return True


# Utility functions for permission checking
def check_therapeutic_permission(user, room, permission_type):
    """
    Utility function to check therapeutic permissions
    """
    if not user or not user.is_authenticated:
        return False, "Authentication required"
    
    # Check stress level
    if user.current_stress_level >= 9:
        return False, "Stress level too high for therapeutic interactions"
    
    # Check room access
    try:
        membership = RoomMembership.objects.get(
            user=user,
            room=room,
            is_active=True
        )
        
        # Permission type specific checks
        if permission_type == 'send_message':
            if membership.is_muted:
                return False, "You are muted in this space"
            
            if user.current_stress_level >= 8:
                return False, "High stress detected. Consider taking a break"
            
            return True, "Permission granted"
        
        elif permission_type == 'moderate':
            is_moderator = room.moderators.filter(id=user.id).exists()
            is_therapist = room.therapists.filter(id=user.id).exists()
            
            if not is_moderator and not is_therapist:
                return False, "Moderation privileges required"
            
            return True, "Permission granted"
        
        elif permission_type == 'invite':
            # Only moderators/therapists/room creator can invite
            is_moderator = room.moderators.filter(id=user.id).exists()
            is_therapist = room.therapists.filter(id=user.id).exists()
            is_creator = room.created_by == user
            
            if not is_moderator and not is_therapist and not is_creator:
                return False, "Invitation privileges required"
            
            return True, "Permission granted"
        
    except RoomMembership.DoesNotExist:
        return False, "You are not a member of this therapeutic space"
    
    return False, "Unknown permission check"


def get_user_therapeutic_permissions(user, room=None):
    """
    Get comprehensive therapeutic permissions for a user
    """
    permissions = {
        'can_send_messages': False,
        'can_moderate': False,
        'can_invite': False,
        'can_create_rooms': False,
        'can_export': False,
        'requires_gentle_mode': user.gentle_mode if user else False,
        'stress_level': user.current_stress_level if user else None,
    }
    
    if not user or not user.is_authenticated:
        return permissions
    
    # General permissions based on user state
    permissions['can_create_rooms'] = user.current_stress_level <= 6
    
    # Room-specific permissions
    if room:
        try:
            membership = RoomMembership.objects.get(
                user=user,
                room=room,
                is_active=True
            )
            
            permissions['can_send_messages'] = not membership.is_muted
            permissions['can_moderate'] = room.moderators.filter(id=user.id).exists() or \
                                         room.therapists.filter(id=user.id).exists()
            permissions['can_invite'] = permissions['can_moderate'] or \
                                       room.created_by == user
            
        except RoomMembership.DoesNotExist:
            pass
    
    # Export permissions based on settings
    chat_settings = getattr(user, 'chat_settings', None)
    if chat_settings:
        permissions['can_export'] = getattr(chat_settings, 'allow_data_export', False)
    
    return permissions


# Django Model Permissions (for admin)
class TherapeuticModelPermissions(permissions.DjangoModelPermissions):
    """
    Custom DjangoModelPermissions with therapeutic considerations
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }
    
    def has_permission(self, request, view):
        # Add therapeutic check to standard model permissions
        if not IsTherapeuticUser().has_permission(request, view):
            return False
        
        return super().has_permission(request, view)


# Permission decorators for function-based views
def therapeutic_permission_required(permission_classes):
    """
    Decorator for function-based views requiring therapeutic permissions
    """
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            # Check all permission classes
            for permission_class in permission_classes:
                permission = permission_class()
                if not permission.has_permission(request, None):
                    raise PermissionDenied(permission.message)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def room_access_required(view_func):
    """
    Decorator ensuring user has access to the room
    """
    @therapeutic_permission_required([RoomAccessPermission])
    def wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped_view


def moderator_required(view_func):
    """
    Decorator requiring moderator privileges
    """
    @therapeutic_permission_required([ModerationPermission])
    def wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped_view


def therapist_required(view_func):
    """
    Decorator requiring therapist privileges
    """
    @therapeutic_permission_required([IsTherapist])
    def wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped_view