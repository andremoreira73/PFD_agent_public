import json
import tempfile
import os

import logging
from django.utils import timezone

## logger instance for this module
logger = logging.getLogger(__name__)


def pfd_bench_run_step_1(run_id):
    """
    Prepares the input for and runs the first graph in the PFD bench workflow:
    1) extracts the schema we defined from the raw .dxf file
    2) sends it to the graph as initial state and invoke
    3) saves results in the database, including the status
    """

    from ..models import Run  # Import here to avoid circular imports
    from .PFD_utils import extract_dxf_schema_v2
    from .PFD_bench_setup import pfd_bench_st1_setup

    # Load the run
    run = Run.objects.get(pk=run_id)
    
    # Update status
    run.status = 'processing'
    run.processing_started_at = timezone.now()
    run.save()


    # Extract DXF schema
    temp_file_path = None

    try:

        if hasattr(run.file.file, 'path'):
            # Local storage - use path directly
            dxf_path = run.file.file.path
        else:
            # Cloud storage - download to temp file
            with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp:
                tmp.write(run.file.file.read())
                temp_file_path = tmp.name
            dxf_path = temp_file_path

        logger.info(f"Processing file {run.file.name} for run {run_id}")

        dxf_extract_dict = extract_dxf_schema_v2(dxf_path)
        dxf_extract = json.dumps(dxf_extract_dict, indent=2, default=str)
        
        # Initialize and run the graph
        graph = pfd_bench_st1_setup()
        initial_state = {"dxf_extract": dxf_extract, "messages": []}
        
        # Run the graph
        result = graph.invoke(initial_state)
        
        # Extract the table data from the result
        corrected_table = result.get('corrected_equipment_table')
        
        # Convert to list of dicts for JSON storage
        table_data = []
        for row in corrected_table.rows:
            table_data.append({
                "tag": row.tag,
                "equipment_type": row.equipment_type,
                "inlet_streams": row.inlet_streams,
                "inlet_count": row.inlet_count,
                "outlet_streams": row.outlet_streams,
                "outlet_count": row.outlet_count,
                "remarks": row.remarks
            })
        
        # Update run with results
        run.generated_table = table_data
        run.status = 'ready_for_review'
        run.processing_completed_at = timezone.now()
        run.save()

    except Exception as e:
        logger.error(f"Error in step 1 of processing run {run_id}: {str(e)}")

    finally:
        # Clean up temp file if we created one
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    return


def pfd_bench_run_step_2(run_id):
    """
    Based on a (reviewed) connectivity table, prepares the process description
    """

    from ..models import Run  # Import here to avoid circular imports
    from .PFD_bench_setup import pfd_bench_st2_setup

    # Load the run
    run = Run.objects.get(pk=run_id)
    
    # Update status
    run.status = 'processing'
    run.processing_started_at = timezone.now()
    run.save()

    try:

        # Initialize and run the graph
        graph = pfd_bench_st2_setup()

        connectivity_table_md = run.final_table_to_markdown()
        
        initial_state = {"connectivity_table": connectivity_table_md, "messages": []}
        
        # Run the graph
        result = graph.invoke(initial_state)
        
        # Extract the table data from the result
        process_description = result.get('process_description')
        

        # Update run with results
        run.generated_text = process_description
        run.status = 'completed'
        run.processing_completed_at = timezone.now()
        run.save()

    except Exception as e:
        logger.error(f"Error in step 2 of processing run {run_id}: {str(e)}")
    
    return
