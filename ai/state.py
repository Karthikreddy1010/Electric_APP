"""
LangGraph Assistant State definition for Grounded AI Assistant.
"""
from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class AssistantState(TypedDict, total=False):
    user_query: str
    history: List[Dict[str, Any]]
    current_tab: Optional[str]
    context_data: Dict[str, Any]
    user_tier: str
    
    # Query Requirement & Routing
    query_requirement: Optional[Dict[str, Any]]
    
    # LangChain message sequence
    messages: List[BaseMessage]
    
    # Tool Execution
    executed_tools: List[str]
    tool_outputs: List[Dict[str, Any]]
    
    # Evidence & Validation
    evidence: Optional[Dict[str, Any]]
    generated_text: Optional[str]
    validated_response: Optional[Dict[str, Any]]
    unverified_blocked: int
    
    # Timing & Observability
    metadata: Dict[str, Any]
