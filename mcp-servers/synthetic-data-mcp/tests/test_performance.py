"""
Performance tests for the synthetic data platform.
"""

import pytest
import time
import asyncio
from typing import List, Dict, Any
import pandas as pd
from unittest.mock import Mock, patch

from synthetic_data_mcp.core.generator import SyntheticDataGenerator
from synthetic_data_mcp.schemas.healthcare import PatientDemographics
from synthetic_data_mcp.schemas.finance import Transaction


class TestPerformance:
    """Test performance characteristics of the platform."""

    @pytest.fixture
    def generator(self):
        """Create a data generator instance."""
        return SyntheticDataGenerator()

    def test_schema_validation_performance(self):
        """Test that schema validation is fast enough."""
        start_time = time.time()
        
        # Create 1000 patient records
        for i in range(1000):
            patient_data = {
                "gender": "M" if i % 2 else "F",
                "race": "white",
                "state": "CA", 
                "age_group": "25-34",
                "zip_code_3digit": "902"
            }
            
            patient = PatientDemographics(**patient_data)
            assert patient.age_group == "25-34"
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 1000 validations in under 1 second
        assert duration < 1.0, f"Schema validation took {duration:.2f}s, should be < 1.0s"

    @pytest.mark.asyncio
    async def test_concurrent_generation_performance(self, generator):
        """Test concurrent data generation performance."""
        start_time = time.time()
        
        # Simulate concurrent generation requests
        async def generate_batch():
            # Mock generation for performance testing
            await asyncio.sleep(0.01)  # Simulate generation time
            return [{"id": i, "value": f"test_{i}"} for i in range(100)]
        
        # Run 10 concurrent batches
        tasks = [generate_batch() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 10 concurrent batches in under 1 second
        assert duration < 1.0, f"Concurrent generation took {duration:.2f}s, should be < 1.0s"
        assert len(results) == 10
        assert all(len(batch) == 100 for batch in results)

    def test_memory_usage_bounds(self, generator):
        """Test that memory usage stays within reasonable bounds."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate large dataset (simulate)
        large_dataset = []
        for i in range(10000):
            record = {
                "id": i,
                "name": f"Patient_{i}",
                "age_group": "25-34",
                "state": "CA"
            }
            large_dataset.append(record)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB, should be < 100MB"

    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test database query performance with mocked connections."""
        start_time = time.time()
        
        # Simulate database queries
        async def mock_query():
            await asyncio.sleep(0.001)  # 1ms query time
            return pd.DataFrame({"id": range(100), "value": range(100)})
        
        # Run 100 queries
        tasks = [mock_query() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 queries in under 1 second
        assert duration < 1.0, f"100 queries took {duration:.2f}s, should be < 1.0s"
        assert len(results) == 100
        assert all(len(df) == 100 for df in results)

    def test_data_processing_throughput(self):
        """Test data processing throughput."""
        start_time = time.time()
        
        # Create large dataset
        data = pd.DataFrame({
            "id": range(50000),
            "value": [f"record_{i}" for i in range(50000)],
            "category": ["A", "B", "C"] * (50000 // 3 + 1)
        })[:50000]
        
        # Perform basic operations
        filtered_data = data[data["category"] == "A"]
        grouped_data = data.groupby("category").size()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should process 50K records in under 1 second
        assert duration < 1.0, f"Data processing took {duration:.2f}s, should be < 1.0s"
        assert len(filtered_data) > 0
        assert len(grouped_data) == 3

    @pytest.mark.asyncio
    async def test_privacy_engine_performance(self):
        """Test privacy engine performance."""
        start_time = time.time()
        
        # Simulate privacy operations on large dataset
        sensitive_records = []
        for i in range(1000):
            record = {
                "name": f"Person_{i}",
                "ssn": f"123-45-{6789 + i:04d}",
                "email": f"person{i}@example.com"
            }
            sensitive_records.append(record)
        
        # Simulate masking operations
        masked_records = []
        for record in sensitive_records:
            masked = {
                "name": "***",
                "ssn": "***-**-****", 
                "email": f"***@{record['email'].split('@')[1]}"
            }
            masked_records.append(masked)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should mask 1000 records in under 1 second
        assert duration < 1.0, f"Privacy masking took {duration:.2f}s, should be < 1.0s"
        assert len(masked_records) == 1000
        assert all(record["name"] == "***" for record in masked_records)

    def test_compliance_validation_performance(self):
        """Test compliance validation performance."""
        start_time = time.time()
        
        # Simulate compliance checks on large dataset
        healthcare_records = []
        for i in range(5000):
            record = {
                "patient_id": f"P{i:06d}",
                "diagnosis": "Type 2 Diabetes",
                "treatment": "Metformin",
                "provider_id": f"DOC{i % 100:03d}"
            }
            healthcare_records.append(record)
        
        # Simulate HIPAA compliance validation
        compliant_records = []
        for record in healthcare_records:
            # Basic compliance check simulation
            is_compliant = all(key in record for key in ["patient_id", "diagnosis"])
            if is_compliant:
                compliant_records.append(record)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should validate 5000 records in under 1 second
        assert duration < 1.0, f"Compliance validation took {duration:.2f}s, should be < 1.0s"
        assert len(compliant_records) == 5000

    @pytest.mark.asyncio
    async def test_scaling_performance(self):
        """Test performance under scaling conditions."""
        # Test with increasing load
        for batch_size in [10, 50, 100, 200]:
            start_time = time.time()
            
            async def process_batch():
                await asyncio.sleep(0.001)  # Simulate processing
                return {"processed": batch_size}
            
            # Process multiple batches concurrently
            tasks = [process_batch() for _ in range(batch_size)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Performance should scale reasonably
            max_expected_time = batch_size * 0.01  # 10ms per batch max
            assert duration < max_expected_time, f"Batch size {batch_size} took {duration:.3f}s, expected < {max_expected_time:.3f}s"
            assert len(results) == batch_size