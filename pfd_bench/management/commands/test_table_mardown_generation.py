
from django.core.management.base import BaseCommand
from pfd_bench.models import Run

class Command(BaseCommand):
    help = 'Test markdown generation for a run'

    def add_arguments(self, parser):
        parser.add_argument('run_id', type=int, help='Run ID to test')

    def handle(self, *args, **options):
        run_id = options['run_id']
        
        try:
            run = Run.objects.get(pk=run_id)
            self.stdout.write(f"Testing run {run_id}: {run.name}")
            self.stdout.write(f"Status: {run.status}")
            self.stdout.write(f"Has generated_table: {bool(run.generated_table)}")
            self.stdout.write(f"Table length: {len(run.generated_table) if run.generated_table else 0}")
            
            # Test markdown generation
            try:
                markdown = run.final_table_to_markdown()
                self.stdout.write(self.style.SUCCESS(f"Markdown generated successfully! Length: {len(markdown)}"))
                self.stdout.write("\nResult:")
                self.stdout.write(markdown)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error generating markdown: {str(e)}"))
                import traceback
                traceback.print_exc()
                
        except Run.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Run {run_id} not found"))