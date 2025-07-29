"""
URL configuration for PFD_agent project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# PFD_agent/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # Home page at root
    path('', include('PFD_agent.auth_urls')),  # Auth URLs (login/logout)
    path('analyzer/', include('pfd_analyzer.urls', namespace='pfd_analyzer')),
    path('bench/', include('pfd_bench.urls', namespace='pfd_bench')), 
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Add browser reload URLs for development
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]



