# pfd_analyzer/forms.py

from django import forms
from .models import PFDFile, PFDRun

class PFDFileForm(forms.ModelForm):
    class Meta:
        model = PFDFile
        fields = ['name', 'file']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter a descriptive name for this PDF'
            }),
            'file': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': '.pdf'
            })
        }

class PFDRunForm(forms.ModelForm):
    class Meta:
        model = PFDRun
        fields = [
            'pfd_file', 'name', 'related_run', 'relationship_description',
            'model', 'prompt_system', 'prompt_user', 'parameters',
            'response_id', 'llm_output_markdown', 
            'tokens_input', 'tokens_output_text', 'tokens_output_reasoning',
            'true_positives', 'false_positives', 'true_negatives', 'false_negatives',
            'text_style_score', 'comments_markdown'
        ]
        widgets = {
            'pfd_file': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Optional: Give this run a descriptive name'
            }),
            'related_run': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'relationship_description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Describe how this run relates to the selected run (e.g., "Used the outcome of run #23 as input for this analysis")'
            }),
            'model': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., o3-2025-04-16, Gemini'
            }),
            'prompt_system': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., 2a, 3_worker'
            }),
            'prompt_user': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., 2b, 4_final'
            }),
            'parameters': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., reasoning effort: medium'
            }),
            'response_id': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'llm_output_markdown': forms.Textarea(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 15,
                'placeholder': 'Paste the LLM response here...'
            }),
            'tokens_input': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'tokens_output_text': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'tokens_output_reasoning': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'true_positives': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'false_positives': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'true_negatives': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'false_negatives': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'text_style_score': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'min': 0,
                'max': 100
            }),
            'comments_markdown': forms.Textarea(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 8,
                'placeholder': 'Add your analysis and comments here...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing a locked run, make certain fields readonly and add visual indicator
        if self.instance.pk and self.instance.is_locked:
            readonly_fields = ['llm_output_markdown', 'response_id', 'model', 
                             'prompt_system', 'prompt_user', 'parameters']
            for field_name in readonly_fields:
                widget = self.fields[field_name].widget
                widget.attrs.update({
                    'readonly': True,
                    'class': widget.attrs.get('class', '') + ' bg-gray-100 cursor-not-allowed'
                })
                self.fields[field_name].help_text = "This field is locked - unlock the run to edit"
        
        # Filter related_run to exclude the current instance to prevent self-reference
        instance = kwargs.get('instance')
        if instance:
            self.fields['related_run'].queryset = PFDRun.objects.exclude(pk=instance.pk)
        else:
            self.fields['related_run'].queryset = PFDRun.objects.all()
        
        # Make related_run field show more descriptive text
        self.fields['related_run'].empty_label = "Select a related run (optional)"
        
        # Custom queryset ordering for better UX
        self.fields['related_run'].queryset = self.fields['related_run'].queryset.order_by('-created_at')