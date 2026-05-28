from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg
from ..models import ChatMessage, ChatRoom, RoomMembership


def calculate_for_room(room):
    """Calculate statistics for a specific room (moved from serializer)."""
    now = timezone.now()
    today = now.date()

    room_messages = ChatMessage.objects.filter(room=room)
    vulnerable_messages = room_messages.filter(is_vulnerable_share=True)
    coping_messages = room_messages.filter(coping_strategy_shared=True)
    affirmation_messages = room_messages.filter(contains_affirmation=True)

    room_memberships = RoomMembership.objects.filter(room=room)

    activity_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_messages = room_messages.filter(created_at__date=day).count()
        activity_data.append(day_messages)

    total_members = room_memberships.count()
    active_members = room_memberships.filter(last_seen__date=today).count()
    engagement_rate = (active_members / total_members * 100) if total_members > 0 else 0

    return {
        'total_messages': room_messages.count(),
        'vulnerable_shares': vulnerable_messages.count(),
        'coping_strategies': coping_messages.count(),
        'affirmations': affirmation_messages.count(),
        'avg_stress_level': room_memberships.aggregate(avg_stress=Avg('entry_stress_level'))['avg_stress'] or 0,
        'activity_data': activity_data,
        'active_members': active_members,
        'new_members_today': room_memberships.filter(joined_at__date=today).count(),
        'messages_today': room_messages.filter(created_at__date=today).count(),
        'engagement_rate': round(engagement_rate, 2)
    }


def calculate_global():
    """Calculate global chat statistics (moved from serializer)."""
    now = timezone.now()
    today = now.date()

    total_rooms = ChatRoom.objects.count()
    total_messages = ChatMessage.objects.count()
    total_users = RoomMembership.objects.values('user').distinct().count()

    active_rooms = ChatRoom.objects.filter(messages__created_at__gte=now - timedelta(hours=24)).distinct().count()

    vulnerable_messages = ChatMessage.objects.filter(is_vulnerable_share=True).count()
    vulnerable_percentage = (vulnerable_messages / total_messages * 100) if total_messages > 0 else 0

    return {
        'total_rooms': total_rooms,
        'total_messages': total_messages,
        'total_users': total_users,
        'active_rooms': active_rooms,
        'vulnerable_percentage': round(vulnerable_percentage, 2),
        'average_room_size': round(total_users / total_rooms, 2) if total_rooms > 0 else 0,
        'messages_today': ChatMessage.objects.filter(created_at__date=today).count()
    }
