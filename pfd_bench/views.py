# pfd_bench/views.py
# 

import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q
from django.urls import reverse

import csv

from .models import Project, Run, ProjectFile, ProjectFileLink
#from .mock_data import SAMPLE_TABLE, generate_mock_equipment_row  # for dev and debug
from .tasks import process_pfd_extraction_step_1, process_pfd_extraction_step_2

logger = logging.getLogger(__name__)

def get_review_state(run):
    """Get review state from the Run model"""
    state = run.review_state or {}
    
    # Ensure required keys exist
    if 'reviewed_indices' not in state:
        state['reviewed_indices'] = []
    if 'equipment_data' not in state:
        state['equipment_data'] = {}
    if 'current_index' not in state:
        state['current_index'] = 0
    
    # Convert list to set for reviewed_indices (for easier operations)
    state['reviewed_indices'] = set(state['reviewed_indices'])
    return state


def save_review_state(run, state):
    """Save review state to the Run model"""
    # Convert set to list for JSON serialization
    state_copy = state.copy()
    state_copy['reviewed_indices'] = list(state['reviewed_indices'])
    
    run.review_state = state_copy
    run.save()


def get_next_unreviewed_index(state, total_equipment):
    """Find the next unreviewed index"""
    for i in range(total_equipment):
        if i not in state['reviewed_indices']:
            return i
    return 0  # All reviewed, return to start



@login_required
def save_progress(request, pk):
    """Handle the Save Progress button from the header"""
    if request.method == 'POST':
        run = get_object_or_404(Run, pk=pk)
        
        if run.status == 'completed':
            return HttpResponse("This run is completed and cannot be edited.", status=403)
        
        # Just save the current state
        run.status = 'draft'
        run.save()
        
        return HttpResponse("""
            <span class="text-green-600">
                <i class="fas fa-check mr-1"></i>Progress saved!
            </span>
        """, headers={'HX-Trigger': 'progressSaved'})


@login_required
def export_equipment_csv(request, pk):
    """Export equipment table as CSV"""
    run = get_object_or_404(Run, pk=pk)
    
    # Create HTTP response with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{run.name}_equipment.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Tag', 'Equipment Type', 'Inlet Streams', 'Inlet Count', 
                     'Outlet Streams', 'Outlet Count', 'Remarks', 'Modified'])
    
    # Get the final equipment data (with user modifications)
    state = run.review_state or {}
    equipment_data = state.get('equipment_data', {})
    
    # Write equipment rows
    for idx, item in enumerate(run.generated_table):
        # Start with original data
        row_data = item.copy()
        
        # Apply user modifications if any
        if str(idx) in equipment_data:
            row_data.update(equipment_data[str(idx)])
        
        # Check if modified
        modified = 'Yes' if str(idx) in equipment_data else 'No'
        
        writer.writerow([
            row_data.get('tag', ''),
            row_data.get('equipment_type', ''),
            row_data.get('inlet_streams', ''),
            row_data.get('inlet_count', ''),
            row_data.get('outlet_streams', ''),
            row_data.get('outlet_count', ''),
            row_data.get('remarks', ''),
            modified
        ])
    
    return response

@login_required
def export_description(request, pk):
    """Export process description as text file"""
    run = get_object_or_404(Run, pk=pk)
    
    if not run.generated_text:
        messages.error(request, "No process description available")
        return redirect('pfd_bench:run_completed', pk=pk)
    
    # Create HTTP response with text header
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{run.name}_process_description.txt"'
    
    # Write content
    response.write(f"Process Description for: {run.name}\n")
    response.write(f"Project: {run.project.name}\n")
    response.write(f"DXF File: {run.project_file.name}\n")
    response.write(f"Generated: {run.completed_at.strftime('%B %d, %Y at %I:%M %p')}\n")
    response.write("=" * 60 + "\n\n")
    response.write(run.generated_text)
    
    return response

# Add this to pfd_bench/views.py

