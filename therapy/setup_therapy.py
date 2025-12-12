import os
import sys

print("🛠️ Setting up Therapeutic Coding Platform...")
print("=" * 50)

# 1. Check and fix serializer imports
print("\n1. Fixing serializer imports...")
serializer_path = "users/serializers.py"
if os.path.exists(serializer_path):
    with open(serializer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the import
    old_import = "from apps.therapy.models import EmotionalCheckIn"
    new_import = "from therapy.models import EmotionalCheckIn"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        print("   ✅ Fixed import: 'apps.therapy.models' → 'therapy.models'")
    elif new_import in content:
        print("   ✅ Import already correct")
    else:
        # Add the import if missing
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "from rest_framework import serializers" in line:
                lines.insert(i + 1, new_import)
                break
        content = '\n'.join(lines)
        print("   ✅ Added missing import")
    
    with open(serializer_path, 'w', encoding='utf-8') as f:
        f.write(content)

# 2. Create missing __init__.py files
print("\n2. Creating missing __init__.py files...")
for app in ['therapy', 'learning', 'social', 'chat']:
    init_file = f"{app}/__init__.py"
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("")
        print(f"   ✅ Created: {init_file}")

# 3. Create therapy admin file if missing
print("\n3. Setting up therapy admin...")
therapy_admin = "therapy/admin.py"
if not os.path.exists(therapy_admin):
    with open(therapy_admin, 'w', encoding='utf-8') as f:
        f.write('''from django.contrib import admin
from .models import EmotionalCheckIn, CopingStrategy

@admin.register(EmotionalCheckIn)
class EmotionalCheckInAdmin(admin.ModelAdmin):
    list_display = ['user', 'primary_emotion', 'intensity', 'created_at']
    list_filter = ['primary_emotion', 'intensity']
    search_fields = ['user__username', 'notes']

@admin.register(CopingStrategy)
class CopingStrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy_type', 'difficulty_level']
    list_filter = ['strategy_type', 'difficulty_level']
''')
    print("   ✅ Created therapy/admin.py")

# 4. Create therapy apps.py if missing
print("\n4. Setting up therapy app config...")
therapy_apps = "therapy/apps.py"
if not os.path.exists(therapy_apps):
    with open(therapy_apps, 'w', encoding='utf-8') as f:
        f.write('''from django.apps import AppConfig

class TherapyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'therapy'
    verbose_name = 'Therapeutic Tools'
''')
    print("   ✅ Created therapy/apps.py")

# 5. Create basic views for therapy
print("\n5. Creating basic therapy views...")
therapy_views = "therapy/views.py"
if not os.path.exists(therapy_views):
    with open(therapy_views, 'w', encoding='utf-8') as f:
        f.write('''from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import EmotionalCheckIn, CopingStrategy
from .serializers import EmotionalCheckInSerializer, CopingStrategySerializer

class EmotionalCheckInViewSet(viewsets.ModelViewSet):
    """API endpoint for emotional check-ins"""
    queryset = EmotionalCheckIn.objects.all()
    serializer_class = EmotionalCheckInSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own check-ins"""
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set user when creating check-in"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['GET'])
    def today(self, request):
        """Get today's check-ins"""
        today = timezone.now().date()
        checkins = self.get_queryset().filter(
            created_at__date=today
        )
        serializer = self.get_serializer(checkins, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['GET'])
    def insights(self, request):
        """Get emotional insights"""
        checkins = self.get_queryset().order_by('-created_at')[:10]
        
        # Calculate basic insights
        if checkins:
            latest = checkins[0]
            pattern = latest.get_emotional_pattern()
            suggestions = latest.suggest_coping_strategies()
        else:
            pattern = {}
            suggestions = []
        
        return Response({
            'recent_checkins': len(checkins),
            'emotional_pattern': pattern,
            'suggested_strategies': suggestions[:3],
            'has_data': len(checkins) > 0
        })

class CopingStrategyViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for coping strategies"""
    queryset = CopingStrategy.objects.filter(is_active=True)
    serializer_class = CopingStrategySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['GET'])
    def recommended(self, request):
        """Get strategies recommended for current emotional state"""
        user = request.user
        
        # Get user's latest emotion
        latest_checkin = EmotionalCheckIn.objects.filter(
            user=user
        ).order_by('-created_at').first()
        
        if latest_checkin:
            # Filter strategies for the current emotion
            target_emotion = latest_checkin.primary_emotion
            strategies = self.get_queryset().filter(
                target_emotions__contains=[target_emotion]
            )
        else:
            # Default gentle strategies
            strategies = self.get_queryset().filter(
                difficulty_level=1
            )[:5]
        
        serializer = self.get_serializer(strategies, many=True)
        return Response(serializer.data)

def dashboard_view(request):
    """Therapy dashboard view"""
    from django.shortcuts import render
    return render(request, 'therapy/dashboard.html')
''')
    print("   ✅ Created therapy/views.py")

# 6. Create therapy serializers
print("\n6. Creating therapy serializers...")
therapy_serializers = "therapy/serializers.py"
if not os.path.exists(therapy_serializers):
    with open(therapy_serializers, 'w', encoding='utf-8') as f:
        f.write('''from rest_framework import serializers
from .models import EmotionalCheckIn, CopingStrategy

class EmotionalCheckInSerializer(serializers.ModelSerializer):
    """Serializer for emotional check-ins"""
    emotional_summary = serializers.SerializerMethodField()
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = EmotionalCheckIn
        fields = [
            'id', 'primary_emotion', 'secondary_emotions', 'intensity',
            'physical_symptoms', 'trigger_description', 'context_tags',
            'coping_strategies_used', 'coping_effectiveness',
            'notes', 'key_insight', 'created_at',
            'emotional_summary', 'time_since'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_emotional_summary(self, obj):
        """Get emotional summary"""
        return obj.emotional_summary
    
    def get_time_since(self, obj):
        """Get human-readable time since"""
        return obj.get_time_since()
    
    def validate(self, data):
        """Validate therapeutic data"""
        # Ensure coping effectiveness matches strategies used
        if data.get('coping_effectiveness') and not data.get('coping_strategies_used'):
            raise serializers.ValidationError(
                "Coping effectiveness requires coping strategies used"
            )
        return data

class CopingStrategySerializer(serializers.ModelSerializer):
    """Serializer for coping strategies"""
    is_recommended = serializers.SerializerMethodField()
    
    class Meta:
        model = CopingStrategy
        fields = [
            'id', 'name', 'description', 'strategy_type',
            'target_emotions', 'estimated_minutes', 'difficulty_level',
            'coding_integration', 'coding_language', 'instructions',
            'tips_for_success', 'common_challenges', 'is_recommended'
        ]
    
    def get_is_recommended(self, obj):
        """Check if strategy is recommended for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_recommended_for_user(request.user)
        return True
''')
    print("   ✅ Created therapy/serializers.py")

# 7. Create therapy URLs
print("\n7. Creating therapy URLs...")
therapy_urls = "therapy/urls.py"
if not os.path.exists(therapy_urls):
    with open(therapy_urls, 'w', encoding='utf-8') as f:
        f.write('''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'checkins', views.EmotionalCheckInViewSet, basename='checkin')
router.register(r'strategies', views.CopingStrategyViewSet, basename='strategy')

urlpatterns = [
    path('api/', include(router.urls)),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]

app_name = 'therapy'
''')
    print("   ✅ Created therapy/urls.py")

print("\n" + "=" * 50)
print("🎉 Setup complete!")
print("\nNext steps:")
print("1. Run migrations: python manage.py makemigrations")
print("2. Apply migrations: python manage.py migrate")
print("3. Run server: python manage.py runserver")
print("4. Visit: http://127.0.0.1:8000/therapy/api/checkins/")