"""
Pydantic models for Tafsir responses
Ensures proper structure and validation of API responses
"""

from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from .verse_models import VerseData, CrossReference


class TafsirExplanation(BaseModel):
    """Model for tafsir explanation from a source"""
    source: Literal["Ibn Kathir", "al-Qurtubi"] = Field(..., description="Tafsir source")
    explanation: str = Field(..., min_length=50, description="Tafsir explanation text")

    @field_validator('explanation')
    @classmethod
    def validate_explanation(cls, v):
        if len(v) < 50:
            raise ValueError("Explanation must be at least 50 characters")
        if "Limited relevant content" in v:
            raise ValueError("Explanation contains placeholder text")
        return v


class Lesson(BaseModel):
    """Model for practical lesson/application"""
    point: str = Field(..., min_length=10, description="Practical lesson or application")

    @field_validator('point')
    @classmethod
    def validate_point(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Lesson point must be meaningful (at least 10 characters)")
        return v.strip()


class TafsirResponse(BaseModel):
    """Model for complete tafsir response"""
    verses: List[VerseData] = Field(..., min_items=1, description="Verses being explained")
    tafsir_explanations: List[TafsirExplanation] = Field(
        ..., min_items=2, max_items=2, description="Exactly 2 tafsir sources"
    )
    cross_references: List[CrossReference] = Field(default_factory=list, description="Related verses")
    lessons_practical_applications: List[Lesson] = Field(
        ..., min_items=2, description="At least 2 practical lessons"
    )
    summary: str = Field(..., min_length=50, max_length=500, description="2-3 sentence summary")
    section_headers: Optional[Dict[str, str]] = Field(None, description="Section headers for UI")
    supplementary_verses: Optional[List[VerseData]] = Field(None, description="Additional referenced verses")

    @model_validator(mode='after')
    def validate_tafsir_sources(self):
        """Ensure we have exactly Ibn Kathir and al-Qurtubi"""
        sources = {exp.source for exp in self.tafsir_explanations}
        if sources != {"Ibn Kathir", "al-Qurtubi"}:
            # Try to fix if one is missing
            if len(self.tafsir_explanations) == 1:
                missing = {"Ibn Kathir", "al-Qurtubi"} - sources
                self.tafsir_explanations.append(
                    TafsirExplanation(
                        source=list(missing)[0],
                        explanation="Commentary not available for this verse from this source."
                    )
                )
        return self

    @model_validator(mode='after')
    def add_section_headers(self):
        """Add section headers if not present"""
        if not self.section_headers:
            self.section_headers = {
                'summary': '📚 Summary',
                'verses': '📖 Verses',
                'tafsir': '📝 Classical Commentary',
                'cross_references': '🔗 Related Verses',
                'lessons': '💡 Lessons & Applications'
            }
        return self

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TafsirRequest(BaseModel):
    """Model for tafsir API request"""
    query: str = Field(..., min_length=1, max_length=500, description="User query")
    approach: Literal["tafsir", "explore"] = Field("tafsir", description="Query approach")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="User profile for personalization")
    include_arabic: bool = Field(True, description="Include Arabic text")
    include_cross_references: bool = Field(True, description="Include cross-references")
    max_verses: int = Field(10, ge=1, le=50, description="Maximum verses to return")


class ErrorResponse(BaseModel):
    """Model for error responses"""
    error: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")
    retry: bool = Field(False, description="Whether client should retry")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class CacheMetadata(BaseModel):
    """Model for cache metadata"""
    cache_key: str = Field(..., description="Cache key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    hit_count: int = Field(0, ge=0)
    last_accessed: Optional[datetime] = None
    compressed: bool = Field(False)
    size_bytes: int = Field(0, ge=0)


class QueryClassification(BaseModel):
    """Model for query classification results"""
    query_type: Literal["verse", "range", "thematic", "question"] = Field(..., description="Type of query")
    verse_refs: List[str] = Field(default_factory=list, description="Extracted verse references")
    themes: List[str] = Field(default_factory=list, description="Identified themes")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Classification confidence")


class RetrievalPlan(BaseModel):
    """Model for LLM retrieval plan"""
    query_intent: str = Field(..., description="Interpreted query intent")
    primary_verses: List[str] = Field(..., min_items=1, description="Primary verses to retrieve")
    contextual_verses: List[str] = Field(default_factory=list, description="Additional context verses")
    tafsir_sources: List[str] = Field(default=["Ibn Kathir", "al-Qurtubi"])
    include_cross_references: bool = Field(True)
    focus_topics: List[str] = Field(default_factory=list, description="Topics to focus on")


class PerformanceMetrics(BaseModel):
    """Model for tracking performance metrics"""
    request_id: str = Field(..., description="Unique request ID")
    cache_hit: bool = Field(False)
    cache_tier: Optional[Literal["redis", "firestore"]] = None
    response_time_ms: float = Field(..., ge=0)
    tokens_used: Optional[int] = None
    firestore_reads: int = Field(0, ge=0)
    redis_operations: int = Field(0, ge=0)