@login_required
def check_run_status(request, pk):
    """Check run status for auto-refresh (HTMX)"""
    run = get_object_or_404(Run, pk=pk)
    
    # If processing is complete, redirect to review
    if run.status in ['ready_for_review', 'under_review']:
        response = HttpResponse(status=303)
        response['Location'] = reverse('pfd_bench:run_review', args=[run.id])
        return response
    
    # If failed, redirect to project with error message
    if run.status == 'failed':
        messages.error(request, f"Processing failed: {run.processing_error}")
        response = HttpResponse(status=303)
        response['Location'] = reverse('pfd_bench:project_detail', args=[run.project.id])
        return response
    
    # Still processing
    return HttpResponse(status=200)



@login_required
def create_run(request, project_id):
    """Create a new run and start processing"""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    
    # Get run name
    run_name = request.POST.get('name', '').strip()
    if not run_name:
        messages.error(request, "Run name is required")
        return redirect('pfd_bench:project_detail', pk=project_id)
    
    # Handle file selection/upload
    project_file = None
    
    # Check if existing file was selected
    file_id = request.POST.get('project_file_id')
    if file_id:
        # Fix: Use projects__in instead of project=
        project_file = get_object_or_404(ProjectFile, pk=file_id, projects__in=[project])
    
    # Check if new file was uploaded
    elif 'project_file' in request.FILES:
        uploaded_file = request.FILES['project_file']
        if uploaded_file.name.endswith('.dxf'):
            # Create the file
            project_file = ProjectFile.objects.create(
                file=uploaded_file,
                name=uploaded_file.name,
                file_type='dxf',
                uploaded_by=request.user
            )
            # Link it to the project
            ProjectFileLink.objects.create(
                project=project,
                file=project_file,
                added_by=request.user
            )
        else:
            messages.error(request, "Please upload a valid DXF file")
            return redirect('pfd_bench:project_detail', pk=project_id)
    
    if not project_file:
        messages.error(request, "Please select or upload a DXF file")
        return redirect('pfd_bench:project_detail', pk=project_id)
    
    # Create the run
    run = Run.objects.create(
        project=project,
        name=run_name,
        file=project_file,
        created_by=request.user
    )
    
    # Start processing - mock up only
    #run.start_processing()

    process_pfd_extraction_step_1.delay(run.id)
    
    # Redirect to processing status page
    response = HttpResponse(status=204)
    response['HX-Redirect'] = reverse('pfd_bench:run_processing', kwargs={'pk': run.id})
    return response




@login_required
def delete_run(request, pk):
    """Delete a run (HTMX)"""
    if request.method != 'DELETE':
        return HttpResponse("Method not allowed", status=405)
    
    run = get_object_or_404(Run, pk=pk)
    project = run.project
    
    # Check permissions
    if request.user != run.created_by and request.user != project.created_by:
        return HttpResponse("Unauthorized", status=403)
    
    run.delete()
    
    # Return updated runs list
    return runs_list(request, project.id)




@login_required
def delete_file(request, pk):
    """Delete a file and all associated runs (HTMX)"""
    if request.method != 'DELETE':
        return HttpResponse("Method not allowed", status=405)
    
    project_file = get_object_or_404(ProjectFile, pk=pk)
    
    # Get the first project this file belongs to (for returning the updated list)
    project = project_file.projects.first()
    
    # Check permissions
    if request.user != project_file.uploaded_by and request.user != project.created_by:
        return HttpResponse("Unauthorized", status=403)
    
    project_file.delete()
    
    # Return updated files list
    return files_list(request, project.id)

@login_required
def delete_file(request, pk):
    """Delete a project's link to a file (only if no runs exist)"""
    if request.method != 'DELETE':
        return HttpResponse("Method not allowed", status=405)
    
    project_file = get_object_or_404(ProjectFile, pk=pk)
    project_id = request.GET.get('project_id')
    if not project_id:
        return HttpResponse("Project ID required", status=400)
    
    project = get_object_or_404(Project, pk=project_id)
    
    # Check permissions
    if request.user != project.created_by:
        return HttpResponse("Unauthorized", status=403)
    
    # Check if this file has any runs in THIS project
    runs_in_project = project_file.runs.filter(project=project).count()
    
    if runs_in_project > 0:
        # Prevent deletion - return an error message
        return HttpResponse(f"""
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                 onclick="if(event.target === this) this.remove()">
                <div class="bg-white rounded-lg p-6 max-w-md">
                    <div class="flex items-start mb-4">
                        <i class="fas fa-exclamation-triangle text-yellow-500 text-2xl mr-3"></i>
                        <div>
                            <h3 class="text-lg font-semibold">Cannot Delete File</h3>
                            <p class="text-gray-600 mt-2">
                                This file is currently used by {runs_in_project} run{'s' if runs_in_project > 1 else ''} 
                                in this project and cannot be deleted.
                            </p>
                            <p class="text-sm text-gray-500 mt-2">
                                To delete this file, you must first delete all associated runs.
                            </p>
                        </div>
                    </div>
                    <div class="flex items-center justify-between mt-6">
                        <a href="{reverse('pfd_bench:project_detail', args=[project.id])}" 
                           class="text-blue-600 hover:text-blue-800 text-sm">
                            View runs using this file
                        </a>
                        <button onclick="this.closest('.fixed').remove()"
                                class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
                            OK
                        </button>
                    </div>
                </div>
            </div>
        """, headers={'HX-Reswap': 'afterbegin', 'HX-Retarget': 'body'})
    
    # File has no runs in this project, safe to unlink
    ProjectFileLink.objects.filter(project=project, file=project_file).delete()
    
    # Check if file is now truly orphaned (no projects AND no runs anywhere)
    if project_file.projects.count() == 0 and project_file.runs.count() == 0:
        # Delete the physical file
        if project_file.file:
            project_file.file.delete()
        project_file.delete()
        logger.info(f"Deleted orphaned file: {project_file.name}")
    
    # Return updated files list
    return files_list(request, project.id)


@login_required
def delete_file(request, pk):
    """Delete a project's link to a file (HTMX)"""
    if request.method != 'DELETE':
        return HttpResponse("Method not allowed", status=405)
    
    project_file = get_object_or_404(ProjectFile, pk=pk)
    
    # We need to know which project we're removing it from
    # This should come from the context (the page we're on)
    project_id = request.GET.get('project_id')
    if not project_id:
        # Try to infer from referer or return error
        return HttpResponse("Project ID required", status=400)
    
    project = get_object_or_404(Project, pk=project_id)
    
    # Check permissions - user should own the project
    if request.user != project.created_by:
        return HttpResponse("Unauthorized", status=403)
    
    # Delete the link between project and file
    ProjectFileLink.objects.filter(project=project, file=project_file).delete()
    
    # Check and clean up orphaned files immediately
    from .utils import cleanup_orphaned_files
    cleanup_orphaned_files()
    
    # Return updated files list
    return files_list(request, project.id)


@login_required
def upload_file(request, project_id):
    """Handle file upload"""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    
    if 'file' not in request.FILES:
        messages.error(request, "No file provided")
        return files_list(request, project_id)
    
    uploaded_file = request.FILES['file']
    if not uploaded_file.name.endswith('.dxf'):
        messages.error(request, "Please upload a valid DXF file")
        return files_list(request, project_id)
    
    # Use the utility function that handles deduplication
    from .utils import handle_file_upload
    project_file, created, project_link = handle_file_upload(uploaded_file, request.user, project)
    
    if created:
        messages.success(request, f"File '{uploaded_file.name}' uploaded successfully")
    else:
        messages.info(request, f"File '{uploaded_file.name}' already exists, linked to project")
    
    return files_list(request, project_id)





