
import operator
import logging

from typing import (List, Optional, TypedDict, 
                    Annotated
                    )

from pydantic import BaseModel, Field

from langchain.chat_models import init_chat_model

from langgraph.graph import StateGraph, END
from langgraph.graph import add_messages



# our files #

from .PFD_prompt_templates import (PFD_extraction_worker_system_prompt, 
                                   PFD_extraction_auditor_system_prompt,
                                   PFD_generator_system_prompt
                                   )



## logger instance for this module
logger = logging.getLogger(f'pfd_bench.pfd_bench_setup')



########### Classes ###############

### STRUCTURED LLM RESPONSES (pydantic)

# Two classes used by both worker and auditor
class EquipmentRow(BaseModel):
    """Single row from the equipment table
    Note: we use this detailed format in order to use pydantic to control and enforce the output
    In principle we could have used str for the output, but then there yould be no enforcing mechanism."""

    tag: str = Field(..., description="Equipment tag identifier")
    equipment_type: str = Field(..., description="Type/description of equipment")
    inlet_streams: str = Field(..., description="Description of inlet streams")
    inlet_count: int = Field(..., ge=0, description="Number of inlet streams")
    outlet_streams: str = Field(..., description="Description of outlet streams")
    outlet_count: int = Field(..., ge=0, description="Number of outlet streams")
    remarks: str = Field("", description="Additional remarks")


class EquipmentTable(BaseModel):
    """Container for all equipment rows"""

    title: Optional[str] = Field(None, description="Table title (e.g., 'Final Corrected Table')")
    rows: List[EquipmentRow] = Field(..., description="List of equipment rows")

    def to_markdown(self) -> str:
        """Convert table back to markdown format"""

        lines = []
        
        # Add title if present
        if self.title:
            lines.append(f"### {self.title}\n")
        
        # Header
        lines.append("| Tag | Equipment type | Inlet streams | Inlet count | Outlet streams | Outlet count | Remarks |")
        lines.append("|---|---|---|---|---|---|---|")
        
        # Rows
        for row in self.rows:
            lines.append(
                f"| {row.tag} | {row.equipment_type} | {row.inlet_streams} | "
                f"{row.inlet_count} | {row.outlet_streams} | {row.outlet_count} | {row.remarks} |"
            )
        
        return "\n".join(lines)


# classes that only the auditor needs
class AuditFinding(BaseModel):
    """Single audit finding row"""

    tag: str = Field(..., description="Equipment tag with the error")
    column_with_error: str = Field(..., description="Column(s) that contain errors")
    original_value: str = Field(..., description="Original incorrect value")
    corrected_value: str = Field(..., description="Corrected value")
    justification: str = Field(..., description="Explanation for the correction")


class AuditFindingsTable(BaseModel):
    """Container for audit findings"""

    title: Optional[str] = Field(None, description="Table title (e.g., 'Audit Findings Table')")
    findings: List[AuditFinding] = Field(..., description="List of audit findings (rows)")

    def to_markdown(self) -> str:
            """Convert table back to markdown format"""

            lines = []
            
            # Add title if present
            if self.title:
                lines.append(f"### {self.title}\n")
            
            # Header
            lines.append("| Tag | Column with Error | Original Value | Corrected Value | Justification |")
            lines.append("|---|---|---|---|---|")
            
            # Rows
            for row in self.findings:
                lines.append(
                    f"| {row.tag} | {row.column_with_error} | {row.original_value} | "
                    f"{row.corrected_value} | {row.justification} |"
                )
            
            return "\n".join(lines)

class AuditedEquipmentTables(BaseModel):
    """Complete output from the audit process"""

    audit_findings: AuditFindingsTable
    corrected_equipment_table: EquipmentTable


class GeneratorOutput(BaseModel):
    """Process description generated based on the connectivity table"""
    process_description: str = Field(..., description="Detailed process description based on the connectivity table")



### STATES - LangGraph states

class ExtrationState(TypedDict):
    messages: Annotated[list, add_messages]  # communication with the LLM...
    dxf_extract: str  # the transformed input based on the original dxf file
    equipment_table: EquipmentTable
    audit_findings: AuditFindingsTable
    corrected_equipment_table: EquipmentTable

class GenerationState(TypedDict):
    messages: Annotated[list, add_messages]  # communication with the LLM...
    connectivity_table: str  # the table that step 1 generates, in markdown format
    process_description: str # the process description


################################################################
# Singletons - create only once and share across functions
# Global variable to cache them
_pfd_worker_agent = None
_pfd_auditor_agent = None
_pfd_generator_agent = None

def get_pfd_worker_agent():
    """Get or create the pfd agents"""
    global _pfd_worker_agent
    
    if _pfd_worker_agent is None:
        llm = init_chat_model("google_genai:gemini-2.5-pro", temperature=1)
        _pfd_worker_agent = llm.with_structured_output(EquipmentTable)
        logger.info("Created new _pfd_worker_agent instance")
    
    return _pfd_worker_agent

def get_pfd_auditor_agent():
    """Get or create the pfd agents"""
    global _pfd_auditor_agent
    
    if _pfd_auditor_agent is None:
        llm = init_chat_model("google_genai:gemini-2.5-pro", temperature=1)
        _pfd_auditor_agent = llm.with_structured_output(AuditedEquipmentTables)
        logger.info("Created new _pfd_auditor_agent instance")
    
    return _pfd_auditor_agent


def get_pfd_generator_agent():
    """Get or create the pfd agents"""
    global _pfd_generator_agent
    
    if _pfd_generator_agent is None:
        llm = init_chat_model("openai:gpt-4o", temperature=1)
        _pfd_generator_agent = llm.with_structured_output(GeneratorOutput)
        logger.info("Created new _pfd_generator_agent instance")
    
    return _pfd_generator_agent



###################################################################
# Nodes
###################################################################


def worker_node(state:ExtrationState) -> ExtrationState:

    logger.info("entered worker")
    
    this_llm = get_pfd_worker_agent()
    
    # import the prompt for this function
    message_for_llm = [{"role": "system", "content": PFD_extraction_worker_system_prompt},
                      {"role": "user", "content": state['dxf_extract']}
                      ]
    
    result = this_llm.invoke(message_for_llm)

    state["equipment_table"] = result
    
    logger.info("left worker")
    
    return state


def auditor_node(state:ExtrationState) -> ExtrationState:

    logger.info("entered auditor")

    this_llm = get_pfd_auditor_agent()
    
    # Convert to markdown using the method from the equipment_table class
    table_markdown = state["equipment_table"].to_markdown()

    # import the prompt for this function
    message_for_llm = [{"role": "system", "content": PFD_extraction_auditor_system_prompt},
                      {"role": "user", "content": f""" 
                      1) The original JSON data file containing the Process Flow Diagram extract: 
                      {state['dxf_extract']}
    
                      2) The candidate markdown table produced by the junior engineer:
                      {table_markdown}
                      """}
                      ]
    
    result = this_llm.invoke(message_for_llm)
    state['audit_findings'] = result.audit_findings
    state['corrected_equipment_table'] = result.corrected_equipment_table

    logger.info("left auditor")
    
    return state


def generator_node(state:GenerationState) -> GenerationState:

    logger.info("entered generator")

    this_llm = get_pfd_generator_agent()
    
    # import the prompt for this function
    message_for_llm = [{"role": "system", "content": PFD_generator_system_prompt},
                      {"role": "user", "content": state["connectivity_table"]}
                      ]
    
    result = this_llm.invoke(message_for_llm)
    state['process_description'] = result.process_description
    
    logger.info("left generator")
    
    return state


###################################################################
# Agents
###################################################################





###################################################################
# Graphs
###################################################################

def pfd_bench_st1_setup():
    """
    We set up a graph for the first leg of the workflow: 
    worker and auditor, the output will be reviewed by a human
    """
    workflow = StateGraph(ExtrationState)
 
    workflow.add_node("worker_node", worker_node)
    workflow.add_node("auditor_node", auditor_node)
    
    workflow.add_edge("worker_node", "auditor_node")
    workflow.add_edge("auditor_node", END)
    
    workflow.set_entry_point("worker_node") 
    
    pfd_bench_st1_graph = workflow.compile()

    return pfd_bench_st1_graph


def pfd_bench_st2_setup():
    """
    We set up a graph for the second leg of the workflow: 
    After human review, get the connectivity table and prepare a process description
    """
    workflow = StateGraph(GenerationState)
 
    workflow.add_node("generator_node", generator_node)
    #workflow.add_node("auditor_generated_node", auditor_generated_node)  # later in time we may add this
    
    workflow.add_edge("generator_node", END)
    
    workflow.set_entry_point("generator_node") 
    
    pfd_bench_st2_graph = workflow.compile()

    return pfd_bench_st2_graph