"""
Caveman compression integration for Enhanced Memory MCP
Adds automatic compression layer to memory storage
"""

import sys
from pathlib import Path

# Add cluster-deployment to path for caveman_utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'cluster-deployment'))
from caveman_utils import compress_observations, get_compression_stats


def compress_entity_observations(entity):
    """
    Compress observations in an entity before storage

    Args:
        entity: Entity dict with 'observations' array

    Returns:
        Modified entity with compressed observations and compression metadata
    """
    if 'observations' not in entity or not entity['observations']:
        return entity

    # Compress observations
    compressed_obs, stats = compress_observations(
        entity['observations'],
        content_type='observation'
    )

    # Store both compressed and original (for now, during testing phase)
    # In production, we may want to store only compressed version
    entity['observations_original'] = entity['observations']
    entity['observations'] = compressed_obs

    # Add compression metadata
    entity['compression_meta'] = {
        'enabled': True,
        'total_observations': stats['total_observations'],
        'observations_compressed': stats['observations_compressed'],
        'observations_skipped': stats['observations_skipped'],
        'token_reduction_pct': stats['token_reduction_pct'],
        'total_original_tokens': stats['total_original_tokens'],
        'total_compressed_tokens': stats['total_compressed_tokens']
    }

    return entity


def decompress_entity_observations(entity):
    """
    Decompress observations when retrieving from storage

    Args:
        entity: Entity dict potentially with compressed observations

    Returns:
        Entity with decompressed observations
    """
    # Check if entity has compression metadata
    if 'compression_meta' not in entity or not entity['compression_meta'].get('enabled'):
        return entity

    # If original observations are stored, restore them
    if 'observations_original' in entity:
        entity['observations'] = entity['observations_original']
        # Don't delete original yet, keep for A/B testing

    # Note: Full decompression using LLM would happen here
    # For now, compressed observations are already human-readable

    return entity


def get_compression_statistics():
    """
    Get global compression statistics from caveman_utils

    Returns:
        dict with compression stats
    """
    return get_compression_stats()


# Example usage and integration instructions
if __name__ == '__main__':
    print("Enhanced Memory MCP - Compression Integration")
    print("=" * 60)
    print()
    print("Integration Steps:")
    print()
    print("1. Modify memory_manager.py create_entities() function:")
    print()
    print("   from compression_integration import compress_entity_observations")
    print()
    print("   def create_entities(entities):")
    print("       for entity in entities:")
    print("           # Apply compression")
    print("           entity = compress_entity_observations(entity)")
    print()
    print("           # Continue with existing logic...")
    print("           store_entity(entity)")
    print()
    print("2. Modify search/retrieval functions:")
    print()
    print("   from compression_integration import decompress_entity_observations")
    print()
    print("   def search_nodes(query):")
    print("       results = qdrant_search(query)")
    print()
    print("       # Decompress results")
    print("       decompressed = [")
    print("           decompress_entity_observations(r)")
    print("           for r in results")
    print("       ]")
    print()
    print("       return decompressed")
    print()
    print("3. Add compression stats to get_memory_status():")
    print()
    print("   from compression_integration import get_compression_statistics")
    print()
    print("   def get_memory_status():")
    print("       status = {")
    print("           # ... existing status ...")
    print("           'compression': get_compression_statistics()")
    print("       }")
    print("       return status")
    print()
    print("=" * 60)
    print()
    print("Testing compression on sample entity...")
    print()

    # Test entity
    test_entity = {
        'name': 'distributed_execution_test',
        'entityType': 'experience',
        'observations': [
            'The distributed execution system was tested with seven different test cases to verify functionality across the cluster. All tests passed successfully, demonstrating that tasks can be routed to the appropriate nodes based on their requirements.',
            'The builder node successfully executed Linux-specific commands, while the orchestrator coordinated the overall workflow.',
            'We observed approximately 0.5 seconds of routing overhead and 1-2 seconds of SSH connection time, which is acceptable for tasks with execution times greater than 5 seconds.'
        ]
    }

    print("Original entity:")
    print(f"  Name: {test_entity['name']}")
    print(f"  Observations: {len(test_entity['observations'])}")
    for i, obs in enumerate(test_entity['observations'], 1):
        print(f"    {i}. {obs[:60]}...")
    print()

    # Compress
    compressed_entity = compress_entity_observations(test_entity)

    print("Compressed entity:")
    print(f"  Name: {compressed_entity['name']}")
    print(f"  Observations: {len(compressed_entity['observations'])}")
    for i, obs in enumerate(compressed_entity['observations'], 1):
        print(f"    {i}. {obs[:60]}...")
    print()

    print("Compression metadata:")
    meta = compressed_entity['compression_meta']
    print(f"  Total observations: {meta['total_observations']}")
    print(f"  Compressed: {meta['observations_compressed']}")
    print(f"  Skipped: {meta['observations_skipped']}")
    print(f"  Token reduction: {meta['token_reduction_pct']:.1f}%")
    print(f"  Original tokens: {meta['total_original_tokens']}")
    print(f"  Compressed tokens: {meta['total_compressed_tokens']}")
    print()

    # Test decompression
    decompressed_entity = decompress_entity_observations(compressed_entity)

    print("Decompressed entity:")
    print(f"  Name: {decompressed_entity['name']}")
    print(f"  Observations: {len(decompressed_entity['observations'])}")
    print()

    print("=" * 60)
    print("Integration test complete!")
    print()
    print("Global compression statistics:")
    stats = get_compression_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
