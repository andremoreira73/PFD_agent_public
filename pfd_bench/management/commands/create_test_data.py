# pfd_bench/management/commands/create_test_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pfd_bench.models import Project, ProjectFile, Run
from pfd_bench.mock_data import SAMPLE_TABLE

class Command(BaseCommand):
    help = 'Creates test data for PFD Bench'

    def handle(self, *args, **options):
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        if created:
            user.set_password('admin')
            user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user (password: admin)'))
        
        # Create a test project
        project, created = Project.objects.get_or_create(
            name='Test PFD Project',
            defaults={
                'description': 'Test project for PFD bench review',
                'created_by': user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created project: {project.name}'))
        
        # Create a test file
        project_file, created = ProjectFile.objects.get_or_create(
            project=project,
            name='test_pfd.dxf',
            defaults={
                'file_type': 'dxf',
                'file': 'project_files/test.dxf',  # This doesn't need to exist for testing
                'uploaded_by': user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created project file: {project_file.name}'))
        
        # Create a test run
        run, created = Run.objects.get_or_create(
            project=project,
            name='Test Run #1',
            defaults={
                'file': project_file,
                'status': 'pending',
                'generated_table': SAMPLE_TABLE,  # Use the mock data
                'created_by': user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created run: {run.name} (ID: {run.pk})'))
        else:
            self.stdout.write(self.style.WARNING(f'Run already exists: {run.name} (ID: {run.pk})'))
        
        self.stdout.write(self.style.SUCCESS(f'\nYou can now access the review at: /bench/run/{run.pk}/review/'))
        self.stdout.write(self.style.SUCCESS('Or create more runs in the admin panel at: /admin/pfd_bench/run/'))