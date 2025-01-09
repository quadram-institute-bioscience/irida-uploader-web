from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Upload, UploadFile, Notification
import iridauploader.core as core
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

def initialize_irida_api():
    """Initialize the IRIDA API from Django settings."""
    settings_dict = {
        "base_url": settings.IRIDA_BASE_URL,
        "client_id": settings.IRIDA_CLIENT_ID,
        "client_secret": settings.IRIDA_CLIENT_SECRET,
        "username": settings.IRIDA_USERNAME,
        "password": settings.IRIDA_PASSWORD,
        "timeout_multiplier": settings.IRIDA_TIMEOUT,
    }

    # Create a temporary config file
    temp_config = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".conf")
    temp_config_path = temp_config.name

    config = configparser.ConfigParser()
    config["Settings"] = settings_dict
    config.write(temp_config)
    temp_config.close()

    # Schedule the temporary file for deletion
    atexit.register(os.unlink, temp_config_path)

    return api_handler._initialize_api(**settings_dict), temp_config_path

def create_irida_project(name, project_description=None):
    """Create a project in IRIDA."""
    if project_description is None:
        project_description = f"Created on {datetime.date.today()} via IUW"
    try:
        _api, _ = initialize_irida_api()
        projects_list = _api.get_projects()
        existed_project = [prj.id for prj in projects_list if prj.name == name]
        
        if len(existed_project) == 0:
            new_project = Project(name, project_description)
            created_project = _api.send_project(new_project)
            project_id = created_project['resource']['identifier']
            return project_id
        else:
            return existed_project[0]
    except Exception as e:
        raise e

def prepare_sample_list(directory_path, pattern="*_R1_001.fastq.gz", project_id=None, 
                       project_name=None, paired_end=True, sort=False):
    """Prepare sample list for IRIDA upload."""
    p = pathlib.Path(directory_path)

    if project_id is None:
        if project_name is None:
            run_date = datetime.date.today().strftime("%y%m%d")
            project_name = f'IUW-{p.parts[-1].replace("_","-")}-{run_date}'
        
        project_id = create_irida_project(name=project_name)

    if paired_end:
        regex = re.compile("_S[0-9]{1,3}|_R[12].|_1.non_host.fastq.gz|_2.non_host.fastq.gz")
    else:
        regex = re.compile(".fastq|.fq.")
        pattern = "*.fastq.gz"

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

@shared_task(bind=True, max_retries=5)
def process_upload(self, upload_id):
    """Process file upload and send to IRIDA."""
    try:
        upload = Upload.objects.get(id=upload_id)
        upload.status = 'uploading'
        upload.save()
        
        # Process each file in the upload
        files = upload.files.all()
        user_dir = upload.user.get_upload_dir()
        target_dir = os.path.join(user_dir, upload.folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Move files to target directory and track status
        for upload_file in files:
            try:
                upload_file.status = 'uploading'
                upload_file.save()
                
                source_path = upload_file.file.path
                target_path = os.path.join(target_dir, upload_file.original_filename)
                
                with open(source_path, 'rb') as src, open(target_path, 'wb') as dst:
                    while True:
                        chunk = src.read(8192)
                        if not chunk:
                            break
                        dst.write(chunk)
                
                upload_file.status = 'success'
                upload_file.save()
                
            except Exception as e:
                upload_file.status = 'failed'
                upload_file.save()
                raise e

        # Prepare sample list and get project ID
        sample_list, project_id = prepare_sample_list(
            directory_path=target_dir,
            project_name=f"IUW-{upload.user.email}-{datetime.date.today().strftime('%y%m%d')}"
        )

        # Upload to IRIDA
        exit_code = core.upload.upload_run_single_entry(
            target_dir,
            force_upload=False,
            upload_mode="default",
            continue_upload=False
        ).exit_code

        if exit_code == 0:
            upload.status = 'success'
        else:
            upload.status = 'failed'
        upload.save()
        
        # Create notification
        create_notification.delay(
            upload.user.id,
            upload.id,
            'success' if upload.status == 'success' else 'error'
        )
        
    except Exception as exc:
        # Increment retry count
        upload = Upload.objects.get(id=upload_id)
        upload.retry_count += 1
        upload.status = 'failed'
        upload.save()
        
        if upload.retry_count < 5:
            raise self.retry(exc=exc, countdown=60)
        else:
            create_notification.delay(
                upload.user.id,
                upload.id,
                'error'
            )

@shared_task
def create_notification(user_id, upload_id, notification_type):
    upload = Upload.objects.get(id=upload_id)
    
    if notification_type == 'success':
        title = 'Upload Complete'
        message = f'Your upload "{upload.folder_name}" has completed successfully.'
    else:
        title = 'Upload Failed'
        message = f'Your upload "{upload.folder_name}" has failed. Please try again.'
    
    # Create in-app notification
    notification = Notification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        related_upload=upload
    )
    
    # Send email notification
    send_email_notification.delay(user_id, title, message)

@shared_task
def send_email_notification(user_id, title, message):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user = User.objects.get(id=user_id)
    send_mail(
        title,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    ) 