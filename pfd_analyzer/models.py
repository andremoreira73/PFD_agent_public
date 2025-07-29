
# pfd_analyzer/models.py

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

class PFDFile(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('pfd_file_detail', kwargs={'pk': self.pk})
    
    class Meta:
        ordering = ['-uploaded_at']

class PFDRun(models.Model):
    # Core identification
    pfd_file = models.ForeignKey(PFDFile, on_delete=models.CASCADE, related_name='runs')

    name = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Optional descriptive name for this run (defaults to run number if empty)"
    )

    # Run relationships - NEW FIELDS
    related_run = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='dependent_runs',
        help_text="Connect this run to another run it depends on or builds upon"
    )
    relationship_description = models.TextField(
        blank=True,
        help_text="Describe how this run relates to the connected run (e.g., 'Used the outcome of run #23 as input for this analysis')"
    )
    
    # Model & Prompt tracking
    model = models.CharField(max_length=100, help_text="e.g., o3-2025-04-16, Gemini")
    prompt_system = models.CharField(max_length=50, help_text="System prompt version (e.g., 2a, 3_worker)")
    prompt_user = models.CharField(max_length=50, help_text="User prompt version (e.g., 2b, 4_final)")
    parameters = models.CharField(max_length=200, help_text="e.g., reasoning effort: medium")
    
    # LLM Response (protected after lock)
    response_id = models.CharField(max_length=100, blank=True)
    llm_output_markdown = models.TextField(help_text="Original LLM response - paste here")
    
    # Protection mechanism
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='locked_runs'
    )
    
    # Token & Pricing tracking
    tokens_input = models.IntegerField(default=0)
    tokens_output_text = models.IntegerField(default=0)
    tokens_output_reasoning = models.IntegerField(default=0)
    
    # Evaluation Metrics
    true_positives = models.IntegerField(default=0)
    false_positives = models.IntegerField(default=0)
    true_negatives = models.IntegerField(default=0)
    false_negatives = models.IntegerField(default=0)
    text_style_score = models.IntegerField(default=0, help_text="Percentage 0-100")
    
    # Collaborative comments (always editable)
    comments_markdown = models.TextField(blank=True, help_text="Your analysis and comments")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    
    #def __str__(self):
    #    return f"Run #{self.pk} - {self.pfd_file.name} ({self.model})"
    
    def __str__(self):
        display_name = self.name if self.name else f"Run #{self.pk}"
        return f"{display_name} - {self.pfd_file.name} ({self.model})"
    
    def get_absolute_url(self):
        return reverse('run_detail', kwargs={'pk': self.pk})
    
    # Calculated properties
    @property
    def total_tokens(self):
        return self.tokens_input + self.tokens_output_text + self.tokens_output_reasoning
    
    @property
    def accuracy(self):
        total = self.true_positives + self.false_positives + self.true_negatives + self.false_negatives
        if total == 0:
            return 0
        return round((self.true_positives + self.true_negatives) / total * 100, 1)
    
    @property
    def precision(self):
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0
        return round(self.true_positives / denominator * 100, 1)
    
    @property
    def recall(self):
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0
        return round(self.true_positives / denominator * 100, 1)
    
    # Locking methods
    def lock(self, user):
        """Lock the LLM output fields"""
        self.is_locked = True
        self.locked_at = timezone.now()
        self.locked_by = user
        self.save()
    
    def unlock(self, user):
        """Unlock the LLM output fields"""
        self.is_locked = False
        self.locked_at = None
        self.locked_by = None
        self.save()
    
    # Helper methods for relationships
    def get_related_runs_chain(self):
        """Get the chain of related runs starting from this run going backwards"""
        chain = []
        current = self
        visited = set()  # Prevent infinite loops
        
        while current.related_run and current.related_run.pk not in visited:
            visited.add(current.pk)
            chain.append(current.related_run)
            current = current.related_run
            
        return chain
    
    def get_dependent_runs_tree(self):
        """Get all runs that depend on this one"""
        return self.dependent_runs.all()
    
    
    class Meta:
        ordering = ['-created_at']