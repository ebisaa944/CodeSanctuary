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
    # Add the new external learning views
    external_courses,
    external_course_detail,
    import_external_course,
    personal_learning_plan,
    api_external_courses,
    api_search_external_courses,
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
    # EXTERNAL LEARNING PLATFORMS
    # ====================
    
    # Browse external learning courses
    path('external/', external_courses, name='external_courses'),
    
    # View external course details
    path('external/<str:platform_name>/<str:external_id>/', 
         external_course_detail, name='external_course_detail'),
    
    # Import external course to personal plan
    path('external/<str:platform_name>/<str:external_id>/import/', 
         import_external_course, name='import_external_course'),
    
    # Personal learning plan with external content
    path('personal-plan/', personal_learning_plan, name='personal_learning_plan'),
    
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
    
    # External learning API endpoints
    path('api/external/courses/', api_external_courses, name='api_external_courses'),
    path('api/external/search/', api_search_external_courses, name='api_search_external_courses'),
    
    # ====================
    # REST FRAMEWORK API ROUTES
    # ====================
    
    # REST API endpoints
    path('api/', include(router.urls)),
    
    # REST Framework authentication
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # learning/urls.py
# In the API ENDPOINTS section, add this line:
path('api/recommendations/', get_recommendations, name='api_recommendations'),  # Add this alias
    
    # ====================
    # ADDITIONAL FUNCTIONALITY
    # ====================
    
    # Wellness and emotional state
    path('wellness-checkin/', views.wellness_checkin, name='wellness_checkin'),
    path('log-emotional-state/', views.log_emotional_state, name='log_emotional_state'),
    path('emotional-history/', views.emotional_state_history, name='emotional_state_history'),
    path('stress-monitor/', views.stress_monitor, name='stress_monitor'),
    path('break-suggestions/', views.break_suggestions, name='break_suggestions'),
    
    # Social integration
    path('share-progress/<int:activity_id>/', views.share_progress, name='share_progress'),
    path('collaboration/create/', views.create_collaboration_session, name='create_collaboration'),
    path('collaboration/join/<str:session_id>/', views.join_collaboration_session, name='join_collaboration'),
    path('community-challenges/', views.community_challenges, name='community_challenges'),
    path('join-challenge/<int:challenge_id>/', views.join_challenge, name='join_challenge'),
    path('dashboard/', views.learning_dashboard, name='learning_dashboard'),
    
    # Chat integration
    path('learning-support/', views.learning_support_chat, name='learning_support_chat'),
    path('discussion/<int:activity_id>/', views.activity_discussion, name='activity_discussion'),
    path('request-code-review/', views.request_code_review, name='request_code_review'),
    path('code-review/<int:review_id>/', views.code_review_detail, name='code_review_detail'),
    
    # User stats and achievements
    path('user-stats/<int:user_id>/', views.user_learning_stats, name='user_learning_stats'),
    path('achievements/', views.user_achievements, name='user_achievements'),
    
    # Learning preferences
    path('preferences/', views.learning_preferences, name='learning_preferences'),
    path('update-preferences/', views.update_learning_preferences, name='update_learning_preferences'),
    
    # Streaks and badges
    path('current-streak/', views.current_streak, name='current_streak'),
    path('streak-history/', views.streak_history, name='streak_history'),
    path('badges/', views.earned_badges, name='earned_badges'),
    path('claim-badge/<int:badge_id>/', views.claim_badge, name='claim_badge'),
    
    # Points and rewards
    path('points/', views.points_balance, name='points_balance'),
    path('rewards/', views.rewards_catalog, name='rewards_catalog'),
    path('redeem/<int:reward_id>/', views.redeem_reward, name='redeem_reward'),
    
    # Analytics
    path('analytics/time/', views.time_analytics, name='time_analytics'),
    path('analytics/daily/', views.daily_analytics, name='daily_analytics'),
    path('analytics/weekly/', views.weekly_analytics, name='weekly_analytics'),
    path('analytics/monthly/', views.monthly_analytics, name='monthly_analytics'),
    path('analytics/performance/', views.performance_analytics, name='performance_analytics'),
    path('analytics/improvement/', views.improvement_analytics, name='improvement_analytics'),
    path('analytics/emotional/', views.emotional_analytics, name='emotional_analytics'),
    path('analytics/stress-patterns/', views.stress_pattern_analytics, name='stress_pattern_analytics'),
    
    # Export and reports
    path('export/pdf/', views.export_progress_pdf, name='export_progress_pdf'),
    path('export/csv/', views.export_progress_csv, name='export_progress_csv'),
    path('certificate/<int:path_id>/', views.export_certificate, name='export_certificate'),
    path('therapy-report/', views.therapy_progress_report, name='therapy_progress_report'),
    path('export-therapy-pdf/', views.export_therapy_report_pdf, name='export_therapy_report_pdf'),
    
    # Resources and tutorials
    path('resources/', views.learning_resources, name='learning_resources'),
    path('resource/<int:resource_id>/', views.resource_detail, name='resource_detail'),
    path('complete-resource/<int:resource_id>/', views.complete_resource, name='complete_resource'),
    path('tutorials/', views.tutorials_list, name='tutorials_list'),
    path('tutorial/<int:tutorial_id>/', views.tutorial_detail, name='tutorial_detail'),
    path('code-examples/', views.code_examples, name='code_examples'),
    path('code-example/<int:example_id>/', views.code_example_detail, name='code_example_detail'),
    
    # Practice and challenges
    path('practice/', views.practice_dashboard, name='practice_dashboard'),
    path('practice/start/', views.start_practice_session, name='start_practice_session'),
    path('practice/end/', views.end_practice_session, name='end_practice_session'),
    path('challenges/', views.code_challenges, name='code_challenges'),
    path('challenge/<int:challenge_id>/', views.code_challenge_detail, name='code_challenge_detail'),
    path('submit-challenge/<int:challenge_id>/', views.submit_code_challenge, name='submit_code_challenge'),
    
    # Mindfulness and wellness
    path('mindfulness/', views.mindfulness_exercise, name='mindfulness_exercise'),
    path('breathing/', views.breathing_exercise, name='breathing_exercise'),
    path('stretching/', views.stretching_exercise, name='stretching_exercise'),
    
    # Recommendations
    path('personalized-recommendations/', views.personalized_recommendations, name='personalized_recommendations'),
    path('mood-recommendations/', views.mood_based_recommendations, name='mood_based_recommendations'),
    
    # Difficulty adjustment
    path('adjust-difficulty/', views.adjust_difficulty, name='adjust_difficulty'),
    path('suggest-difficulty/', views.suggest_difficulty, name='suggest_difficulty'),
    
    # Learning style
    path('learning-style/', views.learning_style_assessment, name='learning_style_assessment'),
    path('learning-style/result/', views.learning_style_result, name='learning_style_result'),
    
    # Reminders and goals
    path('reminders/', views.learning_reminders, name='learning_reminders'),
    path('set-reminder/', views.set_reminder, name='set_reminder'),
    path('delete-reminder/<int:reminder_id>/', views.delete_reminder, name='delete_reminder'),
    path('daily-goals/', views.daily_goals, name='daily_goals'),
    path('set-goal/', views.set_daily_goal, name='set_daily_goal'),
    path('complete-goal/', views.complete_daily_goal, name='complete_daily_goal'),
    
    # Help and support
    path('help/', views.help_center, name='help_center'),
    path('faq/', views.faq, name='faq'),
    path('video-tutorials/', views.video_tutorials, name='video_tutorials'),
    path('support/ticket/create/', views.create_support_ticket, name='create_support_ticket'),
    path('support/tickets/', views.support_tickets, name='support_tickets'),
    path('support/ticket/<int:ticket_id>/', views.support_ticket_detail, name='support_ticket_detail'),
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    path('feedback/thank-you/', views.feedback_thank_you, name='feedback_thank_you'),
    
    # Mobile and offline
    path('mobile/sync/', views.mobile_sync, name='mobile_sync'),
    path('mobile/progress/', views.mobile_progress, name='mobile_progress'),
    path('mobile/notifications/', views.mobile_notifications, name='mobile_notifications'),
    path('offline/activities/', views.offline_activities, name='offline_activities'),
    path('offline/sync/', views.offline_sync, name='offline_sync'),
    
    # Webhooks and integrations
    path('webhook/github/', views.github_webhook, name='github_webhook'),
    path('webhook/slack/', views.slack_webhook, name='slack_webhook'),
    path('integrations/github/', views.github_integration, name='github_integration'),
    path('integrations/slack/', views.slack_integration, name='slack_integration'),
    
    # Error pages and debugging
    path('404/', views.custom_404, name='custom_404'),
    path('500/', views.custom_500, name='custom_500'),
    path('activity-unavailable/', views.activity_unavailable, name='activity_unavailable'),
    path('too-stressed/', views.too_stressed, name='too_stressed'),
    path('health/', views.health_check, name='health_check'),
    path('debug/emotions/', views.debug_emotions, name='debug_emotions'),
    path('debug/progress/', views.debug_progress, name='debug_progress'),
    
    # Redirects for old URLs
    path('old-dashboard/', views.redirect_old_dashboard, name='redirect_old_dashboard'),
    path('old-activity/<int:activity_id>/', views.redirect_old_activity, name='redirect_old_activity'),
]