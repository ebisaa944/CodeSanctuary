# chat/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rooms', views.TherapeuticChatRoomViewSet, basename='chatroom')
router.register(r'messages', views.TherapeuticChatMessageViewSet, basename='chatmessage')
router.register(r'memberships', views.TherapeuticRoomMembershipViewSet, basename='roommembership')
router.register(r'notifications', views.TherapeuticNotificationViewSet, basename='notification')
router.register(r'settings', views.TherapeuticChatSettingsViewSet, basename='chatsettings')

urlpatterns = [
    path('', include(router.urls)),
    
    # Therapeutic search
    path('search/', views.TherapeuticSearchView.as_view(), name='therapeutic-search'),
    
    # Bulk actions
    path('bulk-actions/', views.TherapeuticBulkActionView.as_view(), name='bulk-actions'),
    
    # Export
    path('export/', views.TherapeuticExportView.as_view(), name='therapeutic-export'),
    
    # Dashboard
    path('dashboard/', views.TherapeuticDashboardView.as_view(), name='therapeutic-dashboard'),
    
    # Templates
    path('templates/', views.TherapeuticTemplateView.as_view(), name='room-templates'),
    
    # Safety
    path('safety/', views.TherapeuticSafetyView.as_view(), name='therapeutic-safety'),
    
    # WebSocket/Real-time
    path('websocket-token/', views.therapeutic_websocket_token, name='websocket-token'),
    path('typing/<uuid:room_id>/', views.therapeutic_typing_indicator, name='typing-indicator'),
    path('presence/', views.therapeutic_presence_update, name='presence-update'),
    
    # Room-specific message list (alternative to nested routes)
    path('rooms/<uuid:pk>/messages/', 
         views.TherapeuticChatRoomViewSet.as_view({'get': 'messages'}), 
         name='room-messages'),
    
    # Room insights
    path('rooms/<uuid:pk>/insights/', 
         views.TherapeuticChatRoomViewSet.as_view({'get': 'therapeutic_insights'}), 
         name='room-insights'),
    
    # Room statistics
    path('rooms/<uuid:pk>/statistics/', 
         views.TherapeuticChatRoomViewSet.as_view({'get': 'statistics'}), 
         name='room-statistics'),
    
    # Room emotional check-in
    path('rooms/<uuid:pk>/checkin/', 
         views.TherapeuticChatRoomViewSet.as_view({'post': 'emotional_checkin'}), 
         name='room-checkin'),
    
    # Room safety plan
    path('rooms/<uuid:pk>/safety-plan/', 
         views.TherapeuticChatRoomViewSet.as_view({'post': 'safety_plan_activation'}), 
         name='room-safety-plan'),
]