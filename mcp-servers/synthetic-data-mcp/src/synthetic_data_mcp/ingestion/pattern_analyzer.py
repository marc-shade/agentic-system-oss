"""
Pattern analyzer for learning from real data samples.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import Counter, defaultdict
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats
from loguru import logger


class PatternAnalyzer:
    """Analyzes and learns patterns from real data samples."""
    
    def __init__(self):
        """Initialize the pattern analyzer."""
        self.patterns = {}
        self.distributions = {}
        self.relationships = {}
        self.business_rules = {}
        
    def analyze_structure(self, data: Union[List[Dict], pd.DataFrame]) -> Dict[str, Any]:
        """
        Detect schema, types, and relationships from data.
        
        Args:
            data: Input data as list of dicts or DataFrame
            
        Returns:
            Structure analysis including schema, types, and relationships
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
            
        structure = {
            "columns": {},
            "relationships": [],
            "constraints": [],
            "statistics": {}
        }
        
        # Analyze each column
        for col in df.columns:
            col_analysis = self._analyze_column(df[col])
            structure["columns"][col] = col_analysis
            
        # Detect relationships
        structure["relationships"] = self._detect_relationships(df)
        
        # Identify constraints
        structure["constraints"] = self._identify_constraints(df)
        
        # Calculate statistics
        structure["statistics"] = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum(),
            "missing_values": df.isnull().sum().to_dict()
        }
        
        logger.info(f"Structure analysis complete: {len(df.columns)} columns, {len(df)} rows")
        return structure
    
    def learn_distributions(self, data: Union[List[Dict], pd.DataFrame]) -> Dict[str, Any]:
        """
        Learn statistical distributions from data.
        
        Args:
            data: Input data as list of dicts or DataFrame
            
        Returns:
            Distribution parameters for each column
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
            
        distributions = {}
        
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                distributions[col] = self._fit_numeric_distribution(df[col].dropna())
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                distributions[col] = self._analyze_temporal_patterns(df[col].dropna())
            else:
                distributions[col] = self._extract_categorical_patterns(df[col].dropna())
                
        self.distributions = distributions
        logger.info(f"Learned distributions for {len(distributions)} columns")
        return distributions
    
    def extract_business_rules(self, data: Union[List[Dict], pd.DataFrame]) -> Dict[str, Any]:
        """
        Discover business logic and constraints from data.
        
        Args:
            data: Input data as list of dicts or DataFrame
            
        Returns:
            Discovered business rules and correlations
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
            
        rules = {
            "correlations": {},
            "dependencies": {},
            "validations": [],
            "patterns": {}
        }
        
        # Find correlations
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            significant_corr = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    if abs(corr_matrix.iloc[i, j]) > 0.5:
                        significant_corr.append({
                            "col1": corr_matrix.columns[i],
                            "col2": corr_matrix.columns[j],
                            "correlation": corr_matrix.iloc[i, j]
                        })
            rules["correlations"] = significant_corr
        
        # Detect dependencies
        rules["dependencies"] = self._detect_dependencies(df)
        
        # Infer validation rules
        rules["validations"] = self._infer_validation_rules(df)
        
        # Extract patterns
        rules["patterns"] = self._extract_patterns(df)
        
        self.business_rules = rules
        logger.info(f"Extracted {len(rules['validations'])} validation rules")
        return rules
    
    def _analyze_column(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze a single column."""
        analysis = {
            "dtype": str(series.dtype),
            "unique_count": series.nunique(),
            "null_count": series.isnull().sum(),
            "null_percentage": (series.isnull().sum() / len(series)) * 100
        }
        
        if pd.api.types.is_numeric_dtype(series):
            analysis.update({
                "min": float(series.min()) if not series.empty else None,
                "max": float(series.max()) if not series.empty else None,
                "mean": float(series.mean()) if not series.empty else None,
                "std": float(series.std()) if not series.empty else None,
                "quartiles": series.quantile([0.25, 0.5, 0.75]).to_dict() if not series.empty else {}
            })
        elif pd.api.types.is_datetime64_any_dtype(series):
            analysis.update({
                "min_date": str(series.min()) if not series.empty else None,
                "max_date": str(series.max()) if not series.empty else None,
                "date_range_days": (series.max() - series.min()).days if not series.empty else 0
            })
        else:
            # Categorical
            value_counts = series.value_counts()
            analysis.update({
                "top_values": value_counts.head(10).to_dict(),
                "cardinality": len(value_counts),
                "mode": value_counts.index[0] if not value_counts.empty else None
            })
            
        return analysis
    
    def _fit_numeric_distribution(self, series: pd.Series) -> Dict[str, Any]:
        """Fit statistical distribution to numeric data."""
        if len(series) < 10:
            return {"type": "empirical", "values": series.tolist()}
            
        # Try to fit common distributions
        distributions = ['norm', 'expon', 'gamma', 'beta', 'lognorm']
        best_dist = None
        best_params = None
        best_ks_stat = float('inf')
        
        for dist_name in distributions:
            try:
                dist = getattr(stats, dist_name)
                params = dist.fit(series)
                ks_stat, _ = stats.kstest(series, dist_name, args=params)
                
                if ks_stat < best_ks_stat:
                    best_dist = dist_name
                    best_params = params
                    best_ks_stat = ks_stat
            except:
                continue
                
        if best_dist:
            return {
                "type": "fitted",
                "distribution": best_dist,
                "params": best_params,
                "ks_statistic": best_ks_stat
            }
        else:
            # Fall back to empirical distribution
            return {
                "type": "empirical",
                "mean": float(series.mean()),
                "std": float(series.std()),
                "min": float(series.min()),
                "max": float(series.max()),
                "quantiles": series.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).to_dict()
            }
    
    def _analyze_temporal_patterns(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze temporal patterns in datetime data."""
        if len(series) < 2:
            return {"type": "single_value", "value": str(series.iloc[0])}
            
        # Calculate time differences
        sorted_series = series.sort_values()
        time_diffs = sorted_series.diff().dropna()
        
        return {
            "type": "temporal",
            "min_date": str(sorted_series.min()),
            "max_date": str(sorted_series.max()),
            "mean_interval_seconds": float(time_diffs.mean().total_seconds()) if not time_diffs.empty else 0,
            "std_interval_seconds": float(time_diffs.std().total_seconds()) if len(time_diffs) > 1 else 0,
            "day_of_week_distribution": series.dt.dayofweek.value_counts().to_dict() if hasattr(series.dt, 'dayofweek') else {},
            "hour_distribution": series.dt.hour.value_counts().to_dict() if hasattr(series.dt, 'hour') else {}
        }
    
    def _extract_categorical_patterns(self, series: pd.Series) -> Dict[str, Any]:
        """Extract patterns from categorical data."""
        value_counts = series.value_counts()
        total_count = len(series)
        
        return {
            "type": "categorical",
            "frequencies": (value_counts / total_count).to_dict(),
            "unique_values": value_counts.index.tolist(),
            "entropy": stats.entropy(value_counts.values) if len(value_counts) > 1 else 0,
            "mode": value_counts.index[0] if not value_counts.empty else None,
            "cardinality": len(value_counts)
        }
    
    def _detect_relationships(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect relationships between columns."""
        relationships = []
        
        # Check for potential foreign keys (columns with similar names)
        for col1 in df.columns:
            for col2 in df.columns:
                if col1 != col2:
                    # Check if one column name is contained in another
                    if col1.lower() in col2.lower() or col2.lower() in col1.lower():
                        if col1.endswith('_id') or col2.endswith('_id'):
                            relationships.append({
                                "type": "potential_foreign_key",
                                "from": col1,
                                "to": col2,
                                "confidence": 0.7
                            })
        
        # Check for functional dependencies
        for col1 in df.columns:
            for col2 in df.columns:
                if col1 != col2:
                    if df.groupby(col1)[col2].nunique().max() == 1:
                        relationships.append({
                            "type": "functional_dependency",
                            "from": col1,
                            "to": col2,
                            "confidence": 0.9
                        })
        
        return relationships
    
    def _identify_constraints(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify data constraints."""
        constraints = []
        
        for col in df.columns:
            # Check for uniqueness
            if df[col].nunique() == len(df):
                constraints.append({
                    "type": "unique",
                    "column": col
                })
            
            # Check for non-null
            if df[col].isnull().sum() == 0:
                constraints.append({
                    "type": "not_null",
                    "column": col
                })
            
            # Check for range constraints (numeric columns)
            if pd.api.types.is_numeric_dtype(df[col]):
                if df[col].min() >= 0:
                    constraints.append({
                        "type": "positive",
                        "column": col
                    })
                
        return constraints
    
    def _detect_dependencies(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Detect column dependencies."""
        dependencies = defaultdict(list)
        
        # Simple dependency detection based on correlation and patterns
        for col1 in df.columns:
            for col2 in df.columns:
                if col1 != col2:
                    # Check if values in col2 are determined by col1
                    grouped = df.groupby(col1)[col2].apply(lambda x: len(x.unique()))
                    if grouped.max() == 1:
                        dependencies[col1].append(col2)
        
        return dict(dependencies)
    
    def _infer_validation_rules(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Infer validation rules from data."""
        rules = []
        
        for col in df.columns:
            series = df[col]
            
            # String pattern rules
            if series.dtype == 'object':
                # Check for email pattern
                if series.str.contains(r'^[\w\.-]+@[\w\.-]+\.\w+$', na=False).any():
                    rules.append({
                        "column": col,
                        "type": "pattern",
                        "pattern": "email"
                    })
                
                # Check for phone pattern
                if series.str.contains(r'^\+?\d{10,15}$', na=False).any():
                    rules.append({
                        "column": col,
                        "type": "pattern",
                        "pattern": "phone"
                    })
                
                # Check for consistent length
                lengths = series.str.len().dropna()
                if not lengths.empty and lengths.std() == 0:
                    rules.append({
                        "column": col,
                        "type": "length",
                        "value": int(lengths.iloc[0])
                    })
            
            # Numeric range rules
            if pd.api.types.is_numeric_dtype(series):
                rules.append({
                    "column": col,
                    "type": "range",
                    "min": float(series.min()),
                    "max": float(series.max())
                })
        
        return rules
    
    def _extract_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract complex patterns from data."""
        patterns = {}
        
        # Temporal patterns
        date_cols = df.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0:
            patterns["temporal"] = {}
            for col in date_cols:
                if df[col].notna().sum() > 0:
                    patterns["temporal"][col] = {
                        "weekday_distribution": df[col].dt.dayofweek.value_counts().to_dict(),
                        "monthly_distribution": df[col].dt.month.value_counts().to_dict()
                    }
        
        # Sequence patterns
        patterns["sequences"] = self._find_sequence_patterns(df)
        
        return patterns
    
    def _find_sequence_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Find sequence patterns in data."""
        sequences = {}
        
        # Look for incrementing IDs
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                sorted_vals = df[col].sort_values()
                diffs = sorted_vals.diff().dropna()
                if not diffs.empty and (diffs == 1).all():
                    sequences[col] = {
                        "type": "sequential",
                        "increment": 1,
                        "start": int(sorted_vals.min()),
                        "end": int(sorted_vals.max())
                    }
        
        return sequences
    
    def generate_pattern_summary(self, data: Union[List[Dict], pd.DataFrame]) -> Dict[str, Any]:
        """
        Generate a comprehensive pattern summary from data.
        
        Args:
            data: Input data to analyze
            
        Returns:
            Complete pattern analysis summary
        """
        structure = self.analyze_structure(data)
        distributions = self.learn_distributions(data)
        business_rules = self.extract_business_rules(data)
        
        summary = {
            "structure": structure,
            "distributions": distributions,
            "business_rules": business_rules,
            "metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "row_count": structure["statistics"]["row_count"],
                "column_count": structure["statistics"]["column_count"]
            }
        }
        
        logger.info("Pattern summary generated successfully")
        return summary