"""
Comprehensive tests for all MCP server endpoints - targeting 100% coverage.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime

# Import server and related components
from synthetic_data_mcp.server import app
from mcp.types import Tool, TextContent, CallToolResult


class TestMCPServerEndpoints:
    """Comprehensive tests for all MCP server endpoints."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return SyntheticDataMCPServer()
    
    @pytest.fixture
    def sample_schema(self):
        """Sample schema for testing."""
        return {
            "name": "users",
            "columns": [
                {"name": "id", "type": "integer", "constraints": ["primary_key"]},
                {"name": "name", "type": "varchar", "max_length": 255},
                {"name": "email", "type": "varchar", "max_length": 255},
                {"name": "age", "type": "integer", "min_value": 18, "max_value": 120}
            ]
        }
    
    @pytest.fixture
    def sample_generation_request(self):
        """Sample generation request for testing."""
        return {
            "schema_name": "users",
            "num_records": 100,
            "format": "json",
            "privacy_level": "medium",
            "seed": 42
        }

    def test_server_initialization(self, server):
        """Test server initialization."""
        assert server is not None
        assert hasattr(server, 'database_manager')
        assert hasattr(server, 'generator')
        assert hasattr(server, 'privacy_engine')

    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test listing available tools."""
        tools = await server.list_tools()
        
        assert len(tools.tools) > 0
        tool_names = [tool.name for tool in tools.tools]
        
        # Verify all expected tools are present
        expected_tools = [
            'generate_synthetic_data',
            'validate_schema',
            'analyze_data_distribution',
            'apply_privacy_constraints',
            'compare_datasets',
            'export_data',
            'import_schema',
            'get_generation_history',
            'optimize_generation_parameters',
            'batch_generate_data',
            'validate_privacy_compliance',
            'analyze_data_quality',
            'generate_data_report',
            'manage_data_lineage',
            'configure_database_connection',
            'test_database_connection',
            'list_available_schemas',
            'create_custom_schema',
            'delete_schema'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_generate_synthetic_data_success(self, server, sample_generation_request):
        """Test successful synthetic data generation."""
        with patch.object(server.generator, 'generate_data') as mock_generate:
            mock_data = pd.DataFrame({
                'id': [1, 2, 3],
                'name': ['Alice', 'Bob', 'Charlie'],
                'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com'],
                'age': [25, 30, 35]
            })
            mock_generate.return_value = mock_data
            
            result = await server.call_tool(
                "generate_synthetic_data",
                sample_generation_request
            )
            
            assert isinstance(result, CallToolResult)
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['records_generated'] == 3
            assert 'data' in response_data

    @pytest.mark.asyncio
    async def test_generate_synthetic_data_invalid_schema(self, server):
        """Test data generation with invalid schema."""
        invalid_request = {
            "schema_name": "nonexistent_schema",
            "num_records": 100
        }
        
        with patch.object(server.generator, 'generate_data') as mock_generate:
            mock_generate.side_effect = ValueError("Schema not found")
            
            result = await server.call_tool(
                "generate_synthetic_data", 
                invalid_request
            )
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is False
            assert 'error' in response_data

    @pytest.mark.asyncio
    async def test_validate_schema_success(self, server, sample_schema):
        """Test successful schema validation."""
        with patch.object(server.generator, 'validate_schema') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'issues': [],
                'recommendations': []
            }
            
            result = await server.call_tool("validate_schema", sample_schema)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['validation_result']['valid'] is True

    @pytest.mark.asyncio
    async def test_validate_schema_invalid(self, server):
        """Test schema validation with invalid schema."""
        invalid_schema = {
            "name": "invalid_schema",
            "columns": [
                {"name": "id", "type": "unknown_type"}  # Invalid type
            ]
        }
        
        with patch.object(server.generator, 'validate_schema') as mock_validate:
            mock_validate.return_value = {
                'valid': False,
                'issues': ['Unknown column type: unknown_type'],
                'recommendations': ['Use supported types: integer, varchar, etc.']
            }
            
            result = await server.call_tool("validate_schema", invalid_schema)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['validation_result']['valid'] is False
            assert len(response_data['validation_result']['issues']) > 0

    @pytest.mark.asyncio
    async def test_analyze_data_distribution_success(self, server):
        """Test successful data distribution analysis."""
        analysis_request = {
            "data_source": "users_table",
            "columns": ["age", "salary"],
            "analysis_type": "statistical"
        }
        
        with patch.object(server.generator, 'analyze_distribution') as mock_analyze:
            mock_analyze.return_value = {
                'age': {
                    'mean': 35.5,
                    'median': 34.0,
                    'std': 12.3,
                    'min': 18,
                    'max': 65,
                    'distribution_type': 'normal'
                },
                'salary': {
                    'mean': 75000,
                    'median': 70000,
                    'std': 25000,
                    'min': 30000,
                    'max': 150000,
                    'distribution_type': 'lognormal'
                }
            }
            
            result = await server.call_tool("analyze_data_distribution", analysis_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert 'age' in response_data['distribution_analysis']
            assert 'salary' in response_data['distribution_analysis']

    @pytest.mark.asyncio
    async def test_apply_privacy_constraints_success(self, server):
        """Test successful privacy constraint application."""
        privacy_request = {
            "data_source": "users_data.csv",
            "privacy_level": "high",
            "constraints": {
                "differential_privacy": {"epsilon": 1.0},
                "k_anonymity": {"k": 5},
                "l_diversity": {"l": 3}
            },
            "sensitive_columns": ["name", "email", "ssn"]
        }
        
        with patch.object(server.privacy_engine, 'apply_constraints') as mock_apply:
            mock_apply.return_value = {
                'applied_constraints': ['differential_privacy', 'k_anonymity'],
                'privacy_budget_used': 0.3,
                'records_modified': 95,
                'privacy_score': 0.85
            }
            
            result = await server.call_tool("apply_privacy_constraints", privacy_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['privacy_result']['privacy_score'] == 0.85

    @pytest.mark.asyncio
    async def test_compare_datasets_success(self, server):
        """Test successful dataset comparison."""
        comparison_request = {
            "dataset1_path": "original_data.csv",
            "dataset2_path": "synthetic_data.csv",
            "comparison_metrics": ["statistical_similarity", "correlation_preservation", "privacy_metrics"],
            "columns_to_compare": ["age", "salary", "department"]
        }
        
        with patch.object(server.generator, 'compare_datasets') as mock_compare:
            mock_compare.return_value = {
                'statistical_similarity': 0.92,
                'correlation_preservation': 0.88,
                'privacy_metrics': {
                    'privacy_loss': 0.15,
                    'utility_preservation': 0.87
                },
                'column_similarities': {
                    'age': 0.94,
                    'salary': 0.89,
                    'department': 0.91
                },
                'overall_similarity_score': 0.90
            }
            
            result = await server.call_tool("compare_datasets", comparison_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['comparison_result']['overall_similarity_score'] == 0.90

    @pytest.mark.asyncio
    async def test_export_data_success(self, server):
        """Test successful data export."""
        export_request = {
            "data_source": "generated_users",
            "export_format": "csv",
            "destination_path": "/tmp/exported_data.csv",
            "include_metadata": True,
            "compression": "gzip"
        }
        
        with patch.object(server.generator, 'export_data') as mock_export:
            mock_export.return_value = {
                'export_path': '/tmp/exported_data.csv.gz',
                'records_exported': 1000,
                'file_size_mb': 2.5,
                'export_timestamp': datetime.now().isoformat()
            }
            
            result = await server.call_tool("export_data", export_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['export_result']['records_exported'] == 1000

    @pytest.mark.asyncio
    async def test_import_schema_success(self, server):
        """Test successful schema import."""
        import_request = {
            "schema_source": "/path/to/schema.json",
            "schema_format": "json",
            "validation_level": "strict",
            "overwrite_existing": False
        }
        
        with patch.object(server.generator, 'import_schema') as mock_import:
            mock_import.return_value = {
                'schema_name': 'imported_users_schema',
                'columns_imported': 8,
                'validation_passed': True,
                'import_timestamp': datetime.now().isoformat()
            }
            
            result = await server.call_tool("import_schema", import_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['import_result']['columns_imported'] == 8

    @pytest.mark.asyncio
    async def test_get_generation_history_success(self, server):
        """Test successful generation history retrieval."""
        history_request = {
            "limit": 50,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "schema_filter": "users",
            "include_metadata": True
        }
        
        with patch.object(server.generator, 'get_generation_history') as mock_history:
            mock_history.return_value = {
                'total_generations': 25,
                'generations': [
                    {
                        'id': 'gen_001',
                        'schema_name': 'users',
                        'records_generated': 1000,
                        'timestamp': '2023-06-15T10:30:00Z',
                        'privacy_level': 'medium',
                        'success': True
                    },
                    {
                        'id': 'gen_002',
                        'schema_name': 'users',
                        'records_generated': 500,
                        'timestamp': '2023-06-20T14:15:00Z',
                        'privacy_level': 'high',
                        'success': True
                    }
                ]
            }
            
            result = await server.call_tool("get_generation_history", history_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['history']['total_generations'] == 25

    @pytest.mark.asyncio
    async def test_optimize_generation_parameters_success(self, server):
        """Test successful parameter optimization."""
        optimization_request = {
            "schema_name": "users",
            "target_metrics": ["accuracy", "privacy", "speed"],
            "constraints": {
                "max_generation_time": 300,
                "min_privacy_score": 0.8,
                "min_accuracy_score": 0.85
            },
            "optimization_algorithm": "bayesian"
        }
        
        with patch.object(server.generator, 'optimize_parameters') as mock_optimize:
            mock_optimize.return_value = {
                'optimized_parameters': {
                    'noise_level': 0.1,
                    'sampling_rate': 0.3,
                    'batch_size': 1000,
                    'privacy_budget': 2.0
                },
                'expected_performance': {
                    'accuracy_score': 0.87,
                    'privacy_score': 0.82,
                    'generation_speed': 0.95
                },
                'optimization_iterations': 45,
                'convergence_achieved': True
            }
            
            result = await server.call_tool("optimize_generation_parameters", optimization_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['optimization_result']['convergence_achieved'] is True

    @pytest.mark.asyncio
    async def test_batch_generate_data_success(self, server):
        """Test successful batch data generation."""
        batch_request = {
            "batch_configurations": [
                {"schema_name": "users", "num_records": 1000, "privacy_level": "low"},
                {"schema_name": "orders", "num_records": 5000, "privacy_level": "medium"},
                {"schema_name": "products", "num_records": 500, "privacy_level": "high"}
            ],
            "parallel_processing": True,
            "output_format": "parquet",
            "destination_directory": "/tmp/batch_output"
        }
        
        with patch.object(server.generator, 'batch_generate') as mock_batch:
            mock_batch.return_value = {
                'total_batches': 3,
                'successful_batches': 3,
                'failed_batches': 0,
                'total_records_generated': 6500,
                'batch_results': [
                    {'schema': 'users', 'records': 1000, 'status': 'success'},
                    {'schema': 'orders', 'records': 5000, 'status': 'success'},
                    {'schema': 'products', 'records': 500, 'status': 'success'}
                ],
                'total_generation_time': 45.2
            }
            
            result = await server.call_tool("batch_generate_data", batch_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['batch_result']['total_records_generated'] == 6500

    @pytest.mark.asyncio
    async def test_validate_privacy_compliance_success(self, server):
        """Test successful privacy compliance validation."""
        compliance_request = {
            "data_source": "synthetic_users.csv",
            "compliance_standards": ["GDPR", "HIPAA", "CCPA"],
            "validation_level": "comprehensive",
            "generate_report": True
        }
        
        with patch.object(server.privacy_engine, 'validate_compliance') as mock_validate:
            mock_validate.return_value = {
                'overall_compliance_score': 0.92,
                'compliance_by_standard': {
                    'GDPR': {'score': 0.95, 'status': 'compliant', 'issues': []},
                    'HIPAA': {'score': 0.88, 'status': 'compliant', 'issues': ['Minor anonymization concern']},
                    'CCPA': {'score': 0.93, 'status': 'compliant', 'issues': []}
                },
                'recommendations': [
                    'Increase anonymization for HIPAA compliance',
                    'Consider additional privacy measures for sensitive fields'
                ],
                'risk_assessment': 'Low'
            }
            
            result = await server.call_tool("validate_privacy_compliance", compliance_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['compliance_result']['overall_compliance_score'] == 0.92

    @pytest.mark.asyncio
    async def test_analyze_data_quality_success(self, server):
        """Test successful data quality analysis."""
        quality_request = {
            "data_source": "generated_dataset.csv",
            "quality_metrics": ["completeness", "consistency", "accuracy", "uniqueness"],
            "reference_dataset": "original_dataset.csv",
            "detailed_analysis": True
        }
        
        with patch.object(server.generator, 'analyze_data_quality') as mock_analyze:
            mock_analyze.return_value = {
                'overall_quality_score': 0.89,
                'quality_metrics': {
                    'completeness': 0.98,
                    'consistency': 0.85,
                    'accuracy': 0.87,
                    'uniqueness': 0.86
                },
                'column_quality_scores': {
                    'name': 0.92,
                    'email': 0.88,
                    'age': 0.94,
                    'salary': 0.81
                },
                'quality_issues': [
                    'Some inconsistent formatting in email field',
                    'Minor accuracy issues in salary distribution'
                ],
                'improvement_suggestions': [
                    'Implement stricter email validation',
                    'Refine salary generation algorithm'
                ]
            }
            
            result = await server.call_tool("analyze_data_quality", quality_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['quality_result']['overall_quality_score'] == 0.89

    @pytest.mark.asyncio
    async def test_generate_data_report_success(self, server):
        """Test successful data report generation."""
        report_request = {
            "data_source": "synthetic_users.csv",
            "report_type": "comprehensive",
            "include_visualizations": True,
            "output_format": "html",
            "sections": ["summary", "distribution", "quality", "privacy"]
        }
        
        with patch.object(server.generator, 'generate_report') as mock_report:
            mock_report.return_value = {
                'report_path': '/tmp/data_report.html',
                'report_sections': ['summary', 'distribution', 'quality', 'privacy'],
                'generation_timestamp': datetime.now().isoformat(),
                'file_size_kb': 2048,
                'visualization_count': 12
            }
            
            result = await server.call_tool("generate_data_report", report_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['report_result']['visualization_count'] == 12

    @pytest.mark.asyncio
    async def test_manage_data_lineage_success(self, server):
        """Test successful data lineage management."""
        lineage_request = {
            "operation": "track",
            "source_data": "original_users.csv",
            "generated_data": "synthetic_users.csv",
            "transformation_steps": ["schema_validation", "privacy_application", "data_generation"],
            "metadata": {
                "privacy_level": "medium",
                "generation_algorithm": "GANs"
            }
        }
        
        with patch.object(server.generator, 'manage_lineage') as mock_lineage:
            mock_lineage.return_value = {
                'lineage_id': 'lineage_001',
                'tracking_status': 'active',
                'lineage_graph': {
                    'nodes': 5,
                    'edges': 8,
                    'depth': 3
                },
                'creation_timestamp': datetime.now().isoformat()
            }
            
            result = await server.call_tool("manage_data_lineage", lineage_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['lineage_result']['lineage_id'] == 'lineage_001'

    @pytest.mark.asyncio
    async def test_configure_database_connection_success(self, server):
        """Test successful database connection configuration."""
        config_request = {
            "database_type": "postgresql",
            "connection_params": {
                "host": "localhost",
                "port": 5432,
                "database": "synthetic_data",
                "username": "user",
                "password": "password"
            },
            "connection_pool_size": 10,
            "timeout": 30
        }
        
        with patch.object(server.database_manager, 'configure_connection') as mock_config:
            mock_config.return_value = {
                'configuration_id': 'conn_001',
                'status': 'configured',
                'connection_test': 'passed',
                'pool_initialized': True
            }
            
            result = await server.call_tool("configure_database_connection", config_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['configuration_result']['connection_test'] == 'passed'

    @pytest.mark.asyncio
    async def test_test_database_connection_success(self, server):
        """Test successful database connection testing."""
        test_request = {
            "connection_id": "conn_001",
            "test_query": "SELECT 1",
            "timeout": 10
        }
        
        with patch.object(server.database_manager, 'test_connection') as mock_test:
            mock_test.return_value = {
                'connection_status': 'active',
                'response_time_ms': 45,
                'test_query_result': 'success',
                'connection_pool_status': 'healthy'
            }
            
            result = await server.call_tool("test_database_connection", test_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['connection_test']['connection_status'] == 'active'

    @pytest.mark.asyncio
    async def test_list_available_schemas_success(self, server):
        """Test successful schema listing."""
        list_request = {
            "database_connection": "conn_001",
            "include_metadata": True,
            "filter_pattern": "user*"
        }
        
        with patch.object(server.database_manager, 'list_schemas') as mock_list:
            mock_list.return_value = {
                'schemas': [
                    {
                        'name': 'users',
                        'columns': 8,
                        'created_date': '2023-01-15',
                        'last_modified': '2023-06-10'
                    },
                    {
                        'name': 'user_profiles',
                        'columns': 12,
                        'created_date': '2023-02-20',
                        'last_modified': '2023-06-15'
                    }
                ],
                'total_schemas': 2
            }
            
            result = await server.call_tool("list_available_schemas", list_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['schemas_result']['total_schemas'] == 2

    @pytest.mark.asyncio
    async def test_create_custom_schema_success(self, server):
        """Test successful custom schema creation."""
        schema_request = {
            "schema_name": "custom_users",
            "schema_definition": {
                "columns": [
                    {"name": "id", "type": "integer", "constraints": ["primary_key", "auto_increment"]},
                    {"name": "username", "type": "varchar", "max_length": 50, "constraints": ["unique", "not_null"]},
                    {"name": "email", "type": "varchar", "max_length": 255, "constraints": ["unique"]},
                    {"name": "created_at", "type": "timestamp", "default": "CURRENT_TIMESTAMP"}
                ]
            },
            "validation": True,
            "save_to_database": True
        }
        
        with patch.object(server.generator, 'create_schema') as mock_create:
            mock_create.return_value = {
                'schema_id': 'schema_001',
                'validation_passed': True,
                'schema_saved': True,
                'columns_created': 4,
                'creation_timestamp': datetime.now().isoformat()
            }
            
            result = await server.call_tool("create_custom_schema", schema_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['schema_result']['validation_passed'] is True

    @pytest.mark.asyncio
    async def test_delete_schema_success(self, server):
        """Test successful schema deletion."""
        delete_request = {
            "schema_name": "old_schema",
            "confirm_deletion": True,
            "backup_before_delete": True
        }
        
        with patch.object(server.generator, 'delete_schema') as mock_delete:
            mock_delete.return_value = {
                'deletion_status': 'success',
                'backup_created': True,
                'backup_path': '/backups/old_schema_backup.json',
                'deletion_timestamp': datetime.now().isoformat()
            }
            
            result = await server.call_tool("delete_schema", delete_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['deletion_result']['deletion_status'] == 'success'

    # Error handling tests
    @pytest.mark.asyncio
    async def test_invalid_tool_name(self, server):
        """Test calling invalid tool name."""
        with pytest.raises(Exception):
            await server.call_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, server):
        """Test calling tool with missing required parameters."""
        result = await server.call_tool("generate_synthetic_data", {})
        
        response_data = json.loads(result.content[0].text)
        assert response_data['success'] is False
        assert 'error' in response_data

    @pytest.mark.asyncio
    async def test_invalid_parameter_types(self, server):
        """Test calling tool with invalid parameter types."""
        invalid_request = {
            "schema_name": 123,  # Should be string
            "num_records": "invalid",  # Should be integer
        }
        
        result = await server.call_tool("generate_synthetic_data", invalid_request)
        
        response_data = json.loads(result.content[0].text)
        assert response_data['success'] is False
        assert 'error' in response_data

    @pytest.mark.asyncio
    async def test_database_connection_error(self, server):
        """Test handling database connection errors."""
        config_request = {
            "database_type": "postgresql",
            "connection_params": {
                "host": "invalid-host",
                "port": 5432,
                "database": "test_db",
                "username": "user",
                "password": "password"
            }
        }
        
        with patch.object(server.database_manager, 'configure_connection') as mock_config:
            mock_config.side_effect = Exception("Connection failed")
            
            result = await server.call_tool("configure_database_connection", config_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is False
            assert 'error' in response_data

    @pytest.mark.asyncio
    async def test_privacy_constraint_violation(self, server):
        """Test handling privacy constraint violations."""
        privacy_request = {
            "data_source": "users_data.csv",
            "privacy_level": "impossible_level",  # Invalid privacy level
            "constraints": {
                "differential_privacy": {"epsilon": -1.0}  # Invalid epsilon
            }
        }
        
        with patch.object(server.privacy_engine, 'apply_constraints') as mock_apply:
            mock_apply.side_effect = ValueError("Invalid privacy parameters")
            
            result = await server.call_tool("apply_privacy_constraints", privacy_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is False
            assert 'error' in response_data

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, server):
        """Test handling file not found errors."""
        import_request = {
            "schema_source": "/nonexistent/path/schema.json",
            "schema_format": "json"
        }
        
        with patch.object(server.generator, 'import_schema') as mock_import:
            mock_import.side_effect = FileNotFoundError("Schema file not found")
            
            result = await server.call_tool("import_schema", import_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is False
            assert 'error' in response_data

    # Performance tests
    @pytest.mark.asyncio
    async def test_large_data_generation(self, server):
        """Test generation of large datasets."""
        large_request = {
            "schema_name": "users",
            "num_records": 1000000,  # Large dataset
            "format": "parquet"
        }
        
        with patch.object(server.generator, 'generate_data') as mock_generate:
            # Simulate successful large data generation
            mock_data = pd.DataFrame({
                'id': range(1000000),
                'name': ['User' + str(i) for i in range(1000000)]
            })
            mock_generate.return_value = mock_data
            
            result = await server.call_tool("generate_synthetic_data", large_request)
            
            response_data = json.loads(result.content[0].text)
            assert response_data['success'] is True
            assert response_data['records_generated'] == 1000000

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, server):
        """Test handling concurrent operations."""
        # Create multiple concurrent requests
        requests = [
            {"schema_name": f"users_{i}", "num_records": 100}
            for i in range(5)
        ]
        
        with patch.object(server.generator, 'generate_data') as mock_generate:
            mock_data = pd.DataFrame({'id': [1, 2, 3], 'name': ['A', 'B', 'C']})
            mock_generate.return_value = mock_data
            
            # Execute requests concurrently
            tasks = [
                server.call_tool("generate_synthetic_data", request)
                for request in requests
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All requests should succeed
            for result in results:
                assert not isinstance(result, Exception)
                response_data = json.loads(result.content[0].text)
                assert response_data['success'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=synthetic_data_mcp.server"])