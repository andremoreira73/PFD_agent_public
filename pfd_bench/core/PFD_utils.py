
import ezdxf


##################################################################
# this is a format that HAS TO BE like this (for ReAct agents in particular)
# After customizing a prompt, we pass the returned "create_prompt" function to the LG pre-defined agent
def customize_function_create_prompt(custom_system_prompt):
    def create_prompt(state):
        return [
            {
                "role": "system", 
                "content": custom_system_prompt
            }
        ] + state['messages']
    return create_prompt



def extract_dxf_schema_v2(filepath, proximity_threshold=15):
    """
    Extract schema from DXF file including blocks, lines, and texts.
    Simple and generic - no assumptions about layer names or block types.
    
    Parameters:
    - filepath: path to DXF file
    - proximity_threshold: distance threshold for counting nearby lines (default 15)
    
    Returns:
    - Dictionary with drawing_schema and entities
    """
    def distance(p1, p2):
        return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
    
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    
    # Initialize schema structure
    schema = {
        "drawing_schema": {
            "layers": set(),
            "block_names": set()
        },
        "entities": {
            "blocks": [],
            "lines": [],
            "texts": [],
            "circles": [],
            "arcs": [],
            "arrows": []
        }
    }
    
    # 1. Extract all blocks with attributes
    for insert in msp.query('INSERT'):
        block_data = {
            "block_name": insert.dxf.name,
            "layer": insert.dxf.layer,
            "position": [float(round(insert.dxf.insert.x, 2)), float(round(insert.dxf.insert.y, 2))],
            "rotation": float(round(insert.dxf.rotation, 2)),
            "attributes": {},
            "near_lines": 0
        }
        
        # Add to schema collections
        schema["drawing_schema"]["layers"].add(insert.dxf.layer)
        schema["drawing_schema"]["block_names"].add(insert.dxf.name)
        
        # Extract attributes if available
        if hasattr(insert, 'attribs'):
            for attrib in insert.attribs:
                tag = attrib.dxf.tag.strip()
                value = attrib.dxf.text.strip()
                if value:
                    block_data["attributes"][tag] = value
        
        schema["entities"]["blocks"].append(block_data)
        
        # Check if this is an arrow block
        block_name_lower = insert.dxf.name.lower()
        if 'arrow' in block_name_lower or 'flow' in block_name_lower:
            schema["entities"]["arrows"].append({
                "type": "block",
                "block_name": insert.dxf.name,
                "position": block_data["position"],
                "rotation": block_data["rotation"],
                "layer": insert.dxf.layer
            })
    
    # 2. Extract all lines (store uniformly as vertex lists)
    # Regular lines
    for line in msp.query('LINE'):
        schema["drawing_schema"]["layers"].add(line.dxf.layer)
        line_data = {
            "layer": line.dxf.layer,
            "vertices": [
                [float(round(line.dxf.start.x, 2)), float(round(line.dxf.start.y, 2))],
                [float(round(line.dxf.end.x, 2)), float(round(line.dxf.end.y, 2))]
            ]
        }
        # Add line width if available
        if hasattr(line.dxf, 'lineweight'):
            line_data["width"] = line.dxf.lineweight
        schema["entities"]["lines"].append(line_data)
    
    # Polylines
    for pline in msp.query('LWPOLYLINE'):
        schema["drawing_schema"]["layers"].add(pline.dxf.layer)
        points = pline.get_points('xy')
        vertices = [[float(round(p[0], 2)), float(round(p[1], 2))] for p in points]
        
        if len(vertices) > 1:
            line_data = {
                "layer": pline.dxf.layer,
                "vertices": vertices
            }
            # Add line width if available
            if hasattr(pline.dxf, 'const_width'):
                line_data["width"] = float(round(pline.dxf.const_width, 2))
            schema["entities"]["lines"].append(line_data)
    
    # 3. Extract circles
    for circle in msp.query('CIRCLE'):
        schema["drawing_schema"]["layers"].add(circle.dxf.layer)
        schema["entities"]["circles"].append({
            "center": [float(round(circle.dxf.center.x, 2)), float(round(circle.dxf.center.y, 2))],
            "radius": float(round(circle.dxf.radius, 2)),
            "layer": circle.dxf.layer
        })
    
    # 4. Extract arcs
    for arc in msp.query('ARC'):
        schema["drawing_schema"]["layers"].add(arc.dxf.layer)
        schema["entities"]["arcs"].append({
            "center": [float(round(arc.dxf.center.x, 2)), float(round(arc.dxf.center.y, 2))],
            "radius": float(round(arc.dxf.radius, 2)),
            "start_angle": float(round(arc.dxf.start_angle, 2)),
            "end_angle": float(round(arc.dxf.end_angle, 2)),
            "layer": arc.dxf.layer
        })
    
    # 5. Extract text entities
    # TEXT entities
    for text in msp.query('TEXT'):
        schema["drawing_schema"]["layers"].add(text.dxf.layer)
        schema["entities"]["texts"].append({
            "text_string": text.dxf.text.strip(),
            "layer": text.dxf.layer,
            "position": [float(round(text.dxf.insert.x, 2)), float(round(text.dxf.insert.y, 2))]
        })
    
    # MTEXT entities
    for mtext in msp.query('MTEXT'):
        content = mtext.plain_text() if hasattr(mtext, 'plain_text') else mtext.text
        
        if content.strip():
            schema["drawing_schema"]["layers"].add(mtext.dxf.layer)
            schema["entities"]["texts"].append({
                "text_string": content.strip(),
                "layer": mtext.dxf.layer,
                "position": [float(round(mtext.dxf.insert.x, 2)), float(round(mtext.dxf.insert.y, 2))]
            })
    
    # 6. Count nearby lines for each block
    for block in schema["entities"]["blocks"]:
        near_lines = 0
        block_pos = block["position"]
        
        for line in schema["entities"]["lines"]:
            # Check first and last vertex only (endpoints)
            start = line["vertices"][0]
            end = line["vertices"][-1]
            if (distance(start, block_pos) < proximity_threshold or 
                distance(end, block_pos) < proximity_threshold):
                near_lines += 1
        
        block["near_lines"] = near_lines
    
    # 7. Convert sets to sorted lists
    schema["drawing_schema"]["layers"] = sorted(list(schema["drawing_schema"]["layers"]))
    schema["drawing_schema"]["block_names"] = sorted(list(schema["drawing_schema"]["block_names"]))
    
    return schema


