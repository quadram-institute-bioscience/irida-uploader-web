from ninja import NinjaAPI, File
from ninja.files import UploadedFile
from ninja.security import django_auth
from typing import List
from django.shortcuts import get_object_or_404
from .models import Upload, UploadFile, Notification
from .schemas import (
    UploadSchema, UploadCreateSchema, UploadStatusSchema,
    NotificationSchema, NotificationListSchema, FolderListSchema,
    FileStatusSchema, MessageSchema
)
from .tasks import process_upload
import os

api = NinjaAPI(auth=django_auth, title="IRIDA Uploader API", version="1.0.0")

@api.get("/uploads", response=List[UploadSchema], tags=["uploads"])
def list_uploads(request):
    """List all uploads for the authenticated user."""
    return Upload.objects.filter(user=request.user)

@api.post("/uploads", response=UploadSchema, tags=["uploads"])
def create_upload(request, data: UploadCreateSchema, files: List[UploadedFile] = File(...)):
    """Create a new upload with multiple files."""
    upload = Upload.objects.create(
        user=request.user,
        folder_name=data.folder_name
    )
    
    for file in files:
        UploadFile.objects.create(
            upload=upload,
            file=file,
            original_filename=file.name,
            size=file.size
        )
    
    # Start processing
    process_upload.delay(upload.id)
    return upload

@api.get("/uploads/{upload_id}", response=UploadSchema, tags=["uploads"])
def get_upload(request, upload_id: int):
    """Get details of a specific upload."""
    return get_object_or_404(Upload, id=upload_id, user=request.user)

@api.get("/uploads/{upload_id}/status", response=UploadStatusSchema, tags=["uploads"])
def get_upload_status(request, upload_id: int):
    """Get the status of an upload and its files."""
    upload = get_object_or_404(Upload, id=upload_id, user=request.user)
    files = upload.files.all()
    
    return {
        "status": upload.status,
        "files": [{"name": f.original_filename, "status": f.status} for f in files]
    }

@api.get("/uploads/folders", response=FolderListSchema, tags=["uploads"])
def list_folders(request):
    """List available folders for the authenticated user."""
    user_dir = request.user.get_upload_dir()
    folders = []
    
    if os.path.exists(user_dir):
        for root, dirs, files in os.walk(user_dir):
            rel_path = os.path.relpath(root, user_dir)
            if rel_path != '.':
                folders.append(rel_path)
    
    return {"folders": folders}

@api.delete("/uploads/{upload_id}", response=MessageSchema, tags=["uploads"])
def delete_upload(request, upload_id: int):
    """Delete an upload and its associated files."""
    upload = get_object_or_404(Upload, id=upload_id, user=request.user)
    upload.delete()
    return {"status": "success", "message": "Upload deleted successfully"}

@api.get("/notifications", response=NotificationListSchema, tags=["notifications"])
def list_notifications(request):
    """List all notifications for the authenticated user."""
    notifications = Notification.objects.filter(user=request.user)
    return {"notifications": notifications}

@api.get("/notifications/{notification_id}", response=NotificationSchema, tags=["notifications"])
def get_notification(request, notification_id: int):
    """Get details of a specific notification."""
    return get_object_or_404(Notification, id=notification_id, user=request.user)

@api.post("/notifications/{notification_id}/mark-read", response=MessageSchema, tags=["notifications"])
def mark_notification_read(request, notification_id: int):
    """Mark a notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.read = True
    notification.save()
    return {"status": "success"} 