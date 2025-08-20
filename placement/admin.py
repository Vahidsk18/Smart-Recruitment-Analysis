# placement/admin.py
from django.contrib import admin
from .models import Job, Application

# If django.contrib.admin is REMOVED, this file will effectively do nothing.
try:
    if 'django.contrib.admin' in __import__('django.conf').settings.INSTALLED_APPS:
        admin.site.register(Job)
        admin.site.register(Application)
except Exception:
    pass