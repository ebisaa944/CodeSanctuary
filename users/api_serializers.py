from rest_framework import serializers
from .models import TherapeuticUser


class OnlineUserSerializer(serializers.ModelSerializer):
    """Expose minimal public info for online users; avoid PII/sensitive fields."""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = TherapeuticUser
        fields = ['id', 'display_name', 'avatar_color']
        read_only_fields = fields

    def get_display_name(self, obj):
        # Respect privacy
        if getattr(obj, 'hide_progress', False):
            return 'Learner'
        return obj.username
