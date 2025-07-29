
# pfd_bench/urls.py
from django.urls import path
from . import views

app_name = 'pfd_bench'

urlpatterns = [
    path('', views.project_list, name='dashboard'),

    path('project/<int:pk>/', views.project_detail, name='project_detail'),

    # Create new projects
    path('project/new-modal/', views.new_project_modal, name='new_project_modal'),
    path('project/create/', views.create_project, name='create_project'),
    
    # HTMX partials for project view
    path('project/<int:project_id>/runs/', views.runs_list, name='runs_list'),
    path('project/<int:project_id>/files/', views.files_list, name='files_list'),
    
    # Run management
    path('project/<int:project_id>/new-run-modal/', views.new_run_modal, name='new_run_modal'),
    path('project/<int:project_id>/create-run/', views.create_run, name='create_run'),
    path('run/<int:pk>/processing/', views.run_processing, name='run_processing'),
    path('run/<int:pk>/check-status/', views.check_run_status, name='check_run_status'),
    path('run/<int:pk>/delete/', views.delete_run, name='delete_run'),
    
    # File management
    path('project/<int:project_id>/upload-file-modal/', views.upload_file_modal, name='upload_file_modal'),
    path('project/<int:project_id>/upload-file/', views.upload_file, name='upload_file'),
    path('file/<int:pk>/delete/', views.delete_file, name='delete_file'),
    path('file/<int:file_id>/runs/<int:project_id>/', views.file_runs_modal, name='file_runs_modal'),
    
    # Run review views (existing)
    path('run/<int:pk>/review/', views.run_review, name='run_review'),
    path('run/<int:pk>/equipment/', views.get_equipment_row, name='get_equipment_row'),
    path('run/<int:pk>/submit-review/', views.submit_review, name='submit_review'),
    path('run/<int:pk>/save-progress/', views.save_progress, name='save_progress'),
    
    # Completed run view
    path('run/<int:pk>/completed/', views.run_completed, name='run_completed'),
    
    # Export endpoints
    path('run/<int:pk>/export/csv/', views.export_equipment_csv, name='export_equipment_csv'),
    path('run/<int:pk>/export/description/', views.export_description, name='export_description'),
]