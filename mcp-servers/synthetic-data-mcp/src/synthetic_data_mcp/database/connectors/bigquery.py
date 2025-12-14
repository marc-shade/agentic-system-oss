"""
Google BigQuery connector for cloud data warehouse operations.

Supports:
- Google Cloud BigQuery API
- Streaming inserts and batch loads
- BigQuery ML integration
- Partitioned and clustered tables
- Schema evolution
- Cost optimization
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date, timedelta
from loguru import logger

try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    from google.api_core import exceptions as gcp_exceptions
    import pandas as pd
except ImportError:
    bigquery = None
    service_account = None
    gcp_exceptions = None
    pd = None
    logger.warning("Google Cloud BigQuery dependencies not installed - BigQuery connector disabled")

from ..base import CloudDatabaseConnector


class BigQueryConnector(CloudDatabaseConnector):
    """Google BigQuery connector with advanced analytics capabilities."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize BigQuery connector.
        
        Args:
            connection_config: BigQuery connection parameters
                - project_id: Google Cloud project ID
                - credentials_path: Path to service account JSON file (optional)
                - credentials_json: Service account JSON content (optional)
                - dataset_id: Default dataset ID
                - location: Data location (default: US)
                - timeout: Query timeout in seconds (default: 300)
                - max_results: Maximum results per query (default: 10000)
                - dry_run: Enable dry run mode (default: False)
        """
        if bigquery is None:
            raise ImportError("Google Cloud BigQuery dependencies required. Install with: pip install google-cloud-bigquery pandas")
            
        super().__init__(connection_config)
        
        # Set defaults
        self.config.setdefault('location', 'US')
        self.config.setdefault('timeout', 300)
        self.config.setdefault('max_results', 10000)
        self.config.setdefault('dry_run', False)
        
        self.client = None
        self.dataset_ref = None
    
    def _setup_authentication(self):
        """Setup Google Cloud authentication."""
        if self.config.get('credentials_path'):
            self.credentials = service_account.Credentials.from_service_account_file(
                self.config['credentials_path']
            )
        elif self.config.get('credentials_json'):
            self.credentials = service_account.Credentials.from_service_account_info(
                self.config['credentials_json']
            )
        else:
            # Use default credentials (ADC)
            self.credentials = None
    
    async def connect(self) -> bool:
        """Establish BigQuery connection."""
        try:
            # Create BigQuery client
            if self.credentials:
                self.client = bigquery.Client(
                    project=self.config['project_id'],
                    credentials=self.credentials,
                    location=self.config['location']
                )
            else:
                self.client = bigquery.Client(
                    project=self.config['project_id'],
                    location=self.config['location']
                )
            
            # Test connection by listing datasets
            datasets = list(self.client.list_datasets(max_results=1))
            
            # Set default dataset reference
            if self.config.get('dataset_id'):
                self.dataset_ref = self.client.dataset(self.config['dataset_id'])
            
            logger.info(f"Connected to BigQuery project: {self.config['project_id']}")
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to BigQuery: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close BigQuery connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.dataset_ref = None
        self._connected = False
        logger.info("Disconnected from BigQuery")
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute BigQuery SQL query."""
        if not self.client:
            raise RuntimeError("Not connected to BigQuery")
        
        try:
            # Configure query job
            job_config = bigquery.QueryJobConfig()
            job_config.dry_run = self.config['dry_run']
            job_config.use_query_cache = True
            
            # Add query parameters if provided
            if parameters:
                query_parameters = []
                for param_name, param_value in parameters.items():
                    if isinstance(param_value, str):
                        param_type = 'STRING'
                    elif isinstance(param_value, int):
                        param_type = 'INT64'
                    elif isinstance(param_value, float):
                        param_type = 'FLOAT64'
                    elif isinstance(param_value, bool):
                        param_type = 'BOOL'
                    elif isinstance(param_value, datetime):
                        param_type = 'DATETIME'
                    elif isinstance(param_value, date):
                        param_type = 'DATE'
                    else:
                        param_type = 'STRING'
                        param_value = str(param_value)
                    
                    query_parameters.append(
                        bigquery.ScalarQueryParameter(param_name, param_type, param_value)
                    )
                
                job_config.query_parameters = query_parameters
            
            # Execute query
            query_job = self.client.query(query, job_config=job_config)
            
            if self.config['dry_run']:
                return [{
                    'dry_run': True,
                    'bytes_processed': query_job.total_bytes_processed,
                    'estimated_cost': query_job.total_bytes_processed * 5e-6  # $5 per TB
                }]
            
            # Wait for results
            results = query_job.result(timeout=self.config['timeout'])
            
            # Convert to list of dictionaries
            rows = []
            for row in results:
                row_dict = {}
                for field, value in zip(results.schema, row):
                    # Convert BigQuery types to Python types
                    if isinstance(value, datetime):
                        row_dict[field.name] = value.isoformat()
                    elif isinstance(value, date):
                        row_dict[field.name] = value.isoformat()
                    else:
                        row_dict[field.name] = value
                rows.append(row_dict)
            
            logger.info(f"BigQuery query executed: {len(rows)} rows returned")
            return rows
            
        except Exception as e:
            logger.error(f"BigQuery query failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute BigQuery DML (INSERT, UPDATE, DELETE)."""
        if not self.client:
            raise RuntimeError("Not connected to BigQuery")
        
        try:
            # Configure DML job
            job_config = bigquery.QueryJobConfig()
            job_config.dry_run = self.config['dry_run']
            
            if parameters:
                # Add parameters (same as execute_query)
                query_parameters = []
                for param_name, param_value in parameters.items():
                    if isinstance(param_value, str):
                        param_type = 'STRING'
                    elif isinstance(param_value, int):
                        param_type = 'INT64'
                    elif isinstance(param_value, float):
                        param_type = 'FLOAT64'
                    elif isinstance(param_value, bool):
                        param_type = 'BOOL'
                    elif isinstance(param_value, datetime):
                        param_type = 'DATETIME'
                    else:
                        param_type = 'STRING'
                        param_value = str(param_value)
                    
                    query_parameters.append(
                        bigquery.ScalarQueryParameter(param_name, param_type, param_value)
                    )
                
                job_config.query_parameters = query_parameters
            
            # Execute DML query
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Return number of affected rows
            return query_job.num_dml_affected_rows or 0
            
        except Exception as e:
            logger.error(f"BigQuery write operation failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    async def create_dataset(self, dataset_name: str, location: Optional[str] = None) -> bool:
        """Create BigQuery dataset."""
        try:
            dataset_id = f"{self.config['project_id']}.{dataset_name}"
            dataset = bigquery.Dataset(dataset_id)
            
            # Set location
            dataset.location = location or self.config['location']
            
            # Set default table expiration (30 days)
            dataset.default_table_expiration_ms = 30 * 24 * 60 * 60 * 1000
            
            # Create dataset
            dataset = self.client.create_dataset(dataset, exists_ok=True)
            
            logger.info(f"Created BigQuery dataset: {dataset_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create dataset {dataset_name}: {e}")
            return False
    
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> bool:
        """Create BigQuery table with schema."""
        try:
            if not self.dataset_ref:
                raise ValueError("No default dataset configured")
            
            table_ref = self.dataset_ref.table(table_name)
            
            # Build BigQuery schema
            bq_schema = []
            for field_name, field_config in schema.items():
                if field_name == '_metadata':
                    continue
                
                # Map field types to BigQuery types
                field_type = self._map_to_bigquery_type(field_config.get('type', 'STRING'))
                mode = 'NULLABLE' if field_config.get('nullable', True) else 'REQUIRED'
                
                bq_field = bigquery.SchemaField(
                    name=field_name,
                    field_type=field_type,
                    mode=mode,
                    description=field_config.get('description', '')
                )
                bq_schema.append(bq_field)
            
            # Add default timestamp fields
            bq_schema.extend([
                bigquery.SchemaField('created_at', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('updated_at', 'TIMESTAMP', mode='REQUIRED')
            ])
            
            # Create table
            table = bigquery.Table(table_ref, schema=bq_schema)
            
            # Set partitioning if specified
            metadata = schema.get('_metadata', {})
            if metadata.get('partition_field'):
                if metadata['partition_field'] in ['created_at', 'updated_at']:
                    table.time_partitioning = bigquery.TimePartitioning(
                        type_=bigquery.TimePartitioningType.DAY,
                        field=metadata['partition_field']
                    )
            
            # Set clustering if specified
            if metadata.get('cluster_fields'):
                table.clustering_fields = metadata['cluster_fields']
            
            table = self.client.create_table(table)
            
            logger.info(f"Created BigQuery table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def _map_to_bigquery_type(self, python_type: str) -> str:
        """Map Python types to BigQuery types."""
        type_mapping = {
            'str': 'STRING',
            'int': 'INT64',
            'float': 'FLOAT64',
            'bool': 'BOOL',
            'datetime': 'TIMESTAMP',
            'date': 'DATE',
            'time': 'TIME',
            'dict': 'JSON',
            'list': 'ARRAY',
            'bytes': 'BYTES',
            'decimal': 'NUMERIC',
            'geography': 'GEOGRAPHY'
        }
        
        return type_mapping.get(python_type.lower(), 'STRING')
    
    async def insert_bulk(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Efficient bulk insert using BigQuery streaming API."""
        if not data:
            return 0
        
        try:
            if not self.dataset_ref:
                raise ValueError("No default dataset configured")
            
            table_ref = self.dataset_ref.table(table_name)
            table = self.client.get_table(table_ref)
            
            # Add timestamps
            for record in data:
                record.setdefault('created_at', datetime.utcnow())
                record.setdefault('updated_at', datetime.utcnow())
            
            # Insert data using streaming API
            errors = self.client.insert_rows_json(table, data)
            
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
                return len(data) - len(errors)
            
            logger.info(f"Bulk inserted {len(data)} records into {table_name}")
            return len(data)
            
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def upload_data(self, table_name: str, data: List[Dict[str, Any]], dataset_name: Optional[str] = None) -> int:
        """Upload data using load job (more cost-effective for large datasets)."""
        try:
            dataset_ref = self.client.dataset(dataset_name) if dataset_name else self.dataset_ref
            if not dataset_ref:
                raise ValueError("No dataset specified")
            
            table_ref = dataset_ref.table(table_name)
            
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(data)
            
            # Add timestamps
            df['created_at'] = datetime.utcnow()
            df['updated_at'] = datetime.utcnow()
            
            # Configure load job
            job_config = bigquery.LoadJobConfig()
            job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
            job_config.autodetect = True  # Auto-detect schema
            job_config.source_format = bigquery.SourceFormat.PARQUET
            
            # Load data
            load_job = self.client.load_table_from_dataframe(
                df, table_ref, job_config=job_config
            )
            
            load_job.result()  # Wait for completion
            
            logger.info(f"Uploaded {len(data)} records to {table_name}")
            return len(data)
            
        except Exception as e:
            logger.error(f"Data upload failed for {table_name}: {e}")
            raise
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get BigQuery table schema and metadata."""
        try:
            if not self.dataset_ref:
                raise ValueError("No default dataset configured")
            
            table_ref = self.dataset_ref.table(table_name)
            table = self.client.get_table(table_ref)
            
            # Extract schema information
            schema_fields = {}
            for field in table.schema:
                schema_fields[field.name] = {
                    'type': field.field_type,
                    'mode': field.mode,
                    'description': field.description,
                    'fields': [subfield.name for subfield in (field.fields or [])]
                }
            
            return {
                'table_name': table_name,
                'full_table_id': str(table.table_id),
                'schema': schema_fields,
                'num_rows': table.num_rows,
                'num_bytes': table.num_bytes,
                'created': table.created.isoformat() if table.created else None,
                'modified': table.modified.isoformat() if table.modified else None,
                'location': table.location,
                'partitioning': {
                    'type': table.time_partitioning.type_ if table.time_partitioning else None,
                    'field': table.time_partitioning.field if table.time_partitioning else None
                } if table.time_partitioning else None,
                'clustering_fields': table.clustering_fields,
                'labels': dict(table.labels) if table.labels else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return {}
    
    async def list_tables(self) -> List[str]:
        """List all tables in the default dataset."""
        try:
            if not self.dataset_ref:
                raise ValueError("No default dataset configured")
            
            tables = self.client.list_tables(self.dataset_ref)
            return [table.table_id for table in tables]
            
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    async def export_to_cloud_storage(self, table_name: str, destination_uri: str, format: str = 'CSV') -> bool:
        """Export table to Google Cloud Storage."""
        try:
            if not self.dataset_ref:
                raise ValueError("No default dataset configured")
            
            table_ref = self.dataset_ref.table(table_name)
            
            # Configure extract job
            job_config = bigquery.ExtractJobConfig()
            job_config.destination_format = getattr(bigquery.DestinationFormat, format)
            
            if format == 'CSV':
                job_config.print_header = True
            
            # Start extract job
            extract_job = self.client.extract_table(
                table_ref,
                destination_uri,
                job_config=job_config
            )
            
            extract_job.result()  # Wait for completion
            
            logger.info(f"Exported table {table_name} to {destination_uri}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed for {table_name}: {e}")
            return False
    
    async def run_ml_query(self, model_name: str, prediction_query: str) -> List[Dict[str, Any]]:
        """Run BigQuery ML prediction query."""
        try:
            ml_query = f"""
                SELECT *
                FROM ML.PREDICT(MODEL `{self.config['project_id']}.{self.config['dataset_id']}.{model_name}`, (
                    {prediction_query}
                ))
            """
            
            return await self.execute_query(ml_query)
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            raise
    
    async def create_ml_model(self, model_name: str, training_query: str, model_type: str = 'LINEAR_REG') -> bool:
        """Create BigQuery ML model."""
        try:
            create_model_query = f"""
                CREATE OR REPLACE MODEL `{self.config['project_id']}.{self.config['dataset_id']}.{model_name}`
                OPTIONS(model_type='{model_type}') AS (
                    {training_query}
                )
            """
            
            await self.execute_write(create_model_query)
            
            logger.info(f"Created ML model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"ML model creation failed: {e}")
            return False
    
    async def get_query_cost(self, query: str) -> Dict[str, Any]:
        """Get estimated query cost using dry run."""
        try:
            job_config = bigquery.QueryJobConfig(dry_run=True)
            query_job = self.client.query(query, job_config=job_config)
            
            bytes_processed = query_job.total_bytes_processed
            cost_per_tb = 5.0  # $5 per TB
            estimated_cost = (bytes_processed / (1024**4)) * cost_per_tb
            
            return {
                'bytes_processed': bytes_processed,
                'estimated_cost_usd': estimated_cost,
                'query_valid': True
            }
            
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return {
                'bytes_processed': 0,
                'estimated_cost_usd': 0,
                'query_valid': False,
                'error': str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            start_time = datetime.now()
            
            # Test basic connectivity
            datasets = list(self.client.list_datasets(max_results=1))
            
            # Performance test
            query_start = datetime.now()
            test_query = "SELECT 1 as test_value"
            await self.execute_query(test_query)
            query_time = (datetime.now() - query_start).total_seconds()
            
            # Get project info
            project = self.client.get_project(self.config['project_id'])
            
            # Count tables in default dataset
            table_count = 0
            if self.dataset_ref:
                tables = list(self.client.list_tables(self.dataset_ref, max_results=1000))
                table_count = len(tables)
            
            health_check_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'project_id': self.config['project_id'],
                'project_name': project.friendly_name,
                'location': self.config['location'],
                'dataset_count': len(datasets),
                'table_count': table_count,
                'query_response_time_ms': query_time * 1000,
                'health_check_time_ms': health_check_time * 1000,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }