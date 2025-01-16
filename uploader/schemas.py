from ninja import Schema
from typing import List
from .models import Upload, Notification

class UploadOut(Schema):
    class Config:
        model = Upload
        model_fields = ['id', 'folder_name', 'project_name', 'status', 'created_at']

class NotificationOut(Schema):
    class Config:
        model = Notification
        model_fields = ['id', 'title', 'message', 'type', 'created_at', 'read'] 