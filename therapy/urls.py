from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    EmotionalCheckInViewSet,
    CopingStrategyViewSet,
    QuickCheckInAPI,
    EmotionalHistoryAPI,
    TherapeuticInsightsAPI,
)

# API Router
router = DefaultRouter()
router.register(r'checkins', EmotionalCheckInViewSet, basename='checkin')
router.register(r'strategies', CopingStrategyViewSet, basename='strategy')

app_name = 'therapy'

urlpatterns = [
    # Dashboard and main views
    path('', views.therapy_dashboard, name='dashboard'),
    path('dashboard/', views.therapy_dashboard, name='dashboard'),
    
    # Emotional checkins
    path('checkins/', views.checkin_list, name='checkin_list'),
    path('checkins/create/', views.checkin_create, name='checkin_create'),
    path('checkins/quick/', views.quick_checkin, name='quick_checkin'),
    path('checkins/<int:pk>/', views.checkin_detail, name='checkin_detail'),
    
    # Coping strategies
    path('strategies/', views.coping_strategies_list, name='strategies_list'),
    path('strategies/<int:pk>/', views.coping_strategy_detail, name='strategy_detail'),
    path('strategies/recommendations/', views.get_recommendations, name='get_recommendations'),
    
    # Insights and analysis
    path('insights/', views.emotional_insights, name='insights'),
    path('export/<str:format>/', views.export_data, name='export_data'),
    
    # Admin views (staff only)
    path('admin/strategies/create/', views.coping_strategy_create, name='admin_strategy_create'),
    path('admin/strategies/<int:pk>/edit/', views.coping_strategy_update, name='admin_strategy_edit'),
    
    # Utility
    path('log-activity/', views.log_activity, name='log_activity'),
    
    # API routes (prefixed with api/)
    path('api/', include(router.urls)),
    path('api/quick-checkin/', QuickCheckInAPI.as_view(), name='api_quick_checkin'),
    path('api/history/', EmotionalHistoryAPI.as_view(), name='api_history'),
    path('api/insights/', TherapeuticInsightsAPI.as_view(), name='api_insights'),
    path('api/summary/', views.emotional_summary, name='api_summary'),
    path('api/resources/', views.therapy_resources, name='api_resources'),
]