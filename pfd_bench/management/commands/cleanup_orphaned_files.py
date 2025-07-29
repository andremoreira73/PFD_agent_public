
from django.core.management.base import BaseCommand
from pfd_bench.utils import cleanup_orphaned_files

class Command(BaseCommand):
    help = 'Clean up orphaned files (files with no projects and no runs)'

    def handle(self, *args, **options):
        count = cleanup_orphaned_files()
        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up {count} orphaned files')
            )
        else:
            self.stdout.write('No orphaned files found')