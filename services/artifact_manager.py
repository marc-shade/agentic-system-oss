#!/usr/bin/env python3
"""
Artifact Manager for Builder Node
Handles storage, retrieval, and lifecycle management of build artifacts
"""

import json
import shutil
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid


class ArtifactManager:
    """Manages build artifacts for the Builder node"""

    def __init__(self, base_path: str = "/home/marc/agentic-system/artifacts"):
        self.base_path = Path(base_path)
        self.builds_path = self.base_path / "builds"
        self.cache_path = self.base_path / "cache"
        self.temp_path = self.base_path / "temp"
        self.archive_path = self.base_path / "archive"

        # Ensure directories exist
        for path in [self.builds_path, self.cache_path, self.temp_path, self.archive_path]:
            path.mkdir(parents=True, exist_ok=True)

    def create_build(
        self,
        project_id: str,
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None,
        build_type: str = "release",
        build_command: Optional[str] = None,
        webhook_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        """Create a new build and return build metadata"""

        build_id = str(uuid.uuid4())
        build_number = self._get_next_build_number(project_id)

        # Create build directory structure
        project_path = self.builds_path / project_id
        build_path = project_path / build_id
        artifacts_path = build_path / "artifacts"

        for path in [build_path, artifacts_path, artifacts_path / "binaries",
                     artifacts_path / "packages", artifacts_path / "documentation"]:
            path.mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = {
            "build_id": build_id,
            "project_id": project_id,
            "build_number": build_number,
            "node_id": "macpro51",
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "git_commit": git_commit,
            "git_branch": git_branch,
            "build_type": build_type,
            "build_command": build_command,
            "exit_code": None,
            "artifacts_count": 0,
            "artifacts_size_bytes": 0,
            "tags": tags or [],
            "webhook_url": webhook_url,
        }

        # Save metadata
        metadata_file = build_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def update_build_status(
        self,
        build_id: str,
        status: str,
        exit_code: Optional[int] = None,
        end_time: Optional[str] = None,
    ) -> Dict:
        """Update build status and metadata"""

        metadata = self.get_build_metadata(build_id)
        if not metadata:
            raise ValueError(f"Build {build_id} not found")

        metadata["status"] = status
        metadata["exit_code"] = exit_code
        metadata["end_time"] = end_time or datetime.now().isoformat()

        # Calculate duration
        if metadata["start_time"] and metadata["end_time"]:
            start = datetime.fromisoformat(metadata["start_time"])
            end = datetime.fromisoformat(metadata["end_time"])
            metadata["duration_seconds"] = int((end - start).total_seconds())

        # Save updated metadata
        project_id = metadata["project_id"]
        metadata_file = self.builds_path / project_id / build_id / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        # Update latest symlink if successful
        if status == "success":
            self._update_latest_symlink(project_id, build_id)

        return metadata

    def add_artifact(
        self,
        build_id: str,
        source_path: str,
        artifact_type: str = "binary",
        name: Optional[str] = None,
    ) -> Dict:
        """Add an artifact to a build"""

        metadata = self.get_build_metadata(build_id)
        if not metadata:
            raise ValueError(f"Build {build_id} not found")

        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Determine destination
        project_id = metadata["project_id"]
        build_path = self.builds_path / project_id / build_id
        artifacts_path = build_path / "artifacts"

        # Categorize artifact by type
        if artifact_type == "binary":
            dest_dir = artifacts_path / "binaries"
        elif artifact_type == "package":
            dest_dir = artifacts_path / "packages"
        elif artifact_type == "documentation":
            dest_dir = artifacts_path / "documentation"
        else:
            dest_dir = artifacts_path

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / (name or source.name)

        # Copy artifact
        shutil.copy2(source, dest_file)

        # Calculate checksum
        sha256 = self._calculate_sha256(dest_file)

        # Get file info
        stat = dest_file.stat()

        artifact_info = {
            "name": dest_file.name,
            "type": artifact_type,
            "path": str(dest_file.relative_to(build_path)),
            "size_bytes": stat.st_size,
            "sha256": sha256,
            "executable": os.access(dest_file, os.X_OK),
            "permissions": oct(stat.st_mode)[-3:],
        }

        # Update manifest
        self._update_manifest(build_id, artifact_info)

        # Update metadata counts
        metadata["artifacts_count"] += 1
        metadata["artifacts_size_bytes"] += stat.st_size
        metadata_file = build_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return artifact_info

    def get_build_metadata(self, build_id: str) -> Optional[Dict]:
        """Get metadata for a build"""

        # Search for build across all projects
        for project_path in self.builds_path.iterdir():
            if not project_path.is_dir():
                continue

            metadata_file = project_path / build_id / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    return json.load(f)

        return None

    def get_project_builds(
        self,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Get builds for a project"""

        project_path = self.builds_path / project_id
        if not project_path.exists():
            return []

        builds = []
        for build_path in project_path.iterdir():
            if not build_path.is_dir() or build_path.is_symlink():
                continue

            metadata_file = build_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    if status is None or metadata.get("status") == status:
                        builds.append(metadata)

        # Sort by build number descending
        builds.sort(key=lambda x: x.get("build_number", 0), reverse=True)

        return builds[:limit]

    def get_latest_build(self, project_id: str, status: str = "success") -> Optional[Dict]:
        """Get the latest successful build for a project"""

        builds = self.get_project_builds(project_id, status=status, limit=1)
        return builds[0] if builds else None

    def get_artifact_path(self, build_id: str, artifact_name: str) -> Optional[Path]:
        """Get the full path to an artifact"""

        metadata = self.get_build_metadata(build_id)
        if not metadata:
            return None

        project_id = metadata["project_id"]
        build_path = self.builds_path / project_id / build_id

        # Check manifest
        manifest_file = build_path / "manifest.json"
        if not manifest_file.exists():
            return None

        with open(manifest_file) as f:
            manifest = json.load(f)

        for artifact in manifest.get("artifacts", []):
            if artifact["name"] == artifact_name:
                return build_path / artifact["path"]

        return None

    def cleanup_old_builds(
        self,
        age_days: int = 30,
        keep_last: int = 5,
        keep_tagged: bool = True,
        dry_run: bool = False,
    ) -> Dict:
        """Clean up old builds according to retention policy"""

        cutoff_date = datetime.now() - timedelta(days=age_days)
        deleted_count = 0
        freed_bytes = 0
        kept_count = 0

        for project_path in self.builds_path.iterdir():
            if not project_path.is_dir():
                continue

            project_id = project_path.name
            builds = self.get_project_builds(project_id, limit=1000)

            # Sort by build number
            builds.sort(key=lambda x: x.get("build_number", 0), reverse=True)

            for idx, build in enumerate(builds):
                build_id = build["build_id"]
                # Handle case where end_time or start_time might be None or already a datetime
                time_value = build.get("end_time") or build.get("start_time")
                if isinstance(time_value, str):
                    build_date = datetime.fromisoformat(time_value)
                elif isinstance(time_value, datetime):
                    build_date = time_value
                else:
                    # Skip builds without valid timestamps
                    continue

                # Keep conditions
                keep_reasons = []

                if idx < keep_last:
                    keep_reasons.append(f"recent (#{idx+1})")

                if keep_tagged and build.get("tags"):
                    keep_reasons.append(f"tagged: {','.join(build['tags'])}")

                if build_date > cutoff_date:
                    keep_reasons.append(f"recent ({(datetime.now() - build_date).days} days)")

                if keep_reasons:
                    kept_count += 1
                    print(f"  Keeping {project_id}/{build_id}: {', '.join(keep_reasons)}")
                    continue

                # Delete this build
                build_path = project_path / build_id
                if build_path.exists():
                    size = self._get_directory_size(build_path)
                    freed_bytes += size

                    if not dry_run:
                        shutil.rmtree(build_path)
                        deleted_count += 1
                        print(f"  Deleted {project_id}/{build_id} ({size / 1024 / 1024:.1f} MB)")
                    else:
                        deleted_count += 1
                        print(f"  Would delete {project_id}/{build_id} ({size / 1024 / 1024:.1f} MB)")

        return {
            "deleted_count": deleted_count,
            "kept_count": kept_count,
            "freed_mb": freed_bytes / 1024 / 1024,
            "dry_run": dry_run,
        }

    def get_stats(self) -> Dict:
        """Get artifact storage statistics"""

        total_builds = 0
        total_size = 0
        by_project = {}
        by_status = {"success": 0, "failed": 0, "running": 0}

        for project_path in self.builds_path.iterdir():
            if not project_path.is_dir():
                continue

            project_id = project_path.name
            project_builds = 0
            project_size = 0

            for build_path in project_path.iterdir():
                if not build_path.is_dir() or build_path.is_symlink():
                    continue

                metadata_file = build_path / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)

                    status = metadata.get("status", "unknown")
                    if status in by_status:
                        by_status[status] += 1

                    size = metadata.get("artifacts_size_bytes", 0)
                    project_size += size
                    total_size += size
                    project_builds += 1
                    total_builds += 1

            by_project[project_id] = {
                "count": project_builds,
                "size_gb": project_size / 1024 / 1024 / 1024,
            }

        return {
            "total_artifacts": total_builds,
            "total_size_gb": round(total_size / 1024 / 1024 / 1024, 2),
            "by_project": by_project,
            "by_status": by_status,
        }

    # Helper methods

    def _get_next_build_number(self, project_id: str) -> int:
        """Get the next build number for a project"""

        builds = self.get_project_builds(project_id, limit=1)
        if builds:
            return builds[0].get("build_number", 0) + 1
        return 1

    def _update_latest_symlink(self, project_id: str, build_id: str):
        """Update the 'latest' symlink to point to the newest successful build"""

        project_path = self.builds_path / project_id
        latest_link = project_path / "latest"

        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()

        latest_link.symlink_to(build_id)

    def _update_manifest(self, build_id: str, artifact_info: Dict):
        """Update the artifact manifest"""

        metadata = self.get_build_metadata(build_id)
        if not metadata:
            return

        project_id = metadata["project_id"]
        build_path = self.builds_path / project_id / build_id
        manifest_file = build_path / "manifest.json"

        # Load existing manifest or create new
        if manifest_file.exists():
            with open(manifest_file) as f:
                manifest = json.load(f)
        else:
            manifest = {
                "build_id": build_id,
                "artifacts": [],
                "total_size_bytes": 0,
                "total_artifacts": 0,
            }

        # Add artifact
        manifest["artifacts"].append(artifact_info)
        manifest["total_size_bytes"] += artifact_info["size_bytes"]
        manifest["total_artifacts"] += 1

        # Save manifest
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _get_directory_size(path: Path) -> int:
        """Get total size of a directory"""

        total = 0
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total


if __name__ == "__main__":
    # Test the artifact manager
    manager = ArtifactManager()

    print("Artifact Manager initialized")
    print(f"Base path: {manager.base_path}")

    stats = manager.get_stats()
    print(f"\nCurrent stats:")
    print(json.dumps(stats, indent=2))
