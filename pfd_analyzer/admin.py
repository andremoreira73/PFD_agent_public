# pfd_analyzer/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import PFDFile, PFDRun

@admin.register(PFDFile)
class PFDFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'uploaded_by', 'uploaded_at', 'run_count']
    list_filter = ['uploaded_at', 'uploaded_by']
    search_fields = ['name']
    readonly_fields = ['uploaded_at']
    
    def run_count(self, obj):
        return obj.runs.count()
    run_count.short_description = 'Runs'

@admin.register(PFDRun)
class PFDRunAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'pfd_file_name', 'model', 'created_by', 'created_at', 
        'accuracy', 'related_run_display', 'is_locked_display', 'total_tokens'
    ]
    list_filter = [
        'model', 'is_locked', 'created_at', 'prompt_system', 'prompt_user'
    ]
    search_fields = ['pfd_file__name', 'model', 'response_id']
    readonly_fields = ['created_at', 'updated_at', 'locked_at', 'locked_by']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('pfd_file', 'model', 'prompt_system', 'prompt_user', 'parameters')
        }),
        ('Run Relationships', {  # New section
            'fields': ('related_run', 'relationship_description'),
            'description': 'Connect this run to other runs to track dependencies and workflow'
        }),
        ('LLM Response', {
            'fields': ('response_id', 'llm_output_markdown', 'is_locked', 'locked_at', 'locked_by'),
            'classes': ('collapse',)
        }),
        ('Token Usage', {
            'fields': ('tokens_input', 'tokens_output_text', 'tokens_output_reasoning'),
            'classes': ('collapse',)
        }),
        ('Evaluation', {
            'fields': (
                'true_positives', 'false_positives', 'true_negatives', 'false_negatives',
                'text_style_score'
            )
        }),
        ('Comments', {
            'fields': ('comments_markdown',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def pfd_file_name(self, obj):
        return obj.pfd_file.name
    pfd_file_name.short_description = 'PDF File'


    def related_run_display(self, obj):
        if obj.related_run:
            return format_html(
                '<a href="/admin/pfd_analyzer/pfdrun/{}/change/">Run #{}</a>',
                obj.related_run.pk,
                obj.related_run.pk
            )
        return '-'
    related_run_display.short_description = 'Related Run'

    
    def is_locked_display(self, obj):
        if obj.is_locked:
            return format_html('<span style="color: red;">Locked</span>')
        return format_html('<span style="color: green;">Unlocked</span>')
    is_locked_display.short_description = 'Status'