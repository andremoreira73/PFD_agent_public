# pfd_bench/mock_data.py

def generate_mock_equipment_row(index, table_data):
    """Generate a mock row for review based on the Gemini table structure"""
    if index < len(table_data):
        row = table_data[index]
        return {
            "index": index,
            "tag": row["tag"],
            "equipment_type": row["equipment_type"],
            "inlet_streams": row["inlet_streams"],
            "inlet_count": row["inlet_count"],
            "outlet_streams": row["outlet_streams"],
            "outlet_count": row["outlet_count"],
            "remarks": row["remarks"],
        }
    return None

# Your sample table data
SAMPLE_TABLE = [
    {
        "tag": "03-R010",
        "equipment_type": "Agitated Reactor",
        "inlet_streams": "Feed Stream 1, Feed Stream 2",
        "inlet_count": "2",
        "outlet_streams": "Outlet to Pump 03-P020, Outlet to Vessel 03-V060",
        "outlet_count": "2",
        "remarks": "Equipment block `E-Reaktor-LKA` includes an agitator. Tag inferred from block `Equipment Tag 01_block-2`."
    },
    {
        "tag": "03-P020",
        "equipment_type": "Pump",
        "inlet_streams": "From Reactor 03-R010",
        "inlet_count": "1",
        "outlet_streams": "To Thickener 03-V030",
        "outlet_count": "1",
        "remarks": "Tag inferred from block `Equipment Tag Pumpen 01_block-3`."
    },
    {
        "tag": "03-V030",
        "equipment_type": "Thickener",
        "inlet_streams": "From Pump 03-P020",
        "inlet_count": "1",
        "outlet_streams": "Underflow to Pump 03-P040, Overflow to Vessel 03-V060",
        "outlet_count": "2",
        "remarks": "Includes a scraper. Tag inferred from blocks `Equipment Tag 01_block-5/6`."
    },
    {
        "tag": "03-P040",
        "equipment_type": "Pump",
        "inlet_streams": "From Thickener 03-V030 (Underflow)",
        "inlet_count": "1",
        "outlet_streams": "To Cyclone 03-S050",
        "outlet_count": "1",
        "remarks": "Tag inferred from block `Equipment Tag Pumpen 01_block-2`."
    },
    {
        "tag": "03-S050",
        "equipment_type": "Cyclone Separator",
        "inlet_streams": "From Pump 03-P040",
        "inlet_count": "1",
        "outlet_streams": "Top outlet (Overflow), Bottom outlet (Underflow)",
        "outlet_count": "2",
        "remarks": "The two outlet streams appear to leave the main process area. Tag inferred from block `Equipment Tag 01_block-4`."
    },
    {
        "tag": "03-V060",
        "equipment_type": "Vessel / Tank",
        "inlet_streams": "From Reactor 03-R010, From Thickener 03-V030 (Overflow)",
        "inlet_count": "2",
        "outlet_streams": "-",
        "outlet_count": "0",
        "remarks": "**No outlet stream is shown on the diagram for this vessel.** Tag inferred from block `Equipment Tag 01_block-7`."
    }
]