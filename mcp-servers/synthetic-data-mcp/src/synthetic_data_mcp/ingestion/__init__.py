"""
Data ingestion module for learning from real data patterns.
"""

from .pattern_analyzer import PatternAnalyzer
from .data_ingestion import DataIngestionPipeline
from .knowledge_loader import DynamicKnowledgeLoader

__all__ = [
    'PatternAnalyzer',
    'DataIngestionPipeline', 
    'DynamicKnowledgeLoader'
]