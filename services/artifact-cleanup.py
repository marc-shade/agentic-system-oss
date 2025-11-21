#!/usr/bin/env python3
"""
Artifact Cleanup Service
Automated cleanup of old build artifacts according to retention policies
"""

import sys
import argparse
import json
from artifact_manager import ArtifactManager


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old build artifacts"
    )
    parser.add_argument(
        "--age-days",
        type=int,
        default=30,
        help="Delete builds older than this many days (default: 30)",
    )
    parser.add_argument(
        "--keep-last",
        type=int,
        default=5,
        help="Keep at least this many recent builds per project (default: 5)",
    )
    parser.add_argument(
        "--keep-tagged",
        action="store_true",
        default=True,
        help="Keep builds with tags (default: True)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--max-size-gb",
        type=float,
        help="Maximum total artifact size in GB",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Artifact Cleanup Service")
    print("=" * 70)
    print(f"Age threshold: {args.age_days} days")
    print(f"Keep last: {args.keep_last} builds per project")
    print(f"Keep tagged: {args.keep_tagged}")
    print(f"Dry run: {args.dry_run}")
    if args.max_size_gb:
        print(f"Max size: {args.max_size_gb} GB")
    print("=" * 70)
    print()

    manager = ArtifactManager()

    # Get current stats
    print("Current artifact statistics:")
    stats = manager.get_stats()
    print(json.dumps(stats, indent=2))
    print()

    # Check if cleanup is needed
    if args.max_size_gb and stats["total_size_gb"] <= args.max_size_gb:
        print(f"Total size ({stats['total_size_gb']} GB) is within limit ({args.max_size_gb} GB)")
        print("No cleanup needed.")
        return 0

    # Run cleanup
    print("Running cleanup...")
    print()

    result = manager.cleanup_old_builds(
        age_days=args.age_days,
        keep_last=args.keep_last,
        keep_tagged=args.keep_tagged,
        dry_run=args.dry_run,
    )

    print()
    print("=" * 70)
    print("Cleanup Summary")
    print("=" * 70)
    print(f"Builds deleted: {result['deleted_count']}")
    print(f"Builds kept: {result['kept_count']}")
    print(f"Space freed: {result['freed_mb']:.1f} MB")
    print(f"Dry run: {result['dry_run']}")
    print("=" * 70)

    # Show updated stats
    if not args.dry_run and result['deleted_count'] > 0:
        print()
        print("Updated artifact statistics:")
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
