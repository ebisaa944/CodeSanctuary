"""
URL configuration for therapeutic_coding project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
# from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from .health import health
urlpatterns = [
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Users app URLs (including login/register)
    path('', include('users.urls')),  # This includes the landing page
    
    # Other app URLs
    path('therapy/', include('therapy.urls')),
    path('learning/', include('learning.urls')),
     path('social/', include('social.urls')),  # This line is crucial!
    path('chat/', include('chat.urls')),
    path('health/', health),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
