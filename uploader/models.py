from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import os
import json
import logging

logger = logging.getLogger(__name__)

class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    use_ldap = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_upload_dir(self):
        path = os.path.join(settings.UPLOAD_ROOT, self.email.lower())
        os.makedirs(path, exist_ok=True)
        return path

class Upload(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('uploading', 'Uploading'),
        ('failed', 'Failed'),
        ('success', 'Success')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder_name = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='submitted')
    task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sample_count = models.IntegerField(default=0)  # Track number of samples
    irida_project_id = models.CharField(max_length=50, null=True, blank=True)
    irida_run_id = models.CharField(max_length=50, null=True, blank=True)  # New field for Run ID
    uploaded_samples = models.JSONField(default=list, blank=True)  # New field to store sample details
    retry_count = models.IntegerField(default=0)
    def update_from_status_file(self):
        """Updates the upload record with information from the status file"""
        status_file = os.path.join(self.get_full_path(), 'irida_uploader_status.info')
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    data = json.loads(f.read())
                    
                    # Update Run ID
                    self.irida_run_id = data.get('Run ID')
                    
                    # Update sample information
                    sample_status = data.get('Sample Status', [])
                    successful_samples = [
                        {
                            'name': s['Sample Name'],
                            'project_id': s['Project ID']  # Store Project ID from status file
                        }
                        for s in sample_status
                        if s.get('Uploaded') == 'True'
                    ]
                    
                    self.uploaded_samples = successful_samples
                    self.sample_count = len(successful_samples)
                    
                    # Update project ID if not already set
                    if not self.irida_project_id and successful_samples:
                        self.irida_project_id = successful_samples[0]['project_id']
                    
                    self.save()
                    return True
            except Exception as e:
                logger.error(f"Error updating from status file: {str(e)}")
        return False

    def get_file_info(self):
        """Returns the number of uploaded samples from the database"""
        return self.sample_count

    def get_full_path(self):
        """Returns the absolute path to the folder in UPLOAD_ROOT"""
        return os.path.join(settings.UPLOAD_ROOT, self.user.email, self.folder_name)

    def __str__(self):
        return f"{self.folder_name} ({self.status})"

    class Meta:
        ordering = ['-created_at']

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('info', 'Info'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    related_upload = models.ForeignKey(Upload, on_delete=models.CASCADE, null=True, blank=True)
