from celery import shared_task
from celery import Celery
from celery.app.control import Control
from celery.app import app_or_default
from django.core.mail import send_mail
from django.conf import settings
from .models import Upload, Notification
import iridauploader.core as core
import iridauploader.config as irida_config
from iridauploader.model import Project
from iridauploader.core import api_handler
import os
import tempfile
import atexit
import configparser
import datetime
import logging
import pathlib
import re
import time
from logging import StreamHandler
from io import StringIO
from celery import current_app

logger = logging.getLogger(__name__)

MAX_CONCURRENT_UPLOADS = 2
UPLOAD_LOCK_EXPIRE = 60 * 60  # 1 hour in seconds

def initialize_irida_api():
    """Initialize the IRIDA API from Django settings."""
    logger.info("Initializing IRIDA API")
    settings_dict = {
        "base_url": settings.IRIDA_API_URL,
        "client_id": settings.IRIDA_CLIENT_ID,
        "client_secret": settings.IRIDA_CLIENT_SECRET,
        "username": settings.IRIDA_USERNAME,
        "password": settings.IRIDA_PASSWORD,
        "timeout_multiplier": settings.IRIDA_TIMEOUT,
    }
    logger.info(f"IRIDA settings: {settings_dict}")

    # Create a temporary config file
    temp_config = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".conf")
    temp_config_path = temp_config.name
    logger.info(f"Created temporary config file at: {temp_config_path}")

    # Write config file directly without using configparser
    with open(temp_config_path, 'w') as f:
        f.write("[Settings]\n")
        f.write(f"base_url = {settings_dict['base_url']}\n")
        f.write(f"client_id = {settings_dict['client_id']}\n")
        f.write(f"client_secret = {settings_dict['client_secret']}\n")
        f.write(f"username = {settings_dict['username']}\n")
        f.write(f"password = {settings_dict['password']}\n")
        f.write(f"timeout = {settings_dict['timeout_multiplier']}\n")

    # Schedule the temporary file for deletion
    atexit.register(os.unlink, temp_config_path)

    try:
        logger.info("Attempting to initialize IRIDA API")
        api = api_handler._initialize_api(**settings_dict)
        logger.info("Successfully initialized IRIDA API")
        return api, temp_config_path
    except Exception as e:
        logger.error(f"Failed to initialize IRIDA API: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        raise

def create_irida_project(name, project_description=None):
    """Create a project in IRIDA."""
    if project_description is None:
        project_description = f"Created on {datetime.date.today()} via IUW"
    try:
        logger.info(f"Creating IRIDA project: {name}")
        _api, _ = initialize_irida_api()
        logger.info("Getting list of existing projects")
        projects_list = _api.get_projects()
        existed_project = [prj.id for prj in projects_list if prj.name == name]
        
        if len(existed_project) == 0:
            logger.info("Project doesn't exist, creating new one")
            new_project = Project(name, project_description)
            created_project = _api.send_project(new_project)
            project_id = created_project['resource']['identifier']
            logger.info(f"Created new project with ID: {project_id}")
            return project_id
        else:
            logger.info(f"Project already exists with ID: {existed_project[0]}")
            return existed_project[0]
    except Exception as e:
        logger.error(f"Error creating IRIDA project: {str(e)}")
        raise

def prepare_sample_list(directory_path, pattern=None, project_id=None, 
                       project_name=None, paired_end=None, sort=False):
    """Prepare sample list for IRIDA upload."""
    p = pathlib.Path(directory_path)

    if project_id is None:
        if project_name is None:
            run_date = datetime.date.today().strftime("%y%m%d")
            project_name = f'QIB-{p.parts[-1].replace("_","-")}-{run_date}'
        
        project_id = create_irida_project(name=project_name)

    # Auto-detect paired_end if not specified
    if paired_end is None:
        r1_files = list(p.rglob("*_R1*.fastq.gz"))
        single_end_files = list(p.rglob("*.fastq.gz"))
        single_end_files = [f for f in single_end_files if not ("_R1" in f.name or "_R2" in f.name)]
        paired_end = len(r1_files) > 0

    if paired_end:
        pattern = "*_R1*.fastq.gz"
        regex = re.compile("_S[0-9]{1,3}|_R[12].|_1.non_host.fastq.gz|_2.non_host.fastq.gz")
    else:
        pattern = "*.fastq.gz"
        regex = re.compile(".fastq|.fq.")

    fastqs = list(p.rglob(pattern))
    fastq_names = [fq.name for fq in fastqs]
    _sorted_fastq_names = sorted(fastq_names) if sort else fastq_names

    sample_ids = [regex.split(sp)[0] for sp in _sorted_fastq_names]
    sample_file = p.joinpath("SampleList.csv")

    with sample_file.open(mode="w") as fh:
        fh.write("[Data]\n")
        fh.write("Sample_Name,Project_ID,File_Forward,File_Reverse\n")
        for i, fastq in enumerate(_sorted_fastq_names):
            if paired_end:
                if "_R1" in fastq:
                    reverse_reads = fastq.replace("_R1", "_R2")
                elif "_R1.non_host.fastq.gz" in fastq:
                    reverse_reads = fastq.replace("_R1.non_host.fastq.gz", "_R2.non_host.fastq.gz")
                else:
                    raise ValueError(f"Invalid file name: {fastq}")
            else:
                reverse_reads = ""
            fh.write(f"{sample_ids[i]}, {project_id}, {fastq}, {reverse_reads}\n")

    return sample_file, project_id

class NotificationLogHandler(StreamHandler):
    def __init__(self, upload_id, user_id):
        super().__init__()
        self.upload_id = upload_id
        self.user_id = user_id
        self.buffer = StringIO()

    def emit(self, record):
        msg = self.format(record)
        self.buffer.write(msg + '\n')
        
        # Create notification for errors
        if record.levelno >= logging.ERROR:
            Notification.objects.create(
                user_id=self.user_id,
                title='Upload Error',
                message=msg,
                type='error',
                related_upload_id=self.upload_id
            )

    def close(self):
        self.buffer.close()
        super().close()

def get_queue_info_tasks():
    """Get information about current queue status"""
    try:
        # Get uploads that are in 'submitted' or 'uploading' status from database
        queued_uploads = Upload.objects.filter(status__in=['submitted', 'uploading']).order_by('created_at')
        running_uploads = Upload.objects.filter(status='uploading').count()
        
        all_tasks = []
        for upload in queued_uploads:
            all_tasks.append({
                'id': f'db-{upload.id}',
                'folder_name': upload.folder_name,
                'status': upload.status,
                'user': upload.user.email
            })
        
        return {
            'total_in_queue': len(all_tasks),
            'running_uploads': running_uploads,
            'max_concurrent_uploads': MAX_CONCURRENT_UPLOADS,
            'tasks': all_tasks
        }
        
    except Exception as e:
        logger.error(f"Error getting queue info: {str(e)}")
        return {
            'total_in_queue': 0,
            'running_uploads': 0,
            'max_concurrent_uploads': MAX_CONCURRENT_UPLOADS,
            'tasks': []
        }

@shared_task
def send_email_notification(recipient_email, subject, message):
    """Send email notification as a Celery task."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
        logger.info(f"Email notification sent to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")

@shared_task(bind=True, max_retries=5)
def process_upload(self, upload_id, force_upload=False):
    """Process file upload and send to IRIDA."""
    try:
        logger.info(f"Starting upload process for upload_id: {upload_id}")
        upload = Upload.objects.get(id=upload_id)
        upload.status = 'uploading'
        upload.save()

        # Set up log capture
        irida_logger = logging.getLogger('iridauploader')
        notification_handler = NotificationLogHandler(upload_id, upload.user.id)
        notification_handler.setLevel(logging.INFO)
        irida_logger.addHandler(notification_handler)

        try:
            # Get the target directory
            user_dir = upload.user.get_upload_dir()
            target_dir = os.path.join(user_dir, upload.folder_name)
            logger.info(f"Processing files in directory: {target_dir}")

            # Prepare sample list and get project ID
            try:
                logger.info("Preparing sample list and creating IRIDA project")
                
                subfolder_name = os.path.basename(target_dir)
                run_date = datetime.date.today().strftime("%y%m%d")
                
                project_name = upload.project_name if upload.project_name else f"QIB-{subfolder_name}-{run_date}"
                logger.info(f"Using project name: {project_name}")
                
                sample_list, project_id = prepare_sample_list(
                    directory_path=target_dir,
                    project_name=project_name
                )
                
                # Update upload with project ID and sample count
                with open(sample_list, 'r') as f:
                    # Skip header lines
                    next(f)  # Skip [Data]
                    next(f)  # Skip column headers
                    sample_count = sum(1 for line in f)
                
                upload.sample_count = sample_count
                upload.irida_project_id = project_id
                upload.save()
                
                logger.info(f"Sample list created with {sample_count} samples, project ID: {project_id}")
                
            except Exception as e:
                logger.error(f"Error preparing sample list: {str(e)}")
                raise e

            # Upload to IRIDA
            try:
                logger.info(f"Starting IRIDA upload for directory: {target_dir}")
                logger.info("Initializing IRIDA API for upload")
                
                # Initialize API and get config path
                api, config_path = initialize_irida_api()
                logger.info(f"Using config file: {config_path}")
                
                # Set up configuration
                irida_config.set_config_file(config_path)
                irida_config.setup()
                logger.info("IRIDA configuration set up")
                
                # Perform the upload
                logger.info("Starting upload_run_single_entry")
                result = core.upload.upload_run_single_entry(
                    target_dir,
                    force_upload=force_upload,
                    upload_mode="default",
                    continue_upload=False
                )
                logger.info(f"Upload result: {result}")
                logger.info(f"Upload exit code: {result.exit_code}")

                if result.exit_code == 0:
                    upload.status = 'success'
                    logger.info("IRIDA upload completed successfully")
                    # Send success email asynchronously
                    send_email_notification.delay(
                        upload.user.email,
                        'Upload Complete',
                        f'Your upload of {upload.folder_name} has completed successfully.'
                    )
                else:
                    upload.status = 'failed'
                    logger.error(f"IRIDA upload failed with exit code {result.exit_code}")
                    # Send failure email asynchronously
                    send_email_notification.delay(
                        upload.user.email,
                        'Upload Failed',
                        f'Your upload of {upload.folder_name} has failed. Please check the system for more details.'
                    )
                upload.save()

            except Exception as e:
                logger.error(f"Error during IRIDA upload: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error args: {e.args}")
                upload.status = 'failed'
                upload.save()
                # Send failure email asynchronously
                send_email_notification.delay(
                    upload.user.email,
                    'Upload Failed',
                    f'Your upload of {upload.folder_name} has failed due to an error. Please contact support for assistance.'
                )
                raise e
            
            # Try to create notification, but don't fail if it doesn't work
            try:
                create_notification.delay(
                    upload.user.id,
                    upload.id,
                    'success' if upload.status == 'success' else 'error'
                )
            except Exception as e:
                logger.error(f"Failed to create notification: {str(e)}")
            
        finally:
            # Clean up the log handler
            irida_logger.removeHandler(notification_handler)
            notification_handler.close()

    except Exception as exc:
        logger.error(f"Error processing upload {upload_id}: {str(exc)}")
        # Increment retry count
        try:
            upload = Upload.objects.get(id=upload_id)
            upload.status = 'failed'
            upload.save()
            
            if upload.retry_count < 5:
                raise self.retry(exc=exc, countdown=60)
            else:
                try:
                    create_notification.delay(
                        upload.user.id,
                        upload.id,
                        'error'
                    )
                except Exception as e:
                    logger.error(f"Failed to create error notification: {str(e)}")
        except Upload.DoesNotExist:
            logger.error(f"Upload {upload_id} not found when handling error")
        except Exception as e:
            logger.error(f"Error handling upload failure: {str(e)}")

@shared_task
def create_notification(user_id, upload_id, notification_type):
    """Create a notification for an upload."""
    try:
        upload = Upload.objects.get(id=upload_id)
        
        # Get queue information
        queue_info = get_queue_info_tasks()
        total_in_queue = queue_info['total_in_queue']
        
        # Find position in queue
        queue_position = None
        for idx, task in enumerate(queue_info['tasks']):
            if task.get('args') and str(upload_id) in str(task['args']):
                queue_position = idx + 1
                break
        
        if notification_type == 'success':
            title = 'Upload Complete'
            message = f'Upload of {upload.folder_name} has completed successfully.'
        elif notification_type == 'error':
            title = 'Upload Failed'
            message = f'Upload of {upload.folder_name} has failed.'
        else:
            title = 'Upload In Queue'
            position_msg = f' (Position {queue_position} of {total_in_queue})' if queue_position else ''
            message = f'Upload of {upload.folder_name} is in queue{position_msg}. {total_in_queue} total uploads in queue.'
        
        Notification.objects.create(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            related_upload=upload
        )
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")

@shared_task
def test_celery(x, y):
    """Test task to verify Celery is working."""
    time.sleep(2)  # Simulate some work
    return x + y 

@shared_task
def update_queue_notifications():
    """Update all queue notifications with current positions"""
    try:
        # Get current queue information
        queue_info = get_queue_info_tasks()
        total_in_queue = queue_info['total_in_queue']
        
        # Get all 'submitted' uploads
        queued_uploads = Upload.objects.filter(status='submitted')
        
        for upload in queued_uploads:
            # Find position in queue
            queue_position = None
            for idx, task in enumerate(queue_info['tasks']):
                if task.get('args') and str(upload.id) in str(task['args']):
                    queue_position = idx + 1
                    break
            
            # Create/update notification
            position_msg = f' (Position {queue_position} of {total_in_queue})' if queue_position else ''
            message = f'Upload of {upload.folder_name} is in queue{position_msg}. {total_in_queue} total uploads in queue.'
            
            Notification.objects.update_or_create(
                user_id=upload.user.id,
                related_upload=upload,
                type='info',
                defaults={
                    'title': 'Upload In Queue',
                    'message': message
                }
            )
    except Exception as e:
        logger.error(f"Error updating queue notifications: {str(e)}") 