"""
Pydantic models for Quran verses
Provides type safety and automatic validation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class VerseReference(BaseModel):
    """Model for verse reference"""
    surah: int = Field(..., ge=1, le=114, description="Surah number (1-114)")
    verse: int = Field(..., ge=1, description="Verse number")

    @field_validator('surah')
    @classmethod
    def validate_surah(cls, v):
        if not 1 <= v <= 114:
            raise ValueError(f"Surah number must be between 1 and 114, got {v}")
        return v

    def to_string(self) -> str:
        """Convert to string format (e.g., '2:255')"""
        return f"{self.surah}:{self.verse}"

    @classmethod
    def from_string(cls, ref: str) -> 'VerseReference':
        """Create from string format (e.g., '2:255')"""
        parts = ref.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid verse reference format: {ref}")
        return cls(surah=int(parts[0]), verse=int(parts[1]))


class VerseData(BaseModel):
    """Model for complete verse data"""
    surah_number: int = Field(..., ge=1, le=114)
    verse_number: int = Field(..., ge=1)
    arabic_text: str = Field(..., min_length=1, description="Arabic text of the verse")
    english_text: str = Field(..., min_length=1, description="English translation")
    transliteration: Optional[str] = Field(None, description="Transliteration of Arabic")
    surah_name: Optional[str] = Field(None, description="Name of the Surah")
    is_supplementary: bool = Field(False, description="Whether this is a supplementary verse")

    @property
    def reference(self) -> str:
        """Get verse reference as string"""
        return f"{self.surah_number}:{self.verse_number}"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VerseRange(BaseModel):
    """Model for verse range"""
    surah: int = Field(..., ge=1, le=114)
    start_verse: int = Field(..., ge=1)
    end_verse: int = Field(..., ge=1)

    @field_validator('end_verse')
    @classmethod
    def validate_range(cls, v, values):
        if 'start_verse' in values.data and v < values.data['start_verse']:
            raise ValueError("End verse must be greater than or equal to start verse")
        return v

    def to_string(self) -> str:
        """Convert to string format (e.g., '2:255-257')"""
        return f"{self.surah}:{self.start_verse}-{self.end_verse}"


class CrossReference(BaseModel):
    """Model for cross-reference"""
    verse: str = Field(..., description="Verse reference (e.g., '2:256')")
    arabic_text: Optional[str] = Field(None, description="Arabic text if available")
    english_text: Optional[str] = Field(None, description="English translation if available")
    relevance: str = Field(..., min_length=10, description="Explanation of relevance")

    @field_validator('verse')
    @classmethod
    def validate_verse_format(cls, v):
        try:
            VerseReference.from_string(v)
        except Exception:
            raise ValueError(f"Invalid verse reference format: {v}")
        return v


class VerseMetadata(BaseModel):
    """Model for verse metadata"""
    themes: List[str] = Field(default_factory=list, description="Major themes")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    context: Optional[str] = Field(None, description="Historical context")
    revelation_order: Optional[int] = Field(None, description="Order of revelation")
    location: Optional[str] = Field(None, pattern="^(Meccan|Medinan)$", description="Revelation location")
    related_hadith: List[str] = Field(default_factory=list, description="Related hadith references")


class VerseWithMetadata(VerseData):
    """Model combining verse data with metadata"""
    metadata: Optional[VerseMetadata] = None
    tafsir_available: List[str] = Field(default_factory=list, description="Available tafsir sources")
    cross_references: List[CrossReference] = Field(default_factory=list)


class VerseSearchQuery(BaseModel):
    """Model for verse search query"""
    query: str = Field(..., min_length=1, max_length=500)
    approach: str = Field("tafsir", pattern="^(tafsir|explore)$")
    include_metadata: bool = Field(True)
    include_cross_references: bool = Field(True)
    limit: int = Field(10, ge=1, le=50)