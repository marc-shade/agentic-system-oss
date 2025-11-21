"""Data extraction schemas for structured output."""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Entity(BaseModel):
    name: str
    type: str = Field(description="Entity type: person, organization, location, etc.")
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedData(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    summary: str = Field(description="Brief summary of content")
    sentiment: Sentiment


class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None


class StructuredDocument(BaseModel):
    title: str
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: Optional[str] = None


class TableRow(BaseModel):
    columns: Dict[str, Any]


class ExtractedTable(BaseModel):
    headers: List[str]
    rows: List[TableRow]
    source_description: Optional[str] = None


class DataValidation(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    parsed_value: Optional[Any] = None
