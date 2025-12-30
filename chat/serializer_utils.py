# Add this to chat/serializers.py or create chat/serializer_utils.py

class ChatStatisticsSerializer(serializers.Serializer):
    """
    Serializer for therapeutic chat statistics
    """
    total_messages = serializers.IntegerField()
    total_rooms = serializers.IntegerField()
    active_participants = serializers.IntegerField()
    vulnerable_shares = serializers.IntegerField()
    coping_strategies_shared = serializers.IntegerField()
    affirmations_given = serializers.IntegerField()
    breakthrough_moments = serializers.IntegerField()
    
    # Emotional metrics
    avg_stress_change = serializers.FloatField()
    most_common_emotional_tone = serializers.CharField()
    safety_plan_activations = serializers.IntegerField()
    
    # Therapeutic engagement
    avg_session_duration = serializers.FloatField()
    therapeutic_engagement_score = serializers.FloatField()
    support_ratio = serializers.FloatField(help_text="Support given vs received")
    
    # Time-based metrics
    peak_activity_hours = serializers.ListField(child=serializers.IntegerField())
    daily_active_users = serializers.IntegerField()
    weekly_retention = serializers.FloatField()


class ChatExportSerializer(serializers.ModelSerializer):
    """
    Serializer for exporting therapeutic chat data
    """
    room_info = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()
    therapeutic_context = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'content', 'message_type', 'created_at', 'updated_at',
            'emotional_tone', 'trigger_warning', 'is_vulnerable_share',
            'coping_strategy_shared', 'contains_affirmation',
            'therapeutic_label', 'room_info', 'user_info',
            'therapeutic_context', 'reactions'
        ]
    
    def get_room_info(self, obj):
        return {
            'id': str(obj.room.id),
            'name': obj.room.name,
            'type': obj.room.room_type,
            'safety_level': obj.room.safety_level
        }
    
    def get_user_info(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'emotional_profile': obj.user.emotional_profile,
            'stress_level_at_post': obj.user.current_stress_level
        }
    
    def get_therapeutic_context(self, obj):
        return obj.get_therapeutic_context()
    
    def get_reactions(self, obj):
        reactions = obj.reactions.all()
        return [
            {
                'type': r.reaction_type,
                'user': r.user.username if not r.is_anonymous else 'Anonymous',
                'timestamp': r.created_at
            }
            for r in reactions
        ]