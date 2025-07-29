# pfd_bench/utils.py
import hashlib
import os
from django.core.files.base import ContentFile
from .models import ProjectFile, ProjectFileLink


def calculate_file_hash(file):
    """Calculate SHA256 hash of uploaded file"""
    hasher = hashlib.sha256()
    file.seek(0)  # Ensure we're at the start
    for chunk in file.chunks():
        hasher.update(chunk)
    file.seek(0)  # Reset file pointer
    return hasher.hexdigest()


def handle_file_upload(uploaded_file, user, project=None):
    """
    Handle file upload with deduplication
    Returns: (project_file, created, project_link)
    """
    # Calculate hash
    file_hash = calculate_file_hash(uploaded_file)
    
    # Check if file already exists
    try:
        project_file = ProjectFile.objects.get(file_hash=file_hash)
        created = False
    except ProjectFile.DoesNotExist:
        # Create new project file
        project_file = ProjectFile(
            name=uploaded_file.name,
            file_hash=file_hash,
            file_size=uploaded_file.size,
            file_type='dxf' if uploaded_file.name.endswith('.dxf') else 'other',
            uploaded_by=user
        )
        project_file.file.save(uploaded_file.name, uploaded_file, save=True)
        created = True
    
    # Link to project if provided
    project_link = None
    if project:
        project_link, _ = ProjectFileLink.objects.get_or_create(
            project=project,
            file=project_file,
            defaults={
                'added_by': user,
            }
        )
    
    return project_file, created, project_link


def cleanup_orphaned_files():
    """
    Remove files with no project links and no runs.
    This is the TRUE definition of orphaned files.
    """
    from .models import ProjectFile
    
    # Find truly orphaned files (no projects AND no runs)
    orphaned = ProjectFile.objects.filter(
        projects__isnull=True,  # No projects linked
        runs__isnull=True       # No runs using this file
    ).distinct()
    
    count = orphaned.count()
    space_freed = 0
    
    for file in orphaned:
        # Delete physical file
        if file.file:
            space_freed += file.file_size
            file.file.delete()
        file.delete()
    
    if count > 0:
        print(f"Cleaned up {count} orphaned files, freed {space_freed / 1024 / 1024:.1f} MB")
    
    return count
