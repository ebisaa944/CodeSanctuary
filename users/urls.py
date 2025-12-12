from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    UserProfileViewSet,
    UserSettingsView,
    TherapeuticCommunityView
)

app_name = 'users'


router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')

urlpatterns = [
    # Authentication URLs
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    
    # Profile URLs (via ViewSet)
    path('', include(router.urls)),
    
    # Settings URL
    path('settings/', UserSettingsView.as_view(), name='settings'),
    
    # Community URL
    path('community/', TherapeuticCommunityView.as_view(), name='community'),
    
    # Additional therapeutic endpoints
    path('therapeutic/checkin/', include('therapy.urls')),
    path('learning/plan/', include('learning.urls')),
    path('social/connections/', include('social.urls')),
]

# Add namespace for reverse URL lookups
app_name = 'users'