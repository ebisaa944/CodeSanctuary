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
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/docs/', TemplateView.as_view(
        template_name='api_docs.html',
        extra_context={'title': 'Code Sanctuary API Docs'}
    ), name='api-docs'),
    
    # API Endpoints
    path('api/users/', include('apps.users.urls')),
    path('api/therapy/', include('apps.therapy.urls')),
    path('api/learning/', include('apps.learning.urls')),
    path('api/social/', include('apps.social.urls')),
    
    # Frontend (for React/Vue)
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Authentication (Django built-in)
    path('accounts/', include('django.contrib.auth.urls')),
]

# Serve static/media in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
