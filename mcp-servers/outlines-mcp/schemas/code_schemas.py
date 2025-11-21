"""Code generation schemas for constrained output."""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"


class Parameter(BaseModel):
    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type annotation")
    default: Optional[str] = Field(None, description="Default value if any")
    description: Optional[str] = Field(None, description="Parameter description")


class FunctionSignature(BaseModel):
    name: str = Field(description="Function name")
    parameters: List[Parameter] = Field(default_factory=list)
    return_type: str = Field(description="Return type annotation")
    docstring: Optional[str] = Field(None, description="Function docstring")
    is_async: bool = Field(False, description="Whether function is async")


class ClassDefinition(BaseModel):
    name: str = Field(description="Class name")
    bases: List[str] = Field(default_factory=list, description="Base classes")
    attributes: List[Parameter] = Field(default_factory=list)
    methods: List[FunctionSignature] = Field(default_factory=list)
    docstring: Optional[str] = Field(None)


class CodeBlock(BaseModel):
    language: Language
    code: str = Field(description="The generated code")
    imports: List[str] = Field(default_factory=list, description="Required imports")
    explanation: Optional[str] = Field(None, description="Code explanation")


class CodeReview(BaseModel):
    has_issues: bool
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    quality_score: int = Field(ge=1, le=10)
