from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import os

class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    use_ldap = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_upload_dir(self):
        path = os.path.join(settings.UPLOAD_ROOT, self.email)
        os.makedirs(path, exist_ok=True)
        return path

class Upload(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('uploading', 'Uploading'),
        ('failed', 'Failed'),
        ('success', 'Success'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retry_count = models.IntegerField(default=0)
    task_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

class UploadFile(models.Model):
    upload = models.ForeignKey(Upload, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Upload.STATUS_CHOICES, default='submitted')

class Notification(models.Model):
    TYPE_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('info', 'Information'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    related_upload = models.ForeignKey(Upload, null=True, blank=True, on_delete=models.SET_NULL)
