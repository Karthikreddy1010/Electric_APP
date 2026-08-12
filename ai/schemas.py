"""
Pydantic Data Schemas for Grounded Tool-Using AI Assistant.
"""
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class SourceAuthorityRating(str, Enum):
    HIGH = "high"          # Official government datasets (EIA, NOAA, EPA, BPU)
    MEDIUM = "medium"      # Utility official portals, verified industry databases
    LOW = "low"         # Secondary sources, general web search
    UNVERIFIED = "unverified"  # Unsubstantiated / LLM memory


class ClaimConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class SourceMetadata(BaseModel):
    source_id: str
    title: str
    url: Optional[str] = None
    publication_date: Optional[str] = None
    authority: SourceAuthorityRating = SourceAuthorityRating.HIGH
    geography: Optional[str] = None
    temporal_coverage: Optional[str] = None
    text_snippet: Optional[str] = None
    retrieval_timestamp: Optional[str] = None


class ClaimItem(BaseModel):
    claim_id: str
    claim_text: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    tool_name: str
    raw_output_key: str
    source_provenance: Optional[SourceMetadata] = None
    confidence: ClaimConfidence = ClaimConfidence.HIGH


class CalculationItem(BaseModel):
    calculation_id: str
    formula: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    result: Union[float, int, Dict[str, Any], List[Any]]
    unit: Optional[str] = None
    deterministic_engine: str


class ConflictingSourceItem(BaseModel):
    metric: str
    geography: Optional[str] = None
    year: Optional[int] = None
    sources_compared: List[SourceMetadata] = Field(default_factory=list)
    values_reported: Dict[str, Any] = Field(default_factory=dict)
    resolution_explanation: str
    selected_source: Optional[SourceMetadata] = None


class EvidenceObject(BaseModel):
    question: str
    claims: List[ClaimItem] = Field(default_factory=list)
    calculations: List[CalculationItem] = Field(default_factory=list)
    external_sources: List[SourceMetadata] = Field(default_factory=list)
    conflicting_sources: List[ConflictingSourceItem] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    overall_confidence: ClaimConfidence = ClaimConfidence.HIGH


class GeographicScope(str, Enum):
    CUSTOMER = "customer"
    COUNTY = "county"
    STATE = "state"
    REGIONAL = "regional"
    NATIONAL = "national"


class StructuredQueryRequirement(BaseModel):
    intent: str
    geography_scope: GeographicScope = GeographicScope.CUSTOMER
    state_code: Optional[str] = None  # e.g., "NJ", "TX", "CA"
    year: Optional[int] = None        # e.g., 2024, 2025
    month: Optional[int] = None
    required_metrics: List[str] = Field(default_factory=list)
    is_calculation_required: bool = False
    is_external_retrieval_required: bool = False


class ToolResult(BaseModel):
    success: bool
    tool_name: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    source_metadata: Optional[SourceMetadata] = None


class GroundedResponse(BaseModel):
    answer: str
    evidence: EvidenceObject
    sources: List[SourceMetadata] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    data_freshness: Optional[str] = None
    calculations: List[CalculationItem] = Field(default_factory=list)
    grounded: bool = True
    unverified_claims_blocked: int = 0
