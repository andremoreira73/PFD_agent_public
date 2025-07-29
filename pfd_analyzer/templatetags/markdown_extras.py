from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
import markdown2
import re

register = template.Library()

@register.filter
@stringfilter
def render_markdown(value):
    html = markdown2.markdown(value, extras=['tables', 'fenced-code-blocks', 'code-friendly'])
    
    # Add Tailwind classes to tables
    html = re.sub(r'<table>', r'<table class="w-full border-collapse border border-gray-300 mb-4">', html)
    html = re.sub(r'<th>', r'<th class="border border-gray-300 bg-gray-100 px-3 py-2 text-left font-semibold">', html)
    html = re.sub(r'<td>', r'<td class="border border-gray-300 px-3 py-2">', html)
    html = re.sub(r'<thead>', r'<thead class="bg-gray-50">', html)
    
    return mark_safe(html)