@login_required
def create_project(request):
    """Create a new project"""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    
    if not name:
        messages.error(request, "Project name is required")
        return redirect('pfd_bench:project_list')
    
    project = Project.objects.create(
        name=name,
        description=description,
        created_by=request.user
    )
    
    messages.success(request, f"Project '{name}' created successfully!")
    return redirect('pfd_bench:project_detail', pk=project.id)



############################################################
#######################  main pages ########################




@login_required
def project_detail(request, pk):
    """Show project with runs and files"""
    project = get_object_or_404(Project, pk=pk, created_by=request.user)
    return render(request, 'pfd_bench/project_detail.html', {'project': project})


@login_required
def project_list(request):
    """List all projects for the current user"""
    projects = Project.objects.filter(created_by=request.user)
    return render(request, 'pfd_bench/project_list.html', {'projects': projects})



@login_required
def run_completed(request, pk):
    """Show completed run view"""
    run = get_object_or_404(Run, pk=pk)
    
    if run.status != 'completed':
        return redirect('pfd_bench:run_review', pk=pk)
    
    # Calculate basic stats
    stats = {
        'total_equipment': run.equipment_count,
        'modifications_made': len(run.review_state.get('equipment_data', {})),
    }
    
    return render(request, 'pfd_bench/run_completed.html', {
        'run': run,
        'stats': stats
    })



@login_required
def run_processing(request, pk):
    """Show processing status page"""
    run = get_object_or_404(Run, pk=pk)
    
    # For now, simulate completion with mock data
    #if run.status == 'processing':
    #    run.complete_processing(run.generated_table)
    
    return render(request, 'pfd_bench/run_processing.html', {'run': run})



@login_required
def run_review(request, pk):
    run = get_object_or_404(Run, pk=pk)
    
    # Check if run is completed or frozen during text generation
    if run.status in ['completed', 'generating_description']:
        if run.status == 'generating_description':
            # Redirect to a processing page or back to project
            messages.info(request, "This run is generating the process description...")
            return redirect('pfd_bench:project_detail', pk=run.project.pk)
        else:
            return redirect('pfd_bench:run_completed', pk=pk)
    
    # Clear state on page load if requested (for testing)
    if request.GET.get('reset') == '1':
        run.review_state = {}
        run.status = 'draft'
        run.save()
        messages.info(request, "Review state has been reset.")
    
    # Set status to under_review if it's ready
    if run.status == 'ready_for_review':
        run.status = 'under_review'
        run.save()
    
    context = {
        'run': run,
        'total_equipment': len(run.generated_table),  # Use actual data!
    }
    return render(request, 'pfd_bench/run_review.html', context)




############################################################
######################### partials #########################


@login_required
def runs_list(request, project_id):
    """HTMX partial for filtered runs list"""
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    runs = project.runs.all()
    
    
    # Apply search filter
    search = request.GET.get('search', '')
    if search:
        runs = runs.filter(
            Q(name__icontains=search) | 
            Q(project_file__name__icontains=search)
        )
    
    # Apply status filter
    status = request.GET.get('status', '')
    if status:
        runs = runs.filter(status=status)
    
        
    return render(request, 'pfd_bench/partials/runs_list.html', {
        'runs': runs,
        'project': project
    })


@login_required
def submit_review(request, pk):
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    run = get_object_or_404(Run, pk=pk)
    
    # Check if run is completed/frozen
    if run.status == 'completed':
        return HttpResponse("This run is completed and cannot be edited.", status=403)
    
    action = request.POST.get('action')
    index = int(request.POST.get('equipment_index', 0))
    state = get_review_state(run)
    
    # Debug: Print all POST data
    logger.info(f"Action: {action}, Index: {index}")
    logger.info(f"All POST data: {dict(request.POST)}")
    
    # Handle different actions
    if action == 'approve':
        # Mark as reviewed, discard any unsaved changes
        state['reviewed_indices'].add(index)
        # Remove any saved changes for this index
        if str(index) in state['equipment_data']:
            del state['equipment_data'][str(index)]
    
    elif action in ['submit_changes', 'save', 'save_draft']:
        # Save the changed data
        changes = {}
        
        # Get all the fields that might have been edited
        for field in ['tag', 'equipment_type', 'inlet_streams', 'outlet_streams', 'remarks']:
            if field in request.POST:
                value = request.POST.get(field)
                if value:  # Only save if there's a value
                    changes[field] = value
        
        if changes:
            state['equipment_data'][str(index)] = changes
            logger.info(f"Saved changes for equipment at index {index}: {changes}")
        
        if action == 'submit_changes':
            # Mark as reviewed when submitting changes
            state['reviewed_indices'].add(index)

        elif action == 'save_draft':
            # Save as draft and redirect
            run.status = 'draft'
            save_review_state(run, state)  # Important: save state before redirect
            messages.success(request, "Progress saved as draft.")
            # HTMX redirect - this tells the browser to navigate to the new page
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('pfd_bench:project_detail', kwargs={'pk': run.project.pk})
            return response
    
    elif action == 'finalize_run':
        # Complete the run and freeze it
        run.status = 'generating_description'
        run.completed_at = timezone.now()
        run.completed_by = request.user
        messages.success(request, "Run has been finalized and is now locked.")

        logger.info(f"Finalizing run: Generating the process description text for run {run.id}")
        
        # Trigger text generation workflow
        process_pfd_extraction_step_2.delay(run.id)
        
        save_review_state(run, state)
        # HTMX redirect
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('pfd_bench:project_detail', kwargs={'pk': run.project.pk})
        return response
    
    save_review_state(run, state)
    
    # Determine next index
    if action in ['approve', 'submit_changes']:
        # Move to next unreviewed
        next_index = get_next_unreviewed_index(state, len(run.generated_table))
        # If all reviewed, just go to next sequential
        if next_index == 0 and len(state['reviewed_indices']) == len(run.generated_table):
            next_index = min(index + 1, len(run.generated_table) - 1)
    else:
        # Stay on current (for save action)
        next_index = index
    
    # Get the equipment for the next index
    
    equipment = run.generated_table[next_index].copy()
    equipment['index'] = next_index

    if not equipment:
        return HttpResponse("Error: Equipment not found")
    
    # Apply state to equipment
    equipment['reviewed'] = next_index in state['reviewed_indices']
    if str(next_index) in state['equipment_data']:
        equipment.update(state['equipment_data'][str(next_index)])
    
    # Update navigation state
    state['current_index'] = next_index
    next_unreviewed = get_next_unreviewed_index(state, len(run.generated_table))
    is_sequential = (next_index == next_unreviewed) or all(i in state['reviewed_indices'] for i in range(next_index))
    
    # Check if all reviewed
    all_reviewed = len(state['reviewed_indices']) == len(run.generated_table)
    
    # Build sidebar data
    all_equipment = []
    for i, item in enumerate(run.generated_table):
        equip_data = {
            'index': i,
            'tag': item['tag'],
            'equipment_type': item['equipment_type'],
            'has_changes': str(i) in state.get('equipment_data', {})
        }
        all_equipment.append(equip_data)
    
    save_review_state(run, state)
    
    # Render the response
    return render(request, 'pfd_bench/partials/equipment_review.html', {
        'equipment': equipment,
        'run': run,
        'run_id': pk,
        'total_equipment': len(run.generated_table),
        'next_unreviewed_index': next_unreviewed,
        'is_sequential': is_sequential,
        'all_equipment': all_equipment,
        'reviewed_indices': list(state['reviewed_indices']),
        'all_reviewed': all_reviewed,
    })


@login_required
def get_equipment_row(request, pk):
    run = get_object_or_404(Run, pk=pk)
    
    # Check if run is completed/frozen
    if run.status == 'completed':
        return HttpResponse("This run is completed and cannot be edited.", status=403)
    
    index = int(request.GET.get('index', 0))
    state = get_review_state(run)
    
    # Update current index
    state['current_index'] = index
    
    # Get equipment from actual data
    if index < len(run.generated_table):
        equipment = run.generated_table[index].copy()
        equipment['index'] = index
    else:
        return HttpResponse("No equipment found")
    
    # Check if this row was already reviewed
    equipment['reviewed'] = index in state['reviewed_indices']
    
    # If we have saved changes, apply them
    if str(index) in state['equipment_data']:
        saved_data = state['equipment_data'][str(index)]
        equipment.update(saved_data)
        logger.info(f"Applied saved changes for index {index}: {saved_data}")
    
    # Find next unreviewed index
    next_unreviewed = get_next_unreviewed_index(state, len(run.generated_table))
    
    # Check if user is in sequential review mode
    is_sequential = (index == next_unreviewed) or all(i in state['reviewed_indices'] for i in range(index))
    
    # Check if all reviewed
    all_reviewed = len(state['reviewed_indices']) == len(run.generated_table)
    
    # Build sidebar data
    all_equipment = []
    for i, item in enumerate(run.generated_table):
        equip_data = {
            'index': i,
            'tag': item['tag'],
            'equipment_type': item['equipment_type'],
            'has_changes': str(i) in state.get('equipment_data', {})
        }
        all_equipment.append(equip_data)
    
    save_review_state(run, state)
    
    return render(request, 'pfd_bench/partials/equipment_review.html', {
        'equipment': equipment,
        'run': run,
        'run_id': pk,
        'total_equipment': len(run.generated_table),
        'next_unreviewed_index': next_unreviewed,
        'is_sequential': is_sequential,
        'all_equipment': all_equipment,
        'reviewed_indices': list(state['reviewed_indices']),
        'all_reviewed': all_reviewed,
    })





@login_required
def files_list(request, project_id):
    """HTMX partial for filtered files list"""
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    
    # Annotate files with run counts for this specific project
    from django.db.models import Count, Q
    
    files = project.files.annotate(
        runs_in_project=Count('runs', filter=Q(runs__project=project)),
        total_runs=Count('runs')
    )
    
    # Apply search filter
    search = request.GET.get('search', '')
    if search:
        files = files.filter(name__icontains=search)
    
    # Process files to add computed data
    files_data = []
    for file in files:
        # Get other projects for this file
        other_projects = list(file.projects.exclude(id=project.id))
        
        files_data.append({
            'id': file.id,
            'name': file.name,
            'file_size_display': file.file_size_display,
            'uploaded_at': file.uploaded_at,
            'runs_count': file.runs_in_project,  # Use annotated value
            'total_projects': file.projects.count(),
            'other_projects': other_projects,
            'can_delete': file.runs_in_project == 0
        })
    
    return render(request, 'pfd_bench/partials/files_list.html', {
        'files': files_data,
        'project': project
    })


############################################################
######################### modals ##########################


@login_required
def new_run_modal(request, project_id):
    """Show new run modal"""
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    existing_files = project.files.all()
    
    return render(request, 'pfd_bench/partials/new_run_modal.html', {
        'project': project,
        'existing_files': existing_files
    })

@login_required
def upload_file_modal(request, project_id):
    """Show file upload modal"""
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    return render(request, 'pfd_bench/partials/upload_file_modal.html', {'project': project})


@login_required
def new_project_modal(request):
    """Show new project modal"""
    return render(request, 'pfd_bench/partials/new_project_modal.html')


@login_required
def file_runs_modal(request, file_id, project_id):
    """Show modal with runs using this file"""
    project_file = get_object_or_404(ProjectFile, pk=file_id)
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    
    # Get runs in this project using this file
    runs = project_file.runs.filter(project=project).select_related('created_by')
    
    return render(request, 'pfd_bench/partials/file_runs_modal.html', {
        'file': project_file,
        'project': project,
        'runs': runs
    })