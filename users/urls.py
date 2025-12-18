# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    html_login,
    html_logout,
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    UserProfileViewSet,
    UserSettingsView,
    TherapeuticCommunityView,
    web_logout,
    emotional_state_view,  # Add this import
)

app_name = 'users'

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')

urlpatterns = [

    path('', views.landing_page, name='landing_page'),
    # === HTML AUTHENTICATION (for browsers) ===
    path('login/', html_login, name='login'),
    path('logout/', html_logout, name='logout'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    
    # === API AUTHENTICATION (for mobile apps) ===
    path('api/login/', UserLoginView.as_view(), name='api_login'),
    path('api/logout/', UserLogoutView.as_view(), name='api_logout'),
    
    # Legacy web logout
    path('web-logout/', web_logout, name='web-logout'),

    # Profile URLs
    path('', include(router.urls)),

    # Settings URL
    path('settings/', UserSettingsView.as_view(), name='settings'),

    # Community URL
    path('community/', TherapeuticCommunityView.as_view(), name='community'),
    
    # NEW: Emotional State URL - Add this line
    path('emotional-state/', emotional_state_view, name='emotional_state'),
]