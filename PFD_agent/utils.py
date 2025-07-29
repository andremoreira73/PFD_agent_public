


def get_user_accessible_apps(user):
    """Return list of apps user can access"""
    apps = []
    
    # Everyone can access bench
    if user.is_authenticated:
        apps.append({
            'name': 'PFD Bench',
            'url_name': 'pfd_bench:dashboard',
            'icon': 'fas fa-project-diagram',
            'description': 'Generate Process Flow Diagram Descriptions'
        })
    
    # Staff can also access analyzer
    if user.is_staff:
        apps.append({
            'name': 'PFD Analyzer',
            'url_name': 'pfd_analyzer:dashboard',  
            'icon': 'fas fa-chart-line',
            'description': 'LLM Evaluation & Analysis'
        })
    
    # Future apps can be added here with their own logic
    # if user.has_perm('some_permission'):
    #     apps.append({...})
    
    return apps