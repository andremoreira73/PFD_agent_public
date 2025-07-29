
# pfd_bench/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Project, ProjectFile, Run, EquipmentReview, ProjectFileLink

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'file_count', 'run_count']
    list_filter = ['created_at', 'created_by']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def file_count(self, obj):
        return obj.files.count()
    file_count.short_description = 'Files'
    
    def run_count(self, obj):
        return obj.runs.count()
    run_count.short_description = 'Runs'

@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'file_type', 'uploaded_by', 'uploaded_at', 'get_projects']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['name', 'file_hash']
    readonly_fields = ['uploaded_at', 'file_hash', 'file_size']
    
    def get_projects(self, obj):
        """Display projects using this file"""
        return ", ".join([p.name for p in obj.projects.all()])
    get_projects.short_description = 'Projects'


@admin.register(ProjectFileLink)
class ProjectFileLinkAdmin(admin.ModelAdmin):
    list_display = ['file', 'project', 'added_by', 'added_at']
    list_filter = ['added_at', 'project']
    readonly_fields = ['added_at']

@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'project', 'status', 'created_by', 'created_at', 'status_display']
    list_filter = ['status', 'created_at', 'project']
    search_fields = ['name', 'project__name']
    readonly_fields = ['created_at', 'completed_at', 'review_progress']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('project', 'file', 'name', 'status')
        }),
        ('Review State', {
            'fields': ('review_state', 'generated_table', 'review_progress'),
            'classes': ('collapse',),
            'description': 'Review state is automatically managed by the system'
        }),
        ('Generated Content', {
            'fields': ('generated_text',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'completed_by', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_display(self, obj):
        colors = {
            'pending': 'gray',
            'processing': 'blue',
            'draft': 'yellow',
            'under_review': 'orange',
            'completed': 'green',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def review_progress(self, obj):
        state = obj.review_state or {}
        reviewed = len(state.get('reviewed_indices', []))
        total = len(state.get('equipment_data', {})) or 6  # Using 6 as default from SAMPLE_TABLE
        return f"{reviewed}/{total} items reviewed"
    review_progress.short_description = 'Progress'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(EquipmentReview)
class EquipmentReviewAdmin(admin.ModelAdmin):
    list_display = ['run', 'equipment_index', 'has_changes', 'reviewed_by', 'reviewed_at']
    list_filter = ['has_changes', 'reviewed_at', 'run__project']
    readonly_fields = ['reviewed_at']
