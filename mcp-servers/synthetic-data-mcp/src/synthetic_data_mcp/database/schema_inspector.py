"""
Database schema inspector for automated schema discovery and analysis.

Provides:
- Cross-database schema analysis
- Relationship discovery
- Data type inference
- Performance analysis
- Schema validation
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from loguru import logger
from collections import defaultdict

from .manager import DatabaseManager, DatabaseType
from .base import DatabaseConnector


@dataclass
class ColumnInfo:
    """Column information."""
    name: str
    data_type: str
    nullable: bool
    primary_key: bool
    foreign_key: Optional[str]
    default_value: Optional[Any]
    max_length: Optional[int]
    precision: Optional[int]
    scale: Optional[int]
    is_indexed: bool
    unique: bool
    check_constraints: List[str]
    sample_values: List[Any]
    null_percentage: float
    cardinality: int


@dataclass
class TableInfo:
    """Table information."""
    name: str
    schema_name: str
    database_name: str
    columns: List[ColumnInfo]
    row_count: int
    size_bytes: int
    indexes: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, Any]]
    referenced_by: List[str]
    created_at: Optional[str]
    modified_at: Optional[str]
    table_type: str  # TABLE, VIEW, MATERIALIZED_VIEW


@dataclass
class RelationshipInfo:
    """Table relationship information."""
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    relationship_type: str  # one_to_one, one_to_many, many_to_many
    constraint_name: str


@dataclass
class SchemaAnalysis:
    """Complete schema analysis."""
    database_name: str
    database_type: DatabaseType
    tables: List[TableInfo]
    relationships: List[RelationshipInfo]
    orphaned_tables: List[str]
    duplicate_indexes: List[Dict[str, Any]]
    performance_issues: List[Dict[str, Any]]
    data_quality_issues: List[Dict[str, Any]]
    analysis_timestamp: str


class SchemaInspector:
    """Database schema inspector and analyzer."""
    
    def __init__(self, database_manager: DatabaseManager):
        """Initialize schema inspector."""
        self.db_manager = database_manager
        self.analysis_cache: Dict[str, SchemaAnalysis] = {}
        self.cache_ttl_hours = 24  # Cache analysis for 24 hours
    
    async def analyze_database_schema(
        self,
        database: str,
        deep_analysis: bool = True,
        sample_size: int = 1000
    ) -> SchemaAnalysis:
        """
        Perform comprehensive schema analysis.
        
        Args:
            database: Database connection name
            deep_analysis: Whether to perform deep analysis (slower but more comprehensive)
            sample_size: Number of sample records to analyze per table
            
        Returns:
            Complete schema analysis
        """
        
        # Check cache
        cache_key = f"{database}_{deep_analysis}_{sample_size}"
        if cache_key in self.analysis_cache:
            cached_analysis = self.analysis_cache[cache_key]
            cached_time = datetime.fromisoformat(cached_analysis.analysis_timestamp)
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl_hours * 3600:
                logger.info(f"Returning cached schema analysis for {database}")
                return cached_analysis
        
        logger.info(f"Starting schema analysis for database: {database}")
        start_time = datetime.now()
        
        try:
            # Get database type
            db_config = self.db_manager.configurations.get(database)
            if not db_config:
                raise ValueError(f"Database {database} not found")
            
            db_type = db_config['type']
            
            # Get basic database info
            tables_result = await self.db_manager.list_tables(database=database)
            if not tables_result['success']:
                raise Exception(f"Failed to list tables: {tables_result.get('error')}")
            
            table_names = tables_result['tables']
            
            # Analyze each table
            tables = []
            for table_name in table_names:
                try:
                    table_info = await self._analyze_table(database, table_name, deep_analysis, sample_size)
                    tables.append(table_info)
                except Exception as e:
                    logger.warning(f"Failed to analyze table {table_name}: {e}")
                    continue
            
            # Discover relationships
            relationships = await self._discover_relationships(database, tables, db_type)
            
            # Find orphaned tables
            orphaned_tables = self._find_orphaned_tables(tables, relationships)
            
            # Performance analysis
            performance_issues = []
            if deep_analysis:
                performance_issues = await self._analyze_performance_issues(database, tables)
            
            # Find duplicate indexes
            duplicate_indexes = self._find_duplicate_indexes(tables)
            
            # Data quality analysis
            data_quality_issues = []
            if deep_analysis:
                data_quality_issues = await self._analyze_data_quality(database, tables)
            
            analysis = SchemaAnalysis(
                database_name=database,
                database_type=db_type,
                tables=tables,
                relationships=relationships,
                orphaned_tables=orphaned_tables,
                duplicate_indexes=duplicate_indexes,
                performance_issues=performance_issues,
                data_quality_issues=data_quality_issues,
                analysis_timestamp=datetime.now().isoformat()
            )
            
            # Cache the result
            self.analysis_cache[cache_key] = analysis
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Schema analysis completed in {analysis_time:.2f} seconds")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Schema analysis failed: {e}")
            raise
    
    async def _analyze_table(
        self,
        database: str,
        table_name: str,
        deep_analysis: bool,
        sample_size: int
    ) -> TableInfo:
        """Analyze a specific table."""
        
        # Get basic table schema
        schema_result = await self.db_manager.get_table_schema(table_name, database=database)
        if not schema_result['success']:
            raise Exception(f"Failed to get schema for {table_name}")
        
        table_schema = schema_result['schema']
        
        # Get row count
        count_result = await self.db_manager.execute_query(
            f"SELECT COUNT(*) as row_count FROM {table_name}",
            database=database
        )
        
        row_count = 0
        if count_result['success'] and count_result['results']:
            row_count = count_result['results'][0].get('row_count', 0)
        
        # Analyze columns
        columns = []
        for col_name, col_info in table_schema.get('columns', {}).items():
            column_analysis = await self._analyze_column(
                database, table_name, col_name, col_info, deep_analysis, sample_size
            )
            columns.append(column_analysis)
        
        # Extract table metadata
        table_info = TableInfo(
            name=table_name,
            schema_name=table_schema.get('schema_name', 'public'),
            database_name=database,
            columns=columns,
            row_count=row_count,
            size_bytes=table_schema.get('size_bytes', 0),
            indexes=table_schema.get('indexes', []),
            foreign_keys=table_schema.get('foreign_keys', []),
            referenced_by=[],
            created_at=table_schema.get('created_at'),
            modified_at=table_schema.get('modified_at'),
            table_type=table_schema.get('table_type', 'TABLE')
        )
        
        return table_info
    
    async def _analyze_column(
        self,
        database: str,
        table_name: str,
        column_name: str,
        column_info: Dict[str, Any],
        deep_analysis: bool,
        sample_size: int
    ) -> ColumnInfo:
        """Analyze a specific column."""
        
        sample_values = []
        null_percentage = 0.0
        cardinality = 0
        
        if deep_analysis:
            # Get sample values and statistics
            try:
                sample_query = f"""
                    SELECT 
                        {column_name},
                        COUNT(*) as frequency
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                    GROUP BY {column_name}
                    ORDER BY frequency DESC
                    LIMIT {min(sample_size, 100)}
                """
                
                sample_result = await self.db_manager.execute_query(sample_query, database=database)
                if sample_result['success']:
                    sample_values = [
                        row[column_name] for row in sample_result['results']
                        if row[column_name] is not None
                    ]
                
                # Get null percentage and cardinality
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total_rows,
                        COUNT({column_name}) as non_null_rows,
                        COUNT(DISTINCT {column_name}) as distinct_values
                    FROM {table_name}
                """
                
                stats_result = await self.db_manager.execute_query(stats_query, database=database)
                if stats_result['success'] and stats_result['results']:
                    stats = stats_result['results'][0]
                    total_rows = stats.get('total_rows', 0)
                    non_null_rows = stats.get('non_null_rows', 0)
                    distinct_values = stats.get('distinct_values', 0)
                    
                    if total_rows > 0:
                        null_percentage = (total_rows - non_null_rows) / total_rows
                    cardinality = distinct_values
                    
            except Exception as e:
                logger.warning(f"Failed to get detailed column stats for {column_name}: {e}")
        
        return ColumnInfo(
            name=column_name,
            data_type=column_info.get('type', 'unknown'),
            nullable=column_info.get('nullable', True),
            primary_key=column_info.get('primary_key', False),
            foreign_key=column_info.get('foreign_key'),
            default_value=column_info.get('default'),
            max_length=column_info.get('max_length'),
            precision=column_info.get('precision'),
            scale=column_info.get('scale'),
            is_indexed=column_info.get('indexed', False),
            unique=column_info.get('unique', False),
            check_constraints=column_info.get('check_constraints', []),
            sample_values=sample_values,
            null_percentage=null_percentage,
            cardinality=cardinality
        )
    
    async def _discover_relationships(
        self,
        database: str,
        tables: List[TableInfo],
        db_type: DatabaseType
    ) -> List[RelationshipInfo]:
        """Discover table relationships."""
        
        relationships = []
        
        # First pass: explicit foreign key relationships
        for table in tables:
            for fk in table.foreign_keys:
                relationship = RelationshipInfo(
                    parent_table=fk.get('referenced_table'),
                    parent_column=fk.get('referenced_column'),
                    child_table=table.name,
                    child_column=fk.get('column'),
                    relationship_type='one_to_many',  # Assume one-to-many by default
                    constraint_name=fk.get('constraint_name', '')
                )
                relationships.append(relationship)
        
        # Second pass: infer relationships from naming patterns
        relationships.extend(await self._infer_implicit_relationships(database, tables))
        
        # Third pass: analyze relationship cardinality
        for relationship in relationships:
            relationship.relationship_type = await self._determine_relationship_cardinality(
                database, relationship
            )
        
        return relationships
    
    async def _infer_implicit_relationships(
        self,
        database: str,
        tables: List[TableInfo]
    ) -> List[RelationshipInfo]:
        """Infer relationships from naming patterns and data analysis."""
        
        relationships = []
        
        # Common foreign key naming patterns
        fk_patterns = [
            lambda col, table: col.endswith('_id') and col[:-3] == table.lower(),
            lambda col, table: col == f"{table.lower()}_id",
            lambda col, table: col.endswith('Id') and col[:-2].lower() == table.lower(),
        ]
        
        table_dict = {table.name.lower(): table for table in tables}
        
        for table in tables:
            for column in table.columns:
                # Skip if already has explicit foreign key
                if column.foreign_key:
                    continue
                
                # Check naming patterns
                for pattern in fk_patterns:
                    for potential_parent_name, potential_parent in table_dict.items():
                        if pattern(column.name.lower(), potential_parent_name):
                            # Verify the relationship by checking if values exist
                            if await self._verify_relationship(
                                database, table.name, column.name,
                                potential_parent.name, 'id'  # Assume 'id' as primary key
                            ):
                                relationship = RelationshipInfo(
                                    parent_table=potential_parent.name,
                                    parent_column='id',
                                    child_table=table.name,
                                    child_column=column.name,
                                    relationship_type='inferred',
                                    constraint_name=f"inferred_{table.name}_{column.name}"
                                )
                                relationships.append(relationship)
                            break
        
        return relationships
    
    async def _verify_relationship(
        self,
        database: str,
        child_table: str,
        child_column: str,
        parent_table: str,
        parent_column: str
    ) -> bool:
        """Verify if an inferred relationship actually exists."""
        
        try:
            # Check if child values exist in parent
            verification_query = f"""
                SELECT COUNT(*) as invalid_references
                FROM {child_table} c
                LEFT JOIN {parent_table} p ON c.{child_column} = p.{parent_column}
                WHERE c.{child_column} IS NOT NULL 
                AND p.{parent_column} IS NULL
            """
            
            result = await self.db_manager.execute_query(verification_query, database=database)
            if result['success'] and result['results']:
                invalid_references = result['results'][0].get('invalid_references', 0)
                return invalid_references == 0  # Valid if no invalid references
            
        except Exception as e:
            logger.warning(f"Failed to verify relationship: {e}")
        
        return False
    
    async def _determine_relationship_cardinality(
        self,
        database: str,
        relationship: RelationshipInfo
    ) -> str:
        """Determine the cardinality of a relationship."""
        
        try:
            # Check uniqueness of foreign key in child table
            uniqueness_query = f"""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT {relationship.child_column}) as distinct_values
                FROM {relationship.child_table}
                WHERE {relationship.child_column} IS NOT NULL
            """
            
            result = await self.db_manager.execute_query(uniqueness_query, database=database)
            if result['success'] and result['results']:
                stats = result['results'][0]
                total_rows = stats.get('total_rows', 0)
                distinct_values = stats.get('distinct_values', 0)
                
                if total_rows == distinct_values:
                    return 'one_to_one'
                else:
                    return 'one_to_many'
            
        except Exception as e:
            logger.warning(f"Failed to determine relationship cardinality: {e}")
        
        return 'unknown'
    
    def _find_orphaned_tables(
        self,
        tables: List[TableInfo],
        relationships: List[RelationshipInfo]
    ) -> List[str]:
        """Find tables that have no relationships with other tables."""
        
        connected_tables = set()
        
        for rel in relationships:
            connected_tables.add(rel.parent_table)
            connected_tables.add(rel.child_table)
        
        orphaned = []
        for table in tables:
            if table.name not in connected_tables:
                orphaned.append(table.name)
        
        return orphaned
    
    def _find_duplicate_indexes(self, tables: List[TableInfo]) -> List[Dict[str, Any]]:
        """Find duplicate or redundant indexes."""
        
        duplicates = []
        
        for table in tables:
            # Group indexes by columns
            index_groups = defaultdict(list)
            
            for index in table.indexes:
                columns = tuple(sorted(index.get('columns', [])))
                index_groups[columns].append(index)
            
            # Find groups with multiple indexes
            for columns, indexes in index_groups.items():
                if len(indexes) > 1:
                    duplicates.append({
                        'table': table.name,
                        'columns': list(columns),
                        'duplicate_indexes': [idx.get('name') for idx in indexes],
                        'recommendation': f'Consider keeping only one index on columns: {", ".join(columns)}'
                    })
        
        return duplicates
    
    async def _analyze_performance_issues(
        self,
        database: str,
        tables: List[TableInfo]
    ) -> List[Dict[str, Any]]:
        """Analyze potential performance issues."""
        
        issues = []
        
        for table in tables:
            # Large tables without indexes
            if table.row_count > 10000 and not table.indexes:
                issues.append({
                    'type': 'missing_indexes',
                    'table': table.name,
                    'severity': 'high',
                    'description': f'Table {table.name} has {table.row_count} rows but no indexes',
                    'recommendation': 'Add appropriate indexes on frequently queried columns'
                })
            
            # Tables with too many indexes
            if len(table.indexes) > 10:
                issues.append({
                    'type': 'too_many_indexes',
                    'table': table.name,
                    'severity': 'medium',
                    'description': f'Table {table.name} has {len(table.indexes)} indexes',
                    'recommendation': 'Review and consolidate indexes to improve write performance'
                })
            
            # Large tables without primary keys
            primary_key_columns = [col for col in table.columns if col.primary_key]
            if table.row_count > 1000 and not primary_key_columns:
                issues.append({
                    'type': 'missing_primary_key',
                    'table': table.name,
                    'severity': 'high',
                    'description': f'Table {table.name} has no primary key',
                    'recommendation': 'Add a primary key for better performance and replication'
                })
            
            # Columns with high null percentage
            for column in table.columns:
                if not column.nullable and column.null_percentage > 0.1:  # 10%
                    issues.append({
                        'type': 'data_integrity',
                        'table': table.name,
                        'column': column.name,
                        'severity': 'medium',
                        'description': f'Column {column.name} is defined as NOT NULL but has {column.null_percentage:.1%} null values',
                        'recommendation': 'Fix data integrity or update column definition'
                    })
        
        return issues
    
    async def _analyze_data_quality(
        self,
        database: str,
        tables: List[TableInfo]
    ) -> List[Dict[str, Any]]:
        """Analyze data quality issues."""
        
        issues = []
        
        for table in tables:
            for column in table.columns:
                # High cardinality in small tables (potential data quality issue)
                if table.row_count < 1000 and column.cardinality > table.row_count * 0.9:
                    issues.append({
                        'type': 'high_cardinality',
                        'table': table.name,
                        'column': column.name,
                        'severity': 'low',
                        'description': f'Column {column.name} has very high cardinality ({column.cardinality}/{table.row_count})',
                        'recommendation': 'Review if this column should have more standardized values'
                    })
                
                # Low cardinality in large tables (potential indexing opportunity)
                if table.row_count > 10000 and column.cardinality < 100 and not column.is_indexed:
                    issues.append({
                        'type': 'indexing_opportunity',
                        'table': table.name,
                        'column': column.name,
                        'severity': 'low',
                        'description': f'Column {column.name} has low cardinality and might benefit from indexing',
                        'recommendation': 'Consider adding an index if this column is frequently used in WHERE clauses'
                    })
                
                # Potential email/phone validation issues
                if 'email' in column.name.lower():
                    sample_invalid = [v for v in column.sample_values if isinstance(v, str) and '@' not in v]
                    if sample_invalid:
                        issues.append({
                            'type': 'data_validation',
                            'table': table.name,
                            'column': column.name,
                            'severity': 'medium',
                            'description': f'Email column {column.name} contains invalid email addresses',
                            'recommendation': 'Implement email validation constraints',
                            'sample_invalid': sample_invalid[:5]
                        })
        
        return issues
    
    async def compare_schemas(
        self,
        database1: str,
        database2: str,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compare schemas between two databases."""
        
        # Analyze both databases
        schema1 = await self.analyze_database_schema(database1, deep_analysis=False)
        schema2 = await self.analyze_database_schema(database2, deep_analysis=False)
        
        comparison = {
            'database1': database1,
            'database2': database2,
            'comparison_timestamp': datetime.now().isoformat(),
            'differences': {}
        }
        
        if table_name:
            # Compare specific table
            table1 = next((t for t in schema1.tables if t.name == table_name), None)
            table2 = next((t for t in schema2.tables if t.name == table_name), None)
            
            if not table1:
                comparison['differences']['table_missing_in_db1'] = True
            elif not table2:
                comparison['differences']['table_missing_in_db2'] = True
            else:
                comparison['differences'] = self._compare_tables(table1, table2)
        else:
            # Compare all tables
            tables1 = {t.name: t for t in schema1.tables}
            tables2 = {t.name: t for t in schema2.tables}
            
            # Find missing tables
            missing_in_db2 = set(tables1.keys()) - set(tables2.keys())
            missing_in_db1 = set(tables2.keys()) - set(tables1.keys())
            common_tables = set(tables1.keys()) & set(tables2.keys())
            
            comparison['differences'] = {
                'missing_in_db2': list(missing_in_db2),
                'missing_in_db1': list(missing_in_db1),
                'table_differences': {}
            }
            
            # Compare common tables
            for table_name in common_tables:
                table_diff = self._compare_tables(tables1[table_name], tables2[table_name])
                if table_diff:  # Only include if there are differences
                    comparison['differences']['table_differences'][table_name] = table_diff
        
        return comparison
    
    def _compare_tables(self, table1: TableInfo, table2: TableInfo) -> Dict[str, Any]:
        """Compare two table structures."""
        
        differences = {}
        
        # Compare columns
        columns1 = {c.name: c for c in table1.columns}
        columns2 = {c.name: c for c in table2.columns}
        
        missing_in_table2 = set(columns1.keys()) - set(columns2.keys())
        missing_in_table1 = set(columns2.keys()) - set(columns1.keys())
        common_columns = set(columns1.keys()) & set(columns2.keys())
        
        if missing_in_table1:
            differences['columns_missing_in_table1'] = list(missing_in_table1)
        if missing_in_table2:
            differences['columns_missing_in_table2'] = list(missing_in_table2)
        
        # Compare common columns
        column_differences = {}
        for col_name in common_columns:
            col1, col2 = columns1[col_name], columns2[col_name]
            col_diff = {}
            
            if col1.data_type != col2.data_type:
                col_diff['data_type'] = {'table1': col1.data_type, 'table2': col2.data_type}
            if col1.nullable != col2.nullable:
                col_diff['nullable'] = {'table1': col1.nullable, 'table2': col2.nullable}
            if col1.primary_key != col2.primary_key:
                col_diff['primary_key'] = {'table1': col1.primary_key, 'table2': col2.primary_key}
            
            if col_diff:
                column_differences[col_name] = col_diff
        
        if column_differences:
            differences['column_differences'] = column_differences
        
        # Compare row counts
        if abs(table1.row_count - table2.row_count) > table1.row_count * 0.1:  # 10% difference
            differences['row_count_difference'] = {
                'table1': table1.row_count,
                'table2': table2.row_count,
                'percentage_difference': abs(table1.row_count - table2.row_count) / max(table1.row_count, table2.row_count)
            }
        
        return differences
    
    async def generate_schema_migration(
        self,
        source_database: str,
        target_database: str,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate migration scripts to synchronize schemas."""
        
        comparison = await self.compare_schemas(source_database, target_database, table_name)
        differences = comparison['differences']
        
        migration_scripts = {
            'up_sql': [],
            'down_sql': [],
            'data_migrations': []
        }
        
        if table_name:
            # Single table migration
            if differences.get('table_missing_in_db2'):
                # Create table in target database
                source_schema = await self.analyze_database_schema(source_database, deep_analysis=False)
                source_table = next((t for t in source_schema.tables if t.name == table_name), None)
                
                if source_table:
                    create_sql = self._generate_create_table_sql(source_table)
                    migration_scripts['up_sql'].append(create_sql)
                    migration_scripts['down_sql'].append(f"DROP TABLE IF EXISTS {table_name};")
            
            # Handle column differences
            col_differences = differences.get('column_differences', {})
            for col_name, col_diff in col_differences.items():
                if 'data_type' in col_diff:
                    alter_sql = f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {col_diff['data_type']['table1']};"
                    migration_scripts['up_sql'].append(alter_sql)
        
        else:
            # Full database migration
            for missing_table in differences.get('missing_in_db2', []):
                # Generate CREATE TABLE for missing tables
                source_schema = await self.analyze_database_schema(source_database, deep_analysis=False)
                source_table = next((t for t in source_schema.tables if t.name == missing_table), None)
                
                if source_table:
                    create_sql = self._generate_create_table_sql(source_table)
                    migration_scripts['up_sql'].append(create_sql)
                    migration_scripts['down_sql'].append(f"DROP TABLE IF EXISTS {missing_table};")
        
        return {
            'comparison': comparison,
            'migration_scripts': migration_scripts,
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_create_table_sql(self, table: TableInfo) -> str:
        """Generate CREATE TABLE SQL from table info."""
        
        columns_sql = []
        
        for column in table.columns:
            col_sql = f"{column.name} {column.data_type}"
            
            if not column.nullable:
                col_sql += " NOT NULL"
            
            if column.default_value is not None:
                if isinstance(column.default_value, str):
                    col_sql += f" DEFAULT '{column.default_value}'"
                else:
                    col_sql += f" DEFAULT {column.default_value}"
            
            if column.primary_key:
                col_sql += " PRIMARY KEY"
            
            columns_sql.append(col_sql)
        
        create_sql = f"""CREATE TABLE {table.name} (
    {',\n    '.join(columns_sql)}
);"""
        
        return create_sql
    
    async def get_schema_health_report(self, database: str) -> Dict[str, Any]:
        """Generate a comprehensive schema health report."""
        
        analysis = await self.analyze_database_schema(database, deep_analysis=True)
        
        # Calculate health scores
        total_issues = (
            len(analysis.performance_issues) +
            len(analysis.data_quality_issues) +
            len(analysis.duplicate_indexes)
        )
        
        total_tables = len(analysis.tables)
        orphaned_percentage = len(analysis.orphaned_tables) / total_tables if total_tables > 0 else 0
        
        # Health score calculation (0-100)
        health_score = max(0, 100 - (
            len(analysis.performance_issues) * 10 +
            len(analysis.data_quality_issues) * 5 +
            len(analysis.duplicate_indexes) * 3 +
            orphaned_percentage * 20
        ))
        
        # Recommendations
        recommendations = []
        
        if analysis.performance_issues:
            high_severity_perf = len([i for i in analysis.performance_issues if i.get('severity') == 'high'])
            recommendations.append(f"Address {high_severity_perf} high-severity performance issues")
        
        if analysis.orphaned_tables:
            recommendations.append(f"Review {len(analysis.orphaned_tables)} orphaned tables for potential relationships")
        
        if analysis.duplicate_indexes:
            recommendations.append(f"Remove {len(analysis.duplicate_indexes)} duplicate indexes to improve write performance")
        
        return {
            'database': database,
            'health_score': round(health_score, 1),
            'summary': {
                'total_tables': total_tables,
                'total_columns': sum(len(table.columns) for table in analysis.tables),
                'total_relationships': len(analysis.relationships),
                'orphaned_tables': len(analysis.orphaned_tables),
                'performance_issues': len(analysis.performance_issues),
                'data_quality_issues': len(analysis.data_quality_issues),
                'duplicate_indexes': len(analysis.duplicate_indexes)
            },
            'recommendations': recommendations,
            'detailed_analysis': asdict(analysis),
            'generated_at': datetime.now().isoformat()
        }