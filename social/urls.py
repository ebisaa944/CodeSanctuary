# social/urls.py - CORRECTED VERSION
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    # Class-based HTML views
    CommunityHomeView,
    InteractionListView,
    InteractionDetailView,
    InteractionCreateView,
    SupportCircleListView,
    SupportCircleDetailView,
    SupportCircleJoinView,
    AchievementListView,
    UserAchievementsView,
    
    # API Views
    CommunityAnalyticsView,
    
    # ViewSets
    GentleInteractionViewSet,
    AchievementViewSet,
    SupportCircleViewSet,
)

# Initialize REST Framework router
router = DefaultRouter()
router.register(r'interactions', GentleInteractionViewSet, basename='interaction')
router.register(r'achievements', AchievementViewSet, basename='achievement')
router.register(r'circles', SupportCircleViewSet, basename='circle')

app_name = 'social'

urlpatterns = [
    # ====================
    # CORE SOCIAL PAGES
    # ====================
    
    # Homepage at /social/
    path('', CommunityHomeView.as_view(), name='home'),
    
    # Redirect /social/home/ to /social/
    path('home/', RedirectView.as_view(pattern_name='social:home', permanent=False)),
    
    # Interactions
    path('interactions/', InteractionListView.as_view(), name='interaction_list'),
    path('interactions/create/', InteractionCreateView.as_view(), name='interaction_create'),
    path('interactions/<int:pk>/', InteractionDetailView.as_view(), name='interaction_detail'),
    
    # Support Circles
    path('circles/', SupportCircleListView.as_view(), name='circles_list'),
    path('circles/<int:pk>/', SupportCircleDetailView.as_view(), name='circle_detail'),
    path('circles/<int:pk>/join/', SupportCircleJoinView.as_view(), name='circle_join'),
    
    # Achievements
    path('achievements/', AchievementListView.as_view(), name='achievements_list'),
    path('achievements/my/', UserAchievementsView.as_view(), name='user_achievements'),
    
    # ====================
    # API ENDPOINTS (JSON/AJAX)
    # ====================
    
    # Function-based API views
    path('api/stats/', views.api_community_stats, name='api_stats'),
    path('api/encouragement/', views.api_send_quick_encouragement, name='quick_encouragement'),
    path('api/share-progress/', views.api_share_progress, name='share_progress'),
    path('api/health/', views.health_check, name='health_check'),
    
    # Class-based APIView
    path('api/analytics/', CommunityAnalyticsView.as_view(), name='community_analytics'),
    
    # ====================
    # REST FRAMEWORK API ROUTES
    # ====================
    
    # REST API endpoints (via router) - NO nested "api/" here!
    path('api/', include(router.urls)),
    
    # Additional custom actions for viewsets
    path('api/interactions/<uuid:pk>/create-reply/', 
         views.GentleInteractionViewSet.as_view({'post': 'create_reply'}), 
         name='api_create_reply'),
    path('api/interactions/send-encouragement/', 
         views.GentleInteractionViewSet.as_view({'post': 'send_encouragement'}), 
         name='api_send_encouragement'),
    
    path('api/achievements/<uuid:pk>/add-reflection/', 
         views.AchievementViewSet.as_view({'post': 'add_reflection'}), 
         name='api_add_reflection'),
    path('api/achievements/<uuid:pk>/share/', 
         views.AchievementViewSet.as_view({'post': 'share_achievement'}), 
         name='api_share_achievement'),
    path('api/achievements/<uuid:pk>/recent-earners/', 
         views.AchievementViewSet.as_view({'get': 'recent_earners'}), 
         name='api_recent_earners'),
    
    path('api/circles/<uuid:pk>/join/', 
         views.SupportCircleViewSet.as_view({'post': 'join_circle'}), 
         name='api_join_circle'),
    path('api/circles/<uuid:pk>/leave/', 
         views.SupportCircleViewSet.as_view({'post': 'leave_circle'}), 
         name='api_leave_circle'),
    
    # REST Framework authentication
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]