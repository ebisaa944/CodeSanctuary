import os
import sys

print("🛠️ Setting up Therapeutic Coding Platform...")
print("=" * 50)

# Get current directory
current_dir = os.getcwd()
print(f"Working in: {current_dir}")

# 1. Check and fix serializer imports
print("\n1. Fixing serializer imports...")
serializer_path = os.path.join("users", "serializers.py")
if os.path.exists(serializer_path):
    with open(serializer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the import
    old_import = "from apps.therapy.models import EmotionalCheckIn"
    new_import = "from therapy.models import EmotionalCheckIn"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        print("   ✅ Fixed import: 'apps.therapy.models' → 'therapy.models'")
    elif new_import in content:
        print("   ✅ Import already correct")
    else:
        # Check if import exists in different form
        if "EmotionalCheckIn" in content and "from therapy.models" not in content:
            # Add the import if missing
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "from rest_framework import serializers" in line:
                    lines.insert(i + 1, new_import)
                    break
            content = '\n'.join(lines)
            print("   ✅ Added missing import")
        else:
            print("   ℹ️ Import not found, may be using different approach")
    
    with open(serializer_path, 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print(f"   ❌ Serializer file not found: {serializer_path}")

# 2. Create missing __init__.py files
print("\n2. Creating missing __init__.py files...")
for app in ['therapy', 'learning', 'social', 'chat']:
    # Create app directory if it doesn't exist
    app_dir = app
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
        print(f"   📁 Created directory: {app_dir}")
    
    init_file = os.path.join(app_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("")
        print(f"   ✅ Created: {init_file}")
    else:
        print(f"   ℹ️ Already exists: {init_file}")

# 3. Create basic files for therapy app
print("\n3. Creating basic therapy files...")

# therapy/admin.py
therapy_admin = os.path.join("therapy", "admin.py")
if not os.path.exists(therapy_admin):
    with open(therapy_admin, 'w', encoding='utf-8') as f:
        f.write('''from django.contrib import admin
from .models import EmotionalCheckIn, CopingStrategy

@admin.register(EmotionalCheckIn)
class EmotionalCheckInAdmin(admin.ModelAdmin):
    list_display = ['user', 'primary_emotion', 'intensity', 'created_at']
    list_filter = ['primary_emotion', 'intensity', 'created_at']
    search_fields = ['user__username', 'notes', 'trigger_description']

@admin.register(CopingStrategy)
class CopingStrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy_type', 'difficulty_level', 'estimated_minutes']
    list_filter = ['strategy_type', 'difficulty_level', 'coding_integration']
    search_fields = ['name', 'description']
''')
    print("   ✅ Created therapy/admin.py")

# therapy/apps.py
therapy_apps = os.path.join("therapy", "apps.py")
if not os.path.exists(therapy_apps):
    with open(therapy_apps, 'w', encoding='utf-8') as f:
        f.write('''from django.apps import AppConfig

class TherapyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'therapy'
    verbose_name = 'Therapeutic Tools'
''')
    print("   ✅ Created therapy/apps.py")

# Create basic __init__.py in therapy if missing
therapy_init = os.path.join("therapy", "__init__.py")
if not os.path.exists(therapy_init):
    with open(therapy_init, 'w') as f:
        f.write("")

# 4. Check therapy models exist
print("\n4. Checking therapy models...")
therapy_models = os.path.join("therapy", "models.py")
if os.path.exists(therapy_models):
    with open(therapy_models, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "class EmotionalCheckIn" in content:
        print("   ✅ EmotionalCheckIn model found")
    else:
        print("   ❌ EmotionalCheckIn model not found in models.py")
    
    if "class CopingStrategy" in content:
        print("   ✅ CopingStrategy model found")
    else:
        print("   ❌ CopingStrategy model not found")
else:
    print("   ❌ therapy/models.py not found")

# 5. Check settings.py
print("\n5. Checking settings configuration...")
settings_path = os.path.join("therapeutic_coding", "settings.py")
if os.path.exists(settings_path):
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for therapy in INSTALLED_APPS
    if "'therapy'" in content or '"therapy"' in content:
        print("   ✅ 'therapy' in INSTALLED_APPS")
    else:
        print("   ❌ 'therapy' NOT in INSTALLED_APPS - need to add it")
    
    # Check AUTH_USER_MODEL
    if "AUTH_USER_MODEL = 'users.TherapeuticUser'" in content or "AUTH_USER_MODEL = 'users.TherapeuticUser'" in content.replace(" ", ""):
        print("   ✅ AUTH_USER_MODEL correctly set")
    else:
        print("   ❌ AUTH_USER_MODEL not set to 'users.TherapeuticUser'")
else:
    print("   ❌ settings.py not found")

# 6. Create minimal therapy views if missing
print("\n6. Creating minimal therapy views...")
therapy_views = os.path.join("therapy", "views.py")
if not os.path.exists(therapy_views):
    with open(therapy_views, 'w', encoding='utf-8') as f:
        f.write('''from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    """Therapy dashboard view"""
    return render(request, 'therapy/dashboard.html', {
        'user': request.user,
        'title': 'Therapy Dashboard'
    })

def api_checkins(request):
    """Simple API endpoint for checkins"""
    if request.method == 'GET':
        return JsonResponse({
            'message': 'Therapy API is working',
            'endpoints': [
                '/therapy/dashboard/',
                '/therapy/api/checkins/',
                '/therapy/api/strategies/'
            ]
        })
''')
    print("   ✅ Created minimal therapy/views.py")

# 7. Create therapy URLs
print("\n7. Creating therapy URLs...")
therapy_urls = os.path.join("therapy", "urls.py")
if not os.path.exists(therapy_urls):
    with open(therapy_urls, 'w', encoding='utf-8') as f:
        f.write('''from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('api/checkins/', views.api_checkins, name='api_checkins'),
]

app_name = 'therapy'
''')
    print("   ✅ Created therapy/urls.py")

# 8. Create templates directory
print("\n8. Creating templates...")
therapy_templates_dir = os.path.join("therapy", "templates", "therapy")
os.makedirs(therapy_templates_dir, exist_ok=True)
print(f"   📁 Created directory: {therapy_templates_dir}")

# Create a simple dashboard template
dashboard_template = os.path.join(therapy_templates_dir, "dashboard.html")
if not os.path.exists(dashboard_template):
    with open(dashboard_template, 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Therapy Dashboard - Code Sanctuary</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-heart"></i> Therapeutic Coding
            </a>
        </div>
    </nav>
    
    <div class="container mt-5">
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h2>Welcome to Your Therapeutic Dashboard</h2>
                    </div>
                    <div class="card-body">
                        <p>Hello, {{ user.username }}!</p>
                        <p>This is your safe space for therapeutic coding.</p>
                        
                        <div class="row mt-4">
                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-body">
                                        <h5>Emotional Check-in</h5>
                                        <p>Track how you're feeling</p>
                                        <a href="#" class="btn btn-primary">Check In</a>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-body">
                                        <h5>Coping Strategies</h5>
                                        <p>Tools for emotional regulation</p>
                                        <a href="#" class="btn btn-primary">View Tools</a>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-body">
                                        <h5>Progress Tracking</h5>
                                        <p>See your therapeutic journey</p>
                                        <a href="#" class="btn btn-primary">View Progress</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
''')
    print("   ✅ Created therapy dashboard template")

print("\n" + "=" * 50)
print("🎉 Setup complete!")
print("\n📋 Next steps to run:")
print("1. cd C:\\Users\\ebisaachame\\Desktop\\django_tutorial\\Code_Sanctuary")
print("2. python manage.py makemigrations therapy")
print("3. python manage.py migrate")
print("4. python manage.py runserver")
print("\n🌐 Then visit:")
print("- http://127.0.0.1:8000/therapy/dashboard/")
print("- http://127.0.0.1:8000/therapy/api/checkins/")