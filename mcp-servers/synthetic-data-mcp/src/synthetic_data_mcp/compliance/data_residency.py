"""
Data residency management system for geographic compliance.

Ensures data is stored and processed in accordance with regional
regulations and data sovereignty requirements.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from pathlib import Path
import hashlib

from loguru import logger
import geoip2.database
import pycountry
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import boto3
from azure.storage.blob import BlobServiceClient
from google.cloud import storage as gcs

Base = declarative_base()


class DataRegion(Enum):
    """Supported data regions."""
    US_EAST = "us-east-1"
    US_WEST = "us-west-2"
    EU_WEST = "eu-west-1"
    EU_CENTRAL = "eu-central-1"
    UK = "uk-south-1"
    CANADA = "ca-central-1"
    AUSTRALIA = "ap-southeast-2"
    SINGAPORE = "ap-southeast-1"
    JAPAN = "ap-northeast-1"
    INDIA = "ap-south-1"
    BRAZIL = "sa-east-1"
    SOUTH_AFRICA = "af-south-1"


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    REGULATED = "regulated"


class ResidencyRequirement(Enum):
    """Types of data residency requirements."""
    STRICT = "strict"  # Data must never leave region
    PRIMARY = "primary"  # Primary copy must be in region
    BACKUP_ALLOWED = "backup_allowed"  # Backups can be outside
    TRANSIT_ALLOWED = "transit_allowed"  # Can transit through other regions
    NO_RESTRICTION = "no_restriction"


@dataclass
class GeographicPolicy:
    """Geographic data policy."""
    policy_id: str
    region: DataRegion
    countries: List[str]
    requirement: ResidencyRequirement
    data_types: List[str]
    retention_days: int
    encryption_required: bool
    audit_required: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataLocation:
    """Current location of data."""
    data_id: str
    primary_region: DataRegion
    replica_regions: List[DataRegion]
    storage_service: str  # s3, azure, gcs, local
    bucket_name: str
    object_key: str
    created_at: datetime
    last_accessed: datetime
    size_bytes: int
    classification: DataClassification


class DataResidencyPolicy(Base):
    """Data residency policy database model."""
    __tablename__ = "data_residency_policies"
    
    id = Column(String, primary_key=True)
    region = Column(String, nullable=False)
    countries = Column(JSON)
    requirement = Column(String, nullable=False)
    data_types = Column(JSON)
    retention_days = Column(Integer)
    encryption_required = Column(Boolean, default=True)
    audit_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON, default=dict)


class DataLocationRecord(Base):
    """Data location tracking database model."""
    __tablename__ = "data_locations"
    
    data_id = Column(String, primary_key=True)
    data_hash = Column(String, index=True)
    primary_region = Column(String, nullable=False)
    replica_regions = Column(JSON, default=list)
    storage_service = Column(String)
    bucket_name = Column(String)
    object_key = Column(String)
    classification = Column(String)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    last_verified = Column(DateTime)
    compliance_status = Column(String)


class DataMovement(Base):
    """Data movement audit log."""
    __tablename__ = "data_movements"
    
    id = Column(Integer, primary_key=True)
    data_id = Column(String, nullable=False, index=True)
    source_region = Column(String)
    destination_region = Column(String)
    movement_type = Column(String)  # replication, migration, backup, restore
    initiated_by = Column(String)
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String)  # pending, in_progress, completed, failed
    size_bytes = Column(Integer)
    metadata = Column(JSON, default=dict)


class DataResidencyManager:
    """Manages data residency and geographic compliance."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.policies: Dict[str, GeographicPolicy] = {}
        self.region_mapping = self._initialize_region_mapping()
        self.geo_reader = self._initialize_geoip()
        self._load_policies()
    
    def _initialize_region_mapping(self) -> Dict[str, DataRegion]:
        """Initialize country to region mapping."""
        return {
            # European countries -> EU regions
            "DE": DataRegion.EU_CENTRAL,
            "FR": DataRegion.EU_WEST,
            "IT": DataRegion.EU_WEST,
            "ES": DataRegion.EU_WEST,
            "NL": DataRegion.EU_WEST,
            "BE": DataRegion.EU_WEST,
            "PL": DataRegion.EU_CENTRAL,
            "SE": DataRegion.EU_WEST,
            "DK": DataRegion.EU_WEST,
            "FI": DataRegion.EU_WEST,
            "NO": DataRegion.EU_WEST,
            
            # UK
            "GB": DataRegion.UK,
            
            # North America
            "US": DataRegion.US_EAST,
            "CA": DataRegion.CANADA,
            "MX": DataRegion.US_EAST,
            
            # Asia Pacific
            "JP": DataRegion.JAPAN,
            "SG": DataRegion.SINGAPORE,
            "AU": DataRegion.AUSTRALIA,
            "NZ": DataRegion.AUSTRALIA,
            "IN": DataRegion.INDIA,
            "CN": DataRegion.SINGAPORE,  # Special handling for China
            
            # South America
            "BR": DataRegion.BRAZIL,
            "AR": DataRegion.BRAZIL,
            "CL": DataRegion.BRAZIL,
            
            # Africa
            "ZA": DataRegion.SOUTH_AFRICA,
            "NG": DataRegion.SOUTH_AFRICA,
            "EG": DataRegion.EU_WEST,  # Route through EU
        }
    
    def _initialize_geoip(self):
        """Initialize GeoIP database for IP geolocation."""
        try:
            # In production, use MaxMind GeoIP2 database
            return geoip2.database.Reader('/usr/share/GeoIP/GeoLite2-Country.mmdb')
        except:
            logger.warning("GeoIP database not available")
            return None
    
    def _load_policies(self):
        """Load data residency policies from database."""
        policies = self.db.query(DataResidencyPolicy).all()
        
        for policy in policies:
            self.policies[policy.id] = GeographicPolicy(
                policy_id=policy.id,
                region=DataRegion(policy.region),
                countries=policy.countries,
                requirement=ResidencyRequirement(policy.requirement),
                data_types=policy.data_types,
                retention_days=policy.retention_days,
                encryption_required=policy.encryption_required,
                audit_required=policy.audit_required,
                metadata=policy.metadata or {}
            )
    
    def create_policy(
        self,
        region: DataRegion,
        countries: List[str],
        requirement: ResidencyRequirement,
        data_types: List[str],
        retention_days: int = 90
    ) -> GeographicPolicy:
        """Create a new data residency policy."""
        policy_id = f"POLICY-{region.value}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        policy = GeographicPolicy(
            policy_id=policy_id,
            region=region,
            countries=countries,
            requirement=requirement,
            data_types=data_types,
            retention_days=retention_days,
            encryption_required=True,
            audit_required=True
        )
        
        # Store in database
        db_policy = DataResidencyPolicy(
            id=policy_id,
            region=region.value,
            countries=countries,
            requirement=requirement.value,
            data_types=data_types,
            retention_days=retention_days,
            encryption_required=True,
            audit_required=True
        )
        
        self.db.add(db_policy)
        self.db.commit()
        
        self.policies[policy_id] = policy
        logger.info(f"Created data residency policy: {policy_id}")
        
        return policy
    
    async def get_required_region(
        self,
        user_ip: Optional[str] = None,
        user_country: Optional[str] = None,
        data_type: str = "general"
    ) -> DataRegion:
        """Determine required region for data storage."""
        # Determine country
        country = user_country
        
        if not country and user_ip and self.geo_reader:
            try:
                response = self.geo_reader.country(user_ip)
                country = response.country.iso_code
            except:
                logger.warning(f"Could not geolocate IP: {user_ip}")
        
        if not country:
            # Default to US East if country cannot be determined
            return DataRegion.US_EAST
        
        # Check for specific policies
        for policy in self.policies.values():
            if country in policy.countries and data_type in policy.data_types:
                return policy.region
        
        # Use region mapping
        return self.region_mapping.get(country, DataRegion.US_EAST)
    
    async def validate_data_location(
        self,
        data_id: str,
        required_region: DataRegion,
        current_location: DataLocation
    ) -> Tuple[bool, List[str]]:
        """Validate if data location meets residency requirements."""
        violations = []
        
        # Get applicable policies
        applicable_policies = [
            p for p in self.policies.values()
            if p.region == required_region
        ]
        
        if not applicable_policies:
            # No specific policy, basic validation
            if current_location.primary_region != required_region:
                violations.append(f"Data not in required region {required_region.value}")
            return len(violations) == 0, violations
        
        for policy in applicable_policies:
            # Check primary region
            if policy.requirement == ResidencyRequirement.STRICT:
                if current_location.primary_region != policy.region:
                    violations.append(f"STRICT: Data must be in {policy.region.value}")
                if current_location.replica_regions:
                    for replica in current_location.replica_regions:
                        if replica != policy.region:
                            violations.append(f"STRICT: Replica in {replica.value} violates policy")
            
            elif policy.requirement == ResidencyRequirement.PRIMARY:
                if current_location.primary_region != policy.region:
                    violations.append(f"PRIMARY: Primary copy must be in {policy.region.value}")
            
            # Check encryption
            if policy.encryption_required and current_location.classification != DataClassification.PUBLIC:
                # Would check actual encryption status
                pass
            
            # Check retention
            age_days = (datetime.utcnow() - current_location.created_at).days
            if age_days > policy.retention_days:
                violations.append(f"Data exceeds {policy.retention_days} day retention policy")
        
        return len(violations) == 0, violations
    
    async def store_data(
        self,
        data: bytes,
        data_id: str,
        classification: DataClassification,
        user_country: Optional[str] = None,
        user_ip: Optional[str] = None
    ) -> DataLocation:
        """Store data in compliance with residency requirements."""
        # Determine required region
        required_region = await self.get_required_region(
            user_ip=user_ip,
            user_country=user_country,
            data_type=classification.value
        )
        
        # Select storage service based on region
        storage_config = self._get_storage_config(required_region)
        
        # Store data
        location = await self._store_to_region(
            data=data,
            data_id=data_id,
            region=required_region,
            storage_config=storage_config,
            classification=classification
        )
        
        # Record location
        self._record_data_location(location)
        
        # Audit log
        await self._audit_data_storage(data_id, location)
        
        logger.info(f"Stored data {data_id} in {required_region.value}")
        
        return location
    
    def _get_storage_config(self, region: DataRegion) -> Dict[str, Any]:
        """Get storage configuration for region."""
        # Map regions to cloud provider configurations
        if region in [DataRegion.US_EAST, DataRegion.US_WEST]:
            return {
                "provider": "aws",
                "region": region.value,
                "bucket": f"synthetic-data-{region.value}",
                "kms_key": f"arn:aws:kms:{region.value}:123456789:key/abc"
            }
        elif region in [DataRegion.EU_WEST, DataRegion.EU_CENTRAL, DataRegion.UK]:
            return {
                "provider": "azure",
                "region": region.value,
                "container": f"synthetic-data-{region.value}",
                "key_vault": f"https://synthetic-{region.value}.vault.azure.net/"
            }
        else:
            return {
                "provider": "gcs",
                "region": region.value,
                "bucket": f"synthetic-data-{region.value}",
                "kms_key": f"projects/synthetic/locations/{region.value}/keyRings/data/cryptoKeys/key1"
            }
    
    async def _store_to_region(
        self,
        data: bytes,
        data_id: str,
        region: DataRegion,
        storage_config: Dict[str, Any],
        classification: DataClassification
    ) -> DataLocation:
        """Store data to specific region."""
        provider = storage_config["provider"]
        
        if provider == "aws":
            location = await self._store_to_s3(data, data_id, storage_config)
        elif provider == "azure":
            location = await self._store_to_azure(data, data_id, storage_config)
        elif provider == "gcs":
            location = await self._store_to_gcs(data, data_id, storage_config)
        else:
            location = await self._store_locally(data, data_id, region)
        
        location.classification = classification
        location.primary_region = region
        
        return location
    
    async def _store_to_s3(
        self,
        data: bytes,
        data_id: str,
        config: Dict[str, Any]
    ) -> DataLocation:
        """Store data to AWS S3."""
        s3 = boto3.client('s3', region_name=config["region"])
        
        bucket = config["bucket"]
        key = f"data/{data_id}"
        
        # Store with encryption
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=config["kms_key"],
            Metadata={
                "data_id": data_id,
                "stored_at": datetime.utcnow().isoformat()
            }
        )
        
        return DataLocation(
            data_id=data_id,
            primary_region=DataRegion(config["region"]),
            replica_regions=[],
            storage_service="s3",
            bucket_name=bucket,
            object_key=key,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            size_bytes=len(data),
            classification=DataClassification.INTERNAL
        )
    
    async def _store_to_azure(
        self,
        data: bytes,
        data_id: str,
        config: Dict[str, Any]
    ) -> DataLocation:
        """Store data to Azure Blob Storage."""
        connection_string = f"DefaultEndpointsProtocol=https;AccountName=synthetic{config['region']}"
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        
        container = config["container"]
        blob_name = f"data/{data_id}"
        
        blob_client = blob_service.get_blob_client(
            container=container,
            blob=blob_name
        )
        
        # Store with encryption
        blob_client.upload_blob(
            data,
            overwrite=True,
            metadata={
                "data_id": data_id,
                "stored_at": datetime.utcnow().isoformat()
            }
        )
        
        return DataLocation(
            data_id=data_id,
            primary_region=DataRegion(config["region"]),
            replica_regions=[],
            storage_service="azure",
            bucket_name=container,
            object_key=blob_name,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            size_bytes=len(data),
            classification=DataClassification.INTERNAL
        )
    
    async def _store_to_gcs(
        self,
        data: bytes,
        data_id: str,
        config: Dict[str, Any]
    ) -> DataLocation:
        """Store data to Google Cloud Storage."""
        client = gcs.Client()
        bucket = client.bucket(config["bucket"])
        blob = bucket.blob(f"data/{data_id}")
        
        # Store with encryption
        blob.upload_from_string(
            data,
            content_type='application/octet-stream'
        )
        
        blob.metadata = {
            "data_id": data_id,
            "stored_at": datetime.utcnow().isoformat()
        }
        blob.patch()
        
        return DataLocation(
            data_id=data_id,
            primary_region=DataRegion(config["region"]),
            replica_regions=[],
            storage_service="gcs",
            bucket_name=config["bucket"],
            object_key=f"data/{data_id}",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            size_bytes=len(data),
            classification=DataClassification.INTERNAL
        )
    
    async def _store_locally(
        self,
        data: bytes,
        data_id: str,
        region: DataRegion
    ) -> DataLocation:
        """Store data locally (for development/testing)."""
        base_path = Path(f"/var/data/residency/{region.value}")
        base_path.mkdir(parents=True, exist_ok=True)
        
        file_path = base_path / f"{data_id}.dat"
        
        with open(file_path, "wb") as f:
            f.write(data)
        
        return DataLocation(
            data_id=data_id,
            primary_region=region,
            replica_regions=[],
            storage_service="local",
            bucket_name=str(base_path),
            object_key=str(file_path),
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            size_bytes=len(data),
            classification=DataClassification.INTERNAL
        )
    
    def _record_data_location(self, location: DataLocation):
        """Record data location in database."""
        # Calculate data hash for integrity
        data_hash = hashlib.sha256(location.data_id.encode()).hexdigest()
        
        record = DataLocationRecord(
            data_id=location.data_id,
            data_hash=data_hash,
            primary_region=location.primary_region.value,
            replica_regions=[r.value for r in location.replica_regions],
            storage_service=location.storage_service,
            bucket_name=location.bucket_name,
            object_key=location.object_key,
            classification=location.classification.value,
            size_bytes=location.size_bytes,
            created_at=location.created_at,
            last_accessed=location.last_accessed,
            last_verified=datetime.utcnow(),
            compliance_status="compliant"
        )
        
        self.db.merge(record)  # Update if exists
        self.db.commit()
    
    async def _audit_data_storage(self, data_id: str, location: DataLocation):
        """Audit data storage for compliance."""
        movement = DataMovement(
            data_id=data_id,
            source_region=None,
            destination_region=location.primary_region.value,
            movement_type="initial_storage",
            initiated_by="system",
            initiated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status="completed",
            size_bytes=location.size_bytes,
            metadata={
                "classification": location.classification.value,
                "storage_service": location.storage_service
            }
        )
        
        self.db.add(movement)
        self.db.commit()
    
    async def migrate_data(
        self,
        data_id: str,
        target_region: DataRegion,
        reason: str
    ) -> DataLocation:
        """Migrate data to different region."""
        # Get current location
        current = self.db.query(DataLocationRecord).filter_by(data_id=data_id).first()
        if not current:
            raise ValueError(f"Data {data_id} not found")
        
        # Check if migration is allowed
        current_region = DataRegion(current.primary_region)
        can_migrate = await self._can_migrate(data_id, current_region, target_region)
        
        if not can_migrate:
            raise ValueError(f"Migration from {current_region.value} to {target_region.value} not allowed")
        
        # Start migration
        movement = DataMovement(
            data_id=data_id,
            source_region=current_region.value,
            destination_region=target_region.value,
            movement_type="migration",
            initiated_by="system",
            initiated_at=datetime.utcnow(),
            status="in_progress",
            size_bytes=current.size_bytes,
            metadata={"reason": reason}
        )
        
        self.db.add(movement)
        self.db.commit()
        
        try:
            # Retrieve data from current location
            data = await self._retrieve_data(current)
            
            # Store in new region
            new_location = await self._store_to_region(
                data=data,
                data_id=data_id,
                region=target_region,
                storage_config=self._get_storage_config(target_region),
                classification=DataClassification(current.classification)
            )
            
            # Delete from old location
            await self._delete_data(current)
            
            # Update records
            current.primary_region = target_region.value
            current.last_verified = datetime.utcnow()
            
            movement.completed_at = datetime.utcnow()
            movement.status = "completed"
            
            self.db.commit()
            
            logger.info(f"Migrated data {data_id} from {current_region.value} to {target_region.value}")
            
            return new_location
            
        except Exception as e:
            movement.status = "failed"
            movement.metadata["error"] = str(e)
            self.db.commit()
            raise
    
    async def _can_migrate(
        self,
        data_id: str,
        source_region: DataRegion,
        target_region: DataRegion
    ) -> bool:
        """Check if data migration is allowed."""
        # Check policies
        for policy in self.policies.values():
            if policy.region == source_region:
                if policy.requirement == ResidencyRequirement.STRICT:
                    return False
                elif policy.requirement == ResidencyRequirement.PRIMARY:
                    # Can migrate if target is also compliant
                    return target_region in [policy.region]
        
        return True
    
    async def _retrieve_data(self, location: DataLocationRecord) -> bytes:
        """Retrieve data from storage."""
        if location.storage_service == "s3":
            s3 = boto3.client('s3', region_name=location.primary_region)
            response = s3.get_object(Bucket=location.bucket_name, Key=location.object_key)
            return response['Body'].read()
        
        elif location.storage_service == "local":
            with open(location.object_key, "rb") as f:
                return f.read()
        
        # Additional storage providers...
        return b""
    
    async def _delete_data(self, location: DataLocationRecord):
        """Delete data from storage."""
        if location.storage_service == "s3":
            s3 = boto3.client('s3', region_name=location.primary_region)
            s3.delete_object(Bucket=location.bucket_name, Key=location.object_key)
        
        elif location.storage_service == "local":
            Path(location.object_key).unlink(missing_ok=True)
        
        # Additional storage providers...
    
    async def replicate_data(
        self,
        data_id: str,
        target_regions: List[DataRegion]
    ) -> List[DataLocation]:
        """Replicate data to additional regions."""
        # Get current location
        current = self.db.query(DataLocationRecord).filter_by(data_id=data_id).first()
        if not current:
            raise ValueError(f"Data {data_id} not found")
        
        # Check replication policies
        for target_region in target_regions:
            if not await self._can_replicate(data_id, DataRegion(current.primary_region), target_region):
                raise ValueError(f"Replication to {target_region.value} not allowed")
        
        # Retrieve data
        data = await self._retrieve_data(current)
        
        replicas = []
        for target_region in target_regions:
            # Store replica
            replica_location = await self._store_to_region(
                data=data,
                data_id=f"{data_id}-replica-{target_region.value}",
                region=target_region,
                storage_config=self._get_storage_config(target_region),
                classification=DataClassification(current.classification)
            )
            
            replicas.append(replica_location)
            
            # Update records
            current.replica_regions = current.replica_regions or []
            current.replica_regions.append(target_region.value)
        
        self.db.commit()
        
        logger.info(f"Replicated data {data_id} to {len(replicas)} regions")
        
        return replicas
    
    async def _can_replicate(
        self,
        data_id: str,
        source_region: DataRegion,
        target_region: DataRegion
    ) -> bool:
        """Check if data replication is allowed."""
        for policy in self.policies.values():
            if policy.region == source_region:
                if policy.requirement == ResidencyRequirement.STRICT:
                    return target_region == source_region
                elif policy.requirement == ResidencyRequirement.BACKUP_ALLOWED:
                    return True
        
        return True
    
    def get_data_locations(self, data_id: str) -> Dict[str, Any]:
        """Get all locations where data is stored."""
        record = self.db.query(DataLocationRecord).filter_by(data_id=data_id).first()
        
        if not record:
            return None
        
        return {
            "data_id": data_id,
            "primary_region": record.primary_region,
            "replica_regions": record.replica_regions or [],
            "storage_service": record.storage_service,
            "classification": record.classification,
            "size_bytes": record.size_bytes,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "last_accessed": record.last_accessed.isoformat() if record.last_accessed else None,
            "compliance_status": record.compliance_status
        }
    
    def generate_residency_report(self) -> Dict[str, Any]:
        """Generate data residency compliance report."""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_data_objects": 0,
            "by_region": {},
            "by_classification": {},
            "compliance_summary": {
                "compliant": 0,
                "non_compliant": 0,
                "pending_review": 0
            },
            "recent_movements": []
        }
        
        # Analyze data locations
        locations = self.db.query(DataLocationRecord).all()
        report["total_data_objects"] = len(locations)
        
        for location in locations:
            # By region
            region = location.primary_region
            if region not in report["by_region"]:
                report["by_region"][region] = {
                    "count": 0,
                    "size_bytes": 0,
                    "classifications": {}
                }
            
            report["by_region"][region]["count"] += 1
            report["by_region"][region]["size_bytes"] += location.size_bytes or 0
            
            # By classification
            classification = location.classification
            if classification not in report["by_classification"]:
                report["by_classification"][classification] = {
                    "count": 0,
                    "regions": []
                }
            
            report["by_classification"][classification]["count"] += 1
            if region not in report["by_classification"][classification]["regions"]:
                report["by_classification"][classification]["regions"].append(region)
            
            # Compliance status
            if location.compliance_status == "compliant":
                report["compliance_summary"]["compliant"] += 1
            elif location.compliance_status == "non_compliant":
                report["compliance_summary"]["non_compliant"] += 1
            else:
                report["compliance_summary"]["pending_review"] += 1
        
        # Recent movements
        recent_movements = self.db.query(DataMovement).order_by(
            DataMovement.initiated_at.desc()
        ).limit(10).all()
        
        for movement in recent_movements:
            report["recent_movements"].append({
                "data_id": movement.data_id,
                "type": movement.movement_type,
                "source": movement.source_region,
                "destination": movement.destination_region,
                "initiated_at": movement.initiated_at.isoformat() if movement.initiated_at else None,
                "status": movement.status
            })
        
        return report


# Initialize default policies for major regions
def initialize_default_policies(manager: DataResidencyManager):
    """Initialize default data residency policies."""
    
    # GDPR - EU data must stay in EU
    manager.create_policy(
        region=DataRegion.EU_WEST,
        countries=["DE", "FR", "IT", "ES", "NL", "BE", "PL", "SE", "DK", "FI"],
        requirement=ResidencyRequirement.PRIMARY,
        data_types=["personal_data", "health_data", "financial_data"],
        retention_days=90
    )
    
    # UK GDPR
    manager.create_policy(
        region=DataRegion.UK,
        countries=["GB"],
        requirement=ResidencyRequirement.PRIMARY,
        data_types=["personal_data", "health_data", "financial_data"],
        retention_days=90
    )
    
    # Canadian data sovereignty
    manager.create_policy(
        region=DataRegion.CANADA,
        countries=["CA"],
        requirement=ResidencyRequirement.STRICT,
        data_types=["health_data", "government_data"],
        retention_days=365
    )
    
    # Australian data sovereignty
    manager.create_policy(
        region=DataRegion.AUSTRALIA,
        countries=["AU", "NZ"],
        requirement=ResidencyRequirement.PRIMARY,
        data_types=["health_data", "financial_data"],
        retention_days=180
    )
    
    # Singapore - ASEAN hub
    manager.create_policy(
        region=DataRegion.SINGAPORE,
        countries=["SG", "MY", "TH", "ID", "PH", "VN"],
        requirement=ResidencyRequirement.BACKUP_ALLOWED,
        data_types=["personal_data", "financial_data"],
        retention_days=90
    )
    
    # India data localization
    manager.create_policy(
        region=DataRegion.INDIA,
        countries=["IN"],
        requirement=ResidencyRequirement.STRICT,
        data_types=["payment_data", "government_data"],
        retention_days=180
    )
    
    logger.info("Initialized default data residency policies")