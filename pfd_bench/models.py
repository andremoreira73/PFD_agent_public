
# pfd_bench/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import hashlib
from django.core.files.storage import default_storage

import os


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name


class ProjectFile(models.Model):
    """File storage with deduplication by hash"""
    FILE_TYPES = [
        ('dxf', 'DXF Drawing'),
        ('pdf', 'PDF Document'),
        ('other', 'Other'),
    ]
    
    # File data
    file = models.FileField(upload_to='project_files/')
    name = models.CharField(max_length=255)  # Keep 'name' for compatibility
    file_hash = models.CharField(max_length=64, unique=True, db_index=True)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    
    # Many-to-many relationship with projects
    projects = models.ManyToManyField(Project, related_name='files', through='ProjectFileLink')
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.name
    
    def calculate_hash(self):
        """Calculate SHA256 hash of the file"""
        import hashlib
        hasher = hashlib.sha256()
        self.file.seek(0)
        for chunk in self.file.chunks():
            hasher.update(chunk)
        self.file.seek(0)
        return hasher.hexdigest()
    
    def save(self, *args, **kwargs):
        if self.file:
            if not self.file_hash:
                self.file_hash = self.calculate_hash()
            self.file_size = self.file.size
            if not self.name:  # Only set if not already provided
                self.name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)
        
    @property
    def file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def runs_count(self):
        """Total number of runs using this file"""
        return self.runs.count()
    
    @property
    def runs_count_in_project(self, project):
        """Number of runs using this file in a specific project"""
        return self.runs.filter(project=project).count()
    
    @property
    def is_deletable(self):
        """Check if file can be safely deleted (no runs)"""
        return self.runs_count == 0
    
    @property
    def projects_display(self):
        """Get a formatted list of projects using this file"""
        return ", ".join([p.name for p in self.projects.all()])
    
    def get_runs_by_project(self):
        """Get runs grouped by project"""
        from django.db.models import Count
        return self.runs.values('project__name').annotate(count=Count('id')).order_by('project__name')



class ProjectFileLink(models.Model):
    """Through model for ProjectFile-Project relationship"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    file = models.ForeignKey(ProjectFile, on_delete=models.PROTECT)
    
    # Link metadata
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['project', 'file']
        ordering = ['-added_at']



class Run(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('ready_for_review', 'Ready for Review'),
        ('under_review', 'Under Review'),
        ('draft', 'Draft'),
        ('generating_description', 'Generating Description'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='runs')
    name = models.CharField(max_length=200)
    file = models.ForeignKey(ProjectFile, on_delete=models.CASCADE, related_name='runs')
    #shared_file = models.ForeignKey(SharedFile, on_delete=models.PROTECT, related_name='runs')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    # Processing metadata
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    
    # Review state (JSON field to store progress)
    review_state = models.JSONField(default=dict, blank=True)
    """
    Note that review_state contain exclusively what has been modified. For instance:
    review_state = {
        'reviewed_indices': [0, 2, 3],     # Which rows have been reviewed
        'equipment_data': {                # Changes made to each row
            '0': {'tag': 'New-R010', 'inlet_streams': 'Modified inlet'},
            '2': {'equipment_type': 'Modified Thickener'}
        },
        'current_index': 3                 # Where the user currently is
    }
    """
    
    # Generated data
    generated_table = models.JSONField(default=dict, blank=True)  # The table generated by AI
    generated_text = models.TextField(blank=True)  # Final process description
    ai_confidence_scores = models.JSONField(default=dict, blank=True)  # Placeholder for confidence scores
    
    # Timestamps and users
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_runs')
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='completed_runs')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def equipment_count(self):
        """Total number of equipment items in the table"""
        if isinstance(self.generated_table, list):
            return len(self.generated_table)
        return 0
    
    @property
    def reviewed_count(self):
        """Number of equipment items reviewed"""
        state = self.review_state or {}
        return len(state.get('reviewed_indices', []))
    
    @property
    def progress_display(self):
        """Display review progress"""
        if self.status in ['under_review', 'ready_for_review']:
            return f"{self.reviewed_count}/{self.equipment_count} reviewed"
        return ""
    
    @property
    def has_modifications(self):
        """Check if user made any modifications"""
        state = self.review_state or {}
        return bool(state.get('equipment_data'))
    
    def start_processing(self):
        """Mark run as processing"""
        self.status = 'processing'
        self.processing_started_at = timezone.now()
        self.save()
    
    def complete_processing(self, table_data):
        """Mark processing as complete with generated table"""
        self.status = 'ready_for_review'
        self.processing_completed_at = timezone.now()
        self.generated_table = table_data
        self.save()
    
    def fail_processing(self, error_message):
        """Mark processing as failed"""
        self.status = 'failed'
        self.processing_completed_at = timezone.now()
        self.processing_error = error_message
        self.save()

    @property
    def final_equipment_table(self):
        """
        Returns the final equipment table with user modifications applied.
        This merges the original generated_table with any user changes.
        """
        if not self.generated_table:
            return []
        
        # Start with a deep copy of the original
        final_table = []
        state = self.review_state or {}
        equipment_data = state.get('equipment_data', {})
        
        for idx, item in enumerate(self.generated_table):
            # Copy original item
            row_data = item.copy()
            
            # Apply user modifications if any exist for this index
            if str(idx) in equipment_data:
                row_data.update(equipment_data[str(idx)])
            
            final_table.append(row_data)
        
        return final_table
    

    def final_table_to_markdown(self, title="Modified Table after Human Review"):
        """
        Convert the final equipment table (with user modifications) to markdown format.
        
        Args:
            title: Optional title for the table
            include_modifications: If True, adds a column showing which rows were modified
        
        Returns:
            Markdown formatted string
        """
        final_table = self.final_equipment_table
        if not final_table:
            return "No equipment data available."
        
        lines = []
        
        # Add title if present
        if title:
            lines.append(f"### {title}\n")
        
        # Header
        lines.append("| Tag | Equipment type | Inlet streams | Inlet count | Outlet streams | Outlet count | Remarks | Modified |")
        lines.append("|---|---|---|---|---|---|---|---|")
        
        # Get modification info
        state = self.review_state or {}
        equipment_data = state.get('equipment_data', {})
        
        # Rows
        for idx, row in enumerate(final_table):
            modified = "Yes" if str(idx) in equipment_data else "No"
            lines.append(
                f"| {row.get('tag', '')} | {row.get('equipment_type', '')} | "
                f"{row.get('inlet_streams', '')} | {row.get('inlet_count', '')} | "
                f"{row.get('outlet_streams', '')} | {row.get('outlet_count', '')} | "
                f"{row.get('remarks', '')} | {modified} |"
            )

        return "\n".join(lines)


    def original_table_to_markdown(self, title="Original AI-Generated Table"):
        """Convert the original generated table (without modifications) to markdown."""
        if not self.generated_table:
            return "No equipment data available."
        
        lines = []
        
        if title:
            lines.append(f"### {title}\n")
        
        # Header
        lines.append("| Tag | Equipment type | Inlet streams | Inlet count | Outlet streams | Outlet count | Remarks |")
        lines.append("|---|---|---|---|---|---|---|")
        
        # Rows
        for row in self.generated_table:
            lines.append(
                f"| {row.get('tag', '')} | {row.get('equipment_type', '')} | "
                f"{row.get('inlet_streams', '')} | {row.get('inlet_count', '')} | "
                f"{row.get('outlet_streams', '')} | {row.get('outlet_count', '')} | "
                f"{row.get('remarks', '')} |"
            )
        
        return "\n".join(lines)


class EquipmentReview(models.Model):
    """Track individual equipment reviews (optional, for audit trail)"""
    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name='reviews')
    equipment_index = models.IntegerField()  # Which row in the table
    
    # Original vs reviewed data
    original_data = models.JSONField()
    reviewed_data = models.JSONField(null=True, blank=True)
    has_changes = models.BooleanField(default=False)
    
    # Metadata
    reviewed_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['run', 'equipment_index']
        ordering = ['equipment_index']


