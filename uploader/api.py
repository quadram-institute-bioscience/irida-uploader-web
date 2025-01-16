from ninja import Router
from ninja.security import django_auth
from django.shortcuts import get_object_or_404
from typing import List
from .models import Upload, Notification
from .schemas import UploadOut, NotificationOut

api = Router()

@api.get("/uploads", response=List[UploadOut], auth=django_auth)
def list_uploads(request):
    return Upload.objects.filter(user=request.user)

@api.get("/uploads/{upload_id}", response=UploadOut, auth=django_auth)
def get_upload(request, upload_id: int):
    return get_object_or_404(Upload, id=upload_id, user=request.user)

@api.get("/notifications", response=List[NotificationOut], auth=django_auth)
def list_notifications(request):
    return Notification.objects.filter(user=request.user, read=False) 