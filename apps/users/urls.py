from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.UserProfileViewSet, basename='userprofile')

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('logout/', views.UserLogoutView.as_view(), name='user-logout'),
    
    # Current user
    path('me/', views.UserProfileViewSet.as_view({'get': 'current_user'}), name='current-user'),
    
    # Settings
    path('settings/', views.UserSettingsView.as_view(), name='user-settings'),
    
    # Community
    path('community/', views.TherapeuticCommunityView.as_view(), name='therapeutic-community'),
    
    # Include router URLs
    path('', include(router.urls)),
]