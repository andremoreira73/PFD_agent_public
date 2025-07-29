# PFD_agent/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def get_user_accessible_apps(user):
    """Return list of apps user can access"""
    apps = []
    
    # Everyone can access bench
    if user.is_authenticated:
        apps.append({
            'name': 'PFD Bench',
            'url_name': 'pfd_bench:dashboard',
            'icon': 'fas fa-project-diagram',
            'description': 'Generate Process Descriptions'
        })
    
    # Staff can also access analyzer
    if user.is_staff:
        apps.append({
            'name': 'PFD Analyzer',
            'url_name': 'pfd_analyzer:dashboard',  
            'icon': 'fas fa-chart-line',
            'description': 'LLM Evaluation & Analysis'
        })
    
    return apps

@login_required
def home(request):
    """Landing page showing available apps"""
    accessible_apps = get_user_accessible_apps(request.user)
    
    # Auto-redirect if only one app
    if len(accessible_apps) == 1:
        return redirect(accessible_apps[0]['url_name'])
    
    return render(request, 'home.html', {'apps': accessible_apps})