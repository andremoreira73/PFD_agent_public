# pfd_analyzer/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# Add app_name for namespace to work
app_name = 'pfd_analyzer'

urlpatterns = [   
    # Main views
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # PDF management
    path('upload/', views.PFDFileCreateView.as_view(), name='upload_pdf'),
    path('files/', views.PFDFileListView.as_view(), name='file_list'),
    path('files/<int:pk>/', views.PFDFileDetailView.as_view(), name='pfd_file_detail'),
    
    # Run management
    path('runs/', views.PFDRunListView.as_view(), name='run_list'),
    path('run/new/', views.PFDRunCreateView.as_view(), name='new_run'),
    path('run/<int:pk>/', views.PFDRunDetailView.as_view(), name='run_detail'),
    path('run/<int:pk>/edit/', views.PFDRunUpdateView.as_view(), name='run_edit'),
    path('run/<int:pk>/lock/', views.lock_run, name='lock_run'),
    path('run/<int:pk>/unlock/', views.unlock_run, name='unlock_run'),
    path('search-runs/', views.search_runs, name='search_runs'),
]