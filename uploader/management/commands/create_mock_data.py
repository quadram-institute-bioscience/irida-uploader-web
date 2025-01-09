from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
import os
import random
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates mock data including server subfolders and dummy fastq files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=2,
            help='Number of test users to create'
        )
        parser.add_argument(
            '--samples',
            type=int,
            default=5,
            help='Number of samples per project'
        )
        parser.add_argument(
            '--projects',
            type=int,
            default=3,
            help='Number of projects per user'
        )

    def _create_dummy_fastq(self, filepath, size_kb=1):
        """Create a dummy fastq file with specified size."""
        with open(filepath, 'wb') as f:
            # Write a dummy FASTQ header and sequence
            header = b'@SEQ_ID\n'
            seq = b'ACTG' * 25 + b'\n'  # 100 base sequence
            plus = b'+\n'
            qual = b'I' * 100 + b'\n'  # Quality scores
            
            # Calculate how many records we need for the desired file size
            record = header + seq + plus + qual
            records_needed = (size_kb * 1024) // len(record) + 1
            
            # Write the records
            for _ in range(records_needed):
                f.write(record)

    def _create_user_structure(self, email, num_projects, samples_per_project):
        """Create directory structure and files for a user."""
        base_path = os.path.join(settings.UPLOAD_ROOT, email)
        os.makedirs(base_path, exist_ok=True)
        
        # Create projects with dates from last 30 days
        for i in range(num_projects):
            date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%y%m%d')
            project_name = f"Project_{date}_{i+1}"
            project_path = os.path.join(base_path, project_name)
            os.makedirs(project_path, exist_ok=True)
            
            # Create samples in project
            for j in range(samples_per_project):
                sample_name = f"Sample_{j+1}"
                
                # Create R1 and R2 fastq files
                for read in ['R1', 'R2']:
                    fastq_name = f"{sample_name}_S{j+1}_{read}_001.fastq.gz"
                    fastq_path = os.path.join(project_path, fastq_name)
                    self._create_dummy_fastq(fastq_path)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {fastq_path}')
                    )

    def handle(self, *args, **options):
        num_users = options['users']
        num_projects = options['projects']
        samples_per_project = options['samples']
        
        # Create test users
        for i in range(num_users):
            email = f"test{i+1}@example.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': f'test{i+1}',
                    'is_active': True
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created user {email}')
                )
            
            # Create directory structure and files
            self._create_user_structure(email, num_projects, samples_per_project)
            
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {num_users} users with {num_projects} projects each, '
                f'containing {samples_per_project} samples per project'
            )
        ) 