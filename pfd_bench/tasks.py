
"""
Use this file to add celery wrappers for async function calls
"""


from celery import shared_task
import logging
from django.utils import timezone

from .core.PFD_bench_runs import pfd_bench_run_step_1, pfd_bench_run_step_2

## logger instance for this module
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_pfd_extraction_step_1(self, run_id):
    """
    Process PFD extraction asynchronously
    
    bind=True gives access to self for retries
    max_retries=3 for resilience
    """
    from .models import Run  # Import here to avoid circular imports

    try:
        pfd_bench_run_step_1(run_id)
        logger.info(f"Successfully processed step 1 of run {run_id}")
        
    except Run.DoesNotExist:
        logger.error(f"Run {run_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error processing run {run_id}: {str(e)}")
        
        # Update run with error
        try:
            run = Run.objects.get(pk=run_id)
            run.status = 'failed'
            run.processing_error = str(e)
            run.processing_completed_at = timezone.now()
            run.save()
        except:
            pass
            
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def process_pfd_extraction_step_2(self, run_id):
    """
    Process PFD description from a connectivity table, asynchronously
    
    bind=True gives access to self for retries
    max_retries=3 for resilience
    """
    from .models import Run  # Import here to avoid circular imports

    logger.info(f"Starting step 2 of run {run_id}")

    try:
        pfd_bench_run_step_2(run_id)
        logger.info(f"Successfully processed step 2 of run {run_id}")
        
    except Run.DoesNotExist:
        logger.error(f"Run {run_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error processing run {run_id}: {str(e)}")
        
        # Update run with error
        try:
            run = Run.objects.get(pk=run_id)
            run.status = 'failed'
            run.processing_error = str(e)
            run.processing_completed_at = timezone.now()
            run.save()
        except:
            pass
            
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))