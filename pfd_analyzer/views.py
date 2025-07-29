# pfd_analyzer/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Q
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView
)
from django.urls import reverse_lazy
from .models import PFDFile, PFDRun
from .forms import PFDFileForm, PFDRunForm

# Helper function to check if user has analyzer access
def has_analyzer_access(user):
    return user.is_staff  # or user.groups.filter(name='PFD_Analysts').exists()

# Mixin for class-based views
class AnalyzerAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return has_analyzer_access(self.request.user)
    
    def handle_no_permission(self):
        messages.error(self.request, 'You do not have permission to access the PFD Analyzer.')
        return redirect('pfd_bench:dashboard')  # Redirect to bench app

class DashboardView(LoginRequiredMixin, AnalyzerAccessMixin, TemplateView):
    template_name = 'pfd_analyzer/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_runs'] = PFDRun.objects.select_related('pfd_file', 'created_by')[:5]
        context['recent_files'] = PFDFile.objects.select_related('uploaded_by')[:5]
        context['total_runs'] = PFDRun.objects.count()
        context['total_files'] = PFDFile.objects.count()
        return context

# PDF File Views
class PFDFileCreateView(LoginRequiredMixin, AnalyzerAccessMixin, CreateView):
    model = PFDFile
    form_class = PFDFileForm
    template_name = 'pfd_analyzer/upload_pdf.html'
    success_url = reverse_lazy('file_list')
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        messages.success(self.request, 'PDF uploaded successfully!')
        return super().form_valid(form)

class PFDFileListView(LoginRequiredMixin, AnalyzerAccessMixin, ListView):
    model = PFDFile
    template_name = 'pfd_analyzer/file_list.html'
    context_object_name = 'files'
    paginate_by = 20

class PFDFileDetailView(LoginRequiredMixin, AnalyzerAccessMixin, DetailView):
    model = PFDFile
    template_name = 'pfd_analyzer/file_detail.html'
    context_object_name = 'file'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['runs'] = self.object.runs.select_related('created_by').all()
        return context

# PFD Run Views
class PFDRunCreateView(LoginRequiredMixin, AnalyzerAccessMixin, CreateView):
    model = PFDRun
    form_class = PFDRunForm
    template_name = 'pfd_analyzer/new_run.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'New run created successfully!')
        return super().form_valid(form)

class PFDRunDetailView(LoginRequiredMixin, AnalyzerAccessMixin, DetailView):
    model = PFDRun
    template_name = 'pfd_analyzer/run_detail.html'
    context_object_name = 'run'

class PFDRunUpdateView(LoginRequiredMixin, AnalyzerAccessMixin, UpdateView):
    model = PFDRun
    form_class = PFDRunForm
    template_name = 'pfd_analyzer/run_edit.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_editing'] = True
        
        # Add current related run display text
        if self.object.related_run:
            if self.object.related_run.name:
                context['current_related_run_text'] = f"{self.object.related_run.name} - {self.object.related_run.pfd_file.name}"
            else:
                context['current_related_run_text'] = f"Run #{self.object.related_run.pk} - {self.object.related_run.pfd_file.name}"
        else:
            context['current_related_run_text'] = ""
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Run updated successfully!')
        return super().form_valid(form)

class PFDRunListView(LoginRequiredMixin, AnalyzerAccessMixin, ListView):
    model = PFDRun
    template_name = 'pfd_analyzer/run_list.html'
    context_object_name = 'runs'
    paginate_by = 20
    
    def get_queryset(self):
        return PFDRun.objects.select_related('pfd_file', 'created_by', 'locked_by').all()

# Lock/Unlock functionality
@login_required
@user_passes_test(has_analyzer_access, redirect_field_name=None)
def lock_run(request, pk):
    run = get_object_or_404(PFDRun, pk=pk)
    if not run.is_locked:
        run.lock(request.user)
        messages.success(request, 'Run locked successfully. LLM output is now protected.')
    else:
        messages.info(request, 'Run is already locked.')
    return redirect('run_detail', pk=pk)

@login_required
@user_passes_test(has_analyzer_access, redirect_field_name=None)
def unlock_run(request, pk):
    run = get_object_or_404(PFDRun, pk=pk)
    if run.is_locked:
        run.unlock(request.user)
        messages.warning(request, 'Run unlocked. LLM output can now be edited.')
    else:
        messages.info(request, 'Run is already unlocked.')
    return redirect('run_detail', pk=pk)

@login_required
@user_passes_test(has_analyzer_access, redirect_field_name=None)
def search_runs(request):
    query = request.GET.get('search_query', '')
    current_run_id = request.GET.get('current_run_id')  # To exclude current run when editing
    
    runs = PFDRun.objects.all()
    if current_run_id:
        runs = runs.exclude(pk=current_run_id)
    
    if query:
        runs = runs.filter(
            Q(name__icontains=query) | 
            Q(pfd_file__name__icontains=query) |
            Q(pk__icontains=query)
        ).select_related('pfd_file')[:10]  # Limit to 10 results
    else:
        runs = runs.select_related('pfd_file')[:10]
    
    return render(request, 'pfd_analyzer/partials/run_search_results.html', {
        'runs': runs
    })