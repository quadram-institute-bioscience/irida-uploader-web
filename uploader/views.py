from django.shortcuts import render
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.conf import settings
from .models import Upload, Notification, User
from . import tasks
import os
import json
import logging

logger = logging.getLogger(__name__)

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
    
    # Get user's upload directory path
    user_upload_dir = request.user.get_upload_dir()
    upload_dir_exists = os.path.exists(user_upload_dir)
    
    # Handle search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        from django.db.models import Q
        uploads = uploads.filter(
            Q(folder_name__icontains=search_query) |
            Q(project_name__icontains=search_query) |
            Q(created_at__icontains=search_query)
        )
    
    # Sort by most recent first
    uploads = uploads.order_by('-created_at')
    
    # Set items per page
    items_per_page = 10
    paginator = Paginator(uploads, items_per_page)
    
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    
    try:
        uploads_page = paginator.page(page)
    except:
        uploads_page = paginator.page(1)
    
    # Calculate page range (show 5 pages around current page)
    page_range = list(paginator.get_elided_page_range(uploads_page.number, on_each_side=2, on_ends=1))
    
    # Calculate pagination values
    start_index = (uploads_page.number - 1) * items_per_page + 1
    end_index = min(start_index + items_per_page - 1, paginator.count)
    
    # Serialize the uploads data for Alpine.js
    uploads_data = [{
        'id': upload.id,
        'folder_name': upload.folder_name,
        'project_name': upload.project_name or '',
        'status': upload.status,
        'created_at': upload.created_at.isoformat(),
        'irida_project_id': upload.irida_project_id or '-',
        'file_count': upload.get_file_info()
    } for upload in uploads_page.object_list]
    
    return render(request, 'uploader/dashboard.html', {
        'uploads': {
            'object_list': uploads_data,
            'number': uploads_page.number,
            'has_previous': uploads_page.has_previous(),
            'has_next': uploads_page.has_next(),
            'previous_page_number': uploads_page.previous_page_number() if uploads_page.has_previous() else None,
            'next_page_number': uploads_page.next_page_number() if uploads_page.has_next() else None,
            'paginator': {
                'num_pages': paginator.num_pages,
                'page_range': page_range,
                'count': paginator.count,
                'per_page': items_per_page,
                'start_index': start_index,
                'end_index': end_index
            }
        },
        'search_query': search_query,
        'upload_directory': {
            'path': user_upload_dir,
            'exists': upload_dir_exists
        },
        'irida_base_url': getattr(settings, 'IRIDA_BASE_URL', 'http://127.0.0.1:81/irida')
    })

@login_required
def get_folders(request):
    user_dir = request.user.get_upload_dir()
    folders = []
    
    # Create the user directory if it doesn't exist
    os.makedirs(user_dir, exist_ok=True)
    
    # First, add the root directory
    folders.append('.')
    
    # Then walk through all subdirectories
    for root, dirs, files in os.walk(user_dir):
        rel_path = os.path.relpath(root, user_dir)
        if rel_path != '.':
            folders.append(rel_path)
    
    return JsonResponse({'folders': sorted(folders)})

@login_required
@csrf_exempt
def upload_files(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            folder_name = data.get('folder_name')
            force_upload = data.get('force_upload', False)
            check_only = data.get('check_only', False)
            
            if not folder_name:
                return JsonResponse({'status': 'error', 'message': 'Folder name is required'}, status=400)

            # Get the full path of the selected folder
            user_dir = request.user.get_upload_dir()
            folder_path = os.path.join(user_dir, folder_name)
            
            logger.info(f"Processing upload for folder: {folder_path}")
            
            if not os.path.exists(folder_path):
                logger.error(f"Folder does not exist: {folder_path}")
                return JsonResponse({'status': 'error', 'message': 'Selected folder does not exist'}, status=400)

            # Check for existing upload logs
            status_file = os.path.join(folder_path, 'irida_uploader_status.info')
            
            if os.path.exists(status_file) and not force_upload:
                try:
                    with open(status_file, 'r') as f:
                        status_data = json.load(f)
                    
                    sample_count = len(status_data.get('Sample Status', []))
                    upload_status = status_data.get('Upload Status')
                    irida_project_id = status_data.get('Project ID')
                    
                    if upload_status == 'complete':
                        logger.info(f"Found previous upload with {sample_count} samples")
                        return JsonResponse({
                            'status': 'warning',
                            'message': f'This folder has already been uploaded with {sample_count} samples. Do you want to upload again?',
                            'sample_count': sample_count,
                            'irida_project_id': irida_project_id,
                            'needs_force': True
                        })
                except Exception as e:
                    logger.error(f"Error reading status file: {str(e)}")

            # If this is just a check, return here
            if check_only:
                return JsonResponse({'status': 'ok'})

            # Create the upload record
            upload = Upload.objects.create(
                user=request.user,
                folder_name=folder_name,
                project_name=data.get('project_name'),
                status='submitted',
                sample_count=0  # Will be updated during processing
            )

            # Start Celery task with force_upload parameter
            logger.info(f"Starting upload process for upload_id: {upload.id}")
            task = tasks.process_upload.delay(upload.id, force_upload)
            logger.info(f"Celery task started with ID: {task.id}")
            upload.task_id = task.id
            upload.save()

            return JsonResponse({
                'status': 'success',
                'upload_id': upload.id
            })
        except json.JSONDecodeError:
            logger.error("Invalid JSON data received")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@login_required
def get_upload_status(request, upload_id):
    try:
        upload = Upload.objects.get(id=upload_id, user=request.user)
        
        # Update database from status file
        upload.update_from_status_file()
        
        # Get IRIDA logs if they exist
        logs = ["Log file not found"]
        log_file = os.path.join(request.user.get_upload_dir(), upload.folder_name, 'irida-uploader.log')
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    logs = [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                logger.error(f"Error reading log file: {str(e)}")
        
        return JsonResponse({
            'status': upload.status,
            'logs': logs,
            'irida_project_id': upload.irida_project_id or '-',
            'sample_count': upload.sample_count,
            'run_id': upload.irida_run_id
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

@login_required
@csrf_exempt
def test_celery(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            x = data.get('x', 0)
            y = data.get('y', 0)
            
            logger.info(f"Starting test Celery task with x={x}, y={y}")
            task = tasks.test_celery.delay(x, y)
            logger.info(f"Test task started with ID: {task.id}")
            
            return JsonResponse({
                'status': 'success',
                'task_id': task.id
            })
        except Exception as e:
            logger.error(f"Error starting test task: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@login_required
def test_result(request, task_id):
    try:
        task = tasks.test_celery.AsyncResult(task_id)
        if task.ready():
            return JsonResponse({
                'status': 'success',
                'result': task.get()
            })
        return JsonResponse({
            'status': 'pending'
        })
    except Exception as e:
        logger.error(f"Error getting test result: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
