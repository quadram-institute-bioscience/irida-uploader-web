from ninja import Schema, ModelSchema
from typing import List, Optional
from datetime import datetime
from .models import Upload, UploadFile, Notification

class UserSchema(Schema):
    id: int
    email: str
    username: str

class UploadFileSchema(ModelSchema):
    class Config:
        model = UploadFile
        model_fields = ['id', 'original_filename', 'size', 'status', 'uploaded_at']

class UploadSchema(ModelSchema):
    files: List[UploadFileSchema]
    user: UserSchema

    class Config:
        model = Upload
        model_fields = ['id', 'folder_name', 'status', 'created_at', 'updated_at']

class UploadCreateSchema(Schema):
    folder_name: str

class FileStatusSchema(Schema):
    name: str
    status: str

class UploadStatusSchema(Schema):
    status: str
    files: List[FileStatusSchema]

class FolderListSchema(Schema):
    folders: List[str]

class NotificationSchema(ModelSchema):
    class Config:
        model = Notification
        model_fields = ['id', 'title', 'message', 'type', 'created_at', 'read', 'related_upload']

class NotificationListSchema(Schema):
    notifications: List[NotificationSchema]

class MessageSchema(Schema):
    status: str
    message: Optional[str] = None 