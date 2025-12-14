#!/usr/bin/env python3
"""
Test GraphRAG Implementation
Demonstrates graph-enhanced retrieval capabilities
"""

from pathlib import Path
import sys
import importlib.util

# Load graph_rag module directly
spec = importlib.util.spec_from_file_location("graph_rag", Path(__file__).parent / "graph-rag.py")
graph_rag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_rag)
GraphRAG = graph_rag.GraphRAG


def test_basic_search():
    """Test basic graph-enhanced search"""
    print("=== Test 1: Basic Graph-Enhanced Search ===\n")

    rag = GraphRAG()

    # Search for memory-related entities
    results = rag.graph_enhanced_search(
        query="memory system",
        include_neighbors=True,
        depth=2,
        limit=5
    )

    print(f"Found {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.entity_name}")
        print(f"   Type: {result.entity_type}")
        print(f"   Scores: Vector={result.vector_score:.3f}, Graph={result.graph_score:.3f}, Combined={result.combined_score:.3f}")
        print(f"   Neighbors: {len(result.neighbors)}")

        # Show top neighbors
        if result.neighbors:
            print(f"   Top neighbors:")
            for neighbor in sorted(result.neighbors, key=lambda x: x['weight'], reverse=True)[:3]:
                print(f"     - {neighbor['name']} [{neighbor['relation']}] (weight: {neighbor['weight']:.2f})")

        print()


def test_graph_traversal():
    """Test graph traversal from specific entity"""
    print("\n=== Test 2: Graph Traversal ===\n")

    rag = GraphRAG()

    # Get entity by name
    import sqlite3
    conn = sqlite3.connect(rag.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM entities WHERE name LIKE '%memory%' LIMIT 1")
    entity = cursor.fetchone()
    conn.close()

    if entity:
        entity_id = entity[0]
        entity_name = entity[1]

        print(f"Starting from: {entity_name} (ID: {entity_id})\n")

        # Expand graph context
        context = rag.expand_graph_context([entity_id], depth=2, min_weight=0.5)

        if entity_id in context:
            neighbors = context[entity_id]
            print(f"Found {len(neighbors)} connected entities within 2 hops\n")

            # Group by depth
            by_depth = {}
            for neighbor in neighbors:
                depth = neighbor['depth']
                if depth not in by_depth:
                    by_depth[depth] = []
                by_depth[depth].append(neighbor)

            for depth in sorted(by_depth.keys()):
                print(f"Depth {depth}: {len(by_depth[depth])} entities")
                for neighbor in by_depth[depth][:5]:
                    print(f"  - {neighbor['name']} [{neighbor['relation']}]")
                if len(by_depth[depth]) > 5:
                    print(f"  ... and {len(by_depth[depth]) - 5} more")
                print()


def test_relationship_types():
    """Test different relationship types"""
    print("\n=== Test 3: Relationship Type Analysis ===\n")

    rag = GraphRAG()

    stats = rag.get_statistics()

    print("Relationship type distribution:")
    for rel in stats['relationship_types']:
        print(f"  {rel['relation_type']}: {rel['count']} ({rel['count']/stats['relationships']*100:.1f}%)")


def test_subgraph_building():
    """Test building local subgraph"""
    print("\n=== Test 4: Subgraph Building ===\n")

    rag = GraphRAG()

    # Get a few entities
    import sqlite3
    conn = sqlite3.connect(rag.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM entities LIMIT 10")
    entity_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Build subgraph
    subgraph = rag.build_local_graph(entity_ids)

    print(f"Subgraph with {len(entity_ids)} seed entities:")
    print(f"  Nodes: {subgraph['node_count']}")
    print(f"  Edges: {subgraph['edge_count']}")
    print(f"  Avg edges/node: {subgraph['edge_count']/subgraph['node_count']:.2f}")

    print(f"\nNodes:")
    for node in subgraph['nodes'][:5]:
        print(f"  - {node['name']} ({node['entity_type']})")

    print(f"\nSample edges:")
    for edge in subgraph['edges'][:5]:
        print(f"  - {edge['from_entity_id']} --[{edge['relation_type']}]--> {edge['to_entity_id']}")


def main():
    """Run all tests"""
    print("GraphRAG Implementation Test Suite")
    print("=" * 50)

    try:
        test_basic_search()
        test_graph_traversal()
        test_relationship_types()
        test_subgraph_building()

        print("\n" + "=" * 50)
        print("All tests completed successfully!")

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
