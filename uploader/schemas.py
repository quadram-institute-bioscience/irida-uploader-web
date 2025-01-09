from ninja_schema import ModelSchema
from typing import List
from .models import Upload, Notification

class UploadSchema(ModelSchema):
    class Config:
        model = Upload
        model_fields = ['id', 'folder_name', 'project_name', 'status', 'created_at']

class NotificationSchema(ModelSchema):
    class Config:
        model = Notification
        model_fields = ['id', 'title', 'message', 'type', 'created_at', 'read'] 