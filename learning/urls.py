# learning/urls.py
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    learning_dashboard,
    learning_paths,
    learning_path_detail,
    activity_detail,
    progress_report,
    start_activity,
    submit_activity,
    get_recommendations,
    get_learning_stats,
    LearningPathViewSet,
    MicroActivityViewSet,
    UserProgressViewSet,
)

# Initialize REST Framework router
router = DefaultRouter()
router.register(r'api/paths', LearningPathViewSet, basename='learningpath')
router.register(r'api/activities', MicroActivityViewSet, basename='microactivity')
router.register(r'api/progress', UserProgressViewSet, basename='userprogress')

app_name = 'learning'

urlpatterns = [
    # ====================
    # CORE LEARNING PAGES
    # ====================
    
    # Dashboard at /learning/dashboard/
    path('dashboard/', learning_dashboard, name='dashboard'),
    path('skip-day/', views.skip_day, name='skip_day'),
    path('update-readiness/', views.update_readiness, name='update_readiness'),
    # Redirect /learning/ to /learning/dashboard/
    path('', RedirectView.as_view(url='dashboard/', permanent=False)),
    
    
    # Browse all learning paths
    path('paths/', learning_paths, name='paths'),
    
    # Specific learning path detail
    path('paths/<slug:slug>/', learning_path_detail, name='path_detail'),
    
    # Activity detail page
    path('activities/<slug:slug>/', activity_detail, name='activity_detail'),
    
    # Progress reporting and analytics
    path('progress/', progress_report, name='progress_report'),
    
    # ====================
    # API ENDPOINTS (JSON/AJAX)
    # ====================
    
    # Activity lifecycle management
    path('api/activity/<int:activity_id>/start/', start_activity, name='start_activity'),
    path('api/activity/<int:activity_id>/submit/', submit_activity, name='submit_activity'),
    
    # Recommendations and suggestions
    path('api/recommendations/', get_recommendations, name='get_recommendations'),
    
    
    # Learning statistics
    path('api/stats/', get_learning_stats, name='get_learning_stats'),
    
    # ====================
    # REST FRAMEWORK API ROUTES
    # ====================
    
    # REST API endpoints
    path('api/', include(router.urls)),
    
    # REST Framework authentication
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]