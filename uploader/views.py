from django.shortcuts import render
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.conf import settings
from .models import Upload, UploadFile, Notification, User
from .tasks import process_upload
import os
import json

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        use_ldap = request.POST.get('use_ldap') == 'true'
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Invalid credentials'})
    return render(request, 'uploader/login.html')

@login_required
def dashboard(request):
    uploads = Upload.objects.filter(user=request.user)
    paginator = Paginator(uploads, 10)
    page = request.GET.get('page', 1)
    uploads_page = paginator.get_page(page)
    
    return render(request, 'uploader/dashboard.html', {
        'uploads': uploads_page
    })

@login_required
def get_folders(request):
    user_dir = request.user.get_upload_dir()
    folders = []
    
    for root, dirs, files in os.walk(user_dir):
        rel_path = os.path.relpath(root, user_dir)
        if rel_path != '.':
            folders.append(rel_path)
    
    return JsonResponse({'folders': folders})

@login_required
@csrf_exempt
def upload_files(request):
    if request.method == 'POST':
        folder_name = request.POST.get('folder_name')
        files = request.FILES.getlist('files')
        
        upload = Upload.objects.create(
            user=request.user,
            folder_name=folder_name,
            status='submitted'
        )
        
        for file in files:
            UploadFile.objects.create(
                upload=upload,
                file=file,
                original_filename=file.name,
                size=file.size
            )
        
        # Start Celery task
        task = process_upload.delay(upload.id)
        upload.task_id = task.id
        upload.save()
        
        return JsonResponse({
            'status': 'success',
            'upload_id': upload.id
        })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def get_upload_status(request, upload_id):
    try:
        upload = Upload.objects.get(id=upload_id, user=request.user)
        files = upload.files.all()
        
        return JsonResponse({
            'status': upload.status,
            'files': [{
                'name': f.original_filename,
                'status': f.status
            } for f in files]
        })
    except Upload.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)

@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user,
        read=False
    ).order_by('-created_at')[:5]
    
    return JsonResponse({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.type,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
    })

@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
