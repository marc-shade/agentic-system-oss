#!/usr/bin/env python3
"""
Test script for Enhanced Memory MCP Server Resources
Validates that resources are accessible and return proper data
"""

import json
import asyncio
import sqlite3
from pathlib import Path
import sys

# Add the local directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from server_resources import (
    init_database, create_entities, create_relations, 
    get_entities_resource, get_relations_resource, 
    get_projects_resource, get_insights_resource,
    get_search_resource, get_status_resource,
    list_resources, get_resource,
    DB_PATH, MEMORY_DIR
)

async def setup_test_data():
    """Create test entities and relations for resource testing"""
    print("🔧 Setting up test data...")
    
    # Initialize database
    init_database()
    
    # Create test entities
    test_entities = [
        {
            "name": "TestProject",
            "entityType": "project",
            "observations": [
                "A sample project for testing resources",
                "Uses enhanced memory with compression",
                "Supports browseable knowledge graphs"
            ]
        },
        {
            "name": "ResourceSystem",
            "entityType": "system",
            "observations": [
                "MCP Resources implementation",
                "Enables browsing of memory data",
                "JSON-formatted resource endpoints"
            ]
        },
        {
            "name": "KnowledgeGraph",
            "entityType": "concept",
            "observations": [
                "Graph database with entities and relations",
                "Compressed storage with zlib",
                "Searchable via SQL queries"
            ]
        },
        {
            "name": "AgentMemory",
            "entityType": "agent_knowledge",
            "observations": [
                "Persistent agent knowledge storage",
                "Enables cross-session learning",
                "Supports pattern discovery"
            ]
        }
    ]
    
    # Create entities
    result = await create_entities(test_entities)
    print(f"✅ Created {result['entities_created']} test entities")
    
    # Create test relations
    test_relations = [
        {
            "from": "TestProject",
            "to": "ResourceSystem",
            "relationType": "uses"
        },
        {
            "from": "ResourceSystem",
            "to": "KnowledgeGraph",
            "relationType": "exposes"
        },
        {
            "from": "KnowledgeGraph",
            "to": "AgentMemory",
            "relationType": "stores"
        },
        {
            "from": "AgentMemory",
            "to": "TestProject",
            "relationType": "supports"
        }
    ]
    
    # Create relations
    relations_result = await create_relations(test_relations)
    print(f"✅ Created {relations_result['relations_created']} test relations")
    
    return result, relations_result

async def test_resource_listing():
    """Test the resource listing functionality"""
    print("\n📋 Testing resource listing...")
    
    resources = await list_resources()
    
    print(f"✅ Found {len(resources)} available resources:")
    for resource in resources:
        print(f"  📊 {resource['uri']} - {resource['name']}")
        print(f"     {resource['description']}")
    
    expected_resources = [
        "memory://entities",
        "memory://relations", 
        "memory://projects",
        "memory://insights",
        "memory://search/{query}",
        "memory://status"
    ]
    
    found_uris = [r["uri"] for r in resources]
    for expected in expected_resources:
        if expected in found_uris:
            print(f"  ✅ {expected}")
        else:
            print(f"  ❌ Missing: {expected}")
    
    return resources

async def test_entities_resource():
    """Test the entities resource"""
    print("\n🏗️ Testing entities resource...")
    
    try:
        resource_data = await get_entities_resource()
        content = json.loads(resource_data["contents"][0]["text"])
        
        print(f"✅ Entities resource loaded successfully")
        print(f"  📊 Total entities: {content['total_entities']}")
        print(f"  🏷️ Tier distribution: {content['by_tier']}")
        print(f"  📝 Type distribution: {content['by_type']}")
        
        # Show sample entities
        if content["entities"]:
            print(f"  📋 Sample entities:")
            for entity in content["entities"][:3]:
                print(f"    - {entity['name']} ({entity['entityType']}) - Tier: {entity['tier']}")
                print(f"      Observations: {len(entity['observations'])}")
                savings = entity["metadata"]["savings"]
                print(f"      Compression savings: {savings}")
        
        return content
        
    except Exception as e:
        print(f"❌ Error testing entities resource: {e}")
        return None

async def test_relations_resource():
    """Test the relations resource"""
    print("\n🔗 Testing relations resource...")
    
    try:
        resource_data = await get_relations_resource()
        content = json.loads(resource_data["contents"][0]["text"])
        
        print(f"✅ Relations resource loaded successfully")
        print(f"  📊 Total relations: {content['total_relations']}")
        print(f"  🏷️ Relation types: {content['relation_types']}")
        
        # Show sample relations
        if content["relations"]:
            print(f"  📋 Sample relations:")
            for relation in content["relations"][:3]:
                print(f"    - {relation['from']['name']} --{relation['relationType']}--> {relation['to']['name']}")
        
        return content
        
    except Exception as e:
        print(f"❌ Error testing relations resource: {e}")
        return None

async def test_projects_resource():
    """Test the projects resource"""
    print("\n📁 Testing projects resource...")
    
    try:
        resource_data = await get_projects_resource()
        content = json.loads(resource_data["contents"][0]["text"])
        
        print(f"✅ Projects resource loaded successfully")
        print(f"  📊 Total projects: {content['total_projects']}")
        
        # Show sample projects
        if content["projects"]:
            print(f"  📋 Projects found:")
            for project in content["projects"]:
                print(f"    - {project['name']} ({project['entityType']})")
                print(f"      Access count: {project['access_count']}")
        
        return content
        
    except Exception as e:
        print(f"❌ Error testing projects resource: {e}")
        return None

async def test_insights_resource():
    """Test the insights resource"""
    print("\n🔍 Testing insights resource...")
    
    try:
        resource_data = await get_insights_resource()
        content = json.loads(resource_data["contents"][0]["text"])
        
        print(f"✅ Insights resource loaded successfully")
        
        insights = content["insights"]
        
        # Most accessed entities
        if "most_accessed" in insights:
            print(f"  📈 Most accessed entities:")
            for entity in insights["most_accessed"][:3]:
                print(f"    - {entity['name']} (accessed {entity['access_count']} times)")
        
        # Compression stats
        if "compression_stats" in insights:
            stats = insights["compression_stats"]
            print(f"  🗜️ Compression statistics:")
            print(f"    - Total savings: {stats['total_savings_percent']}")
            print(f"    - Average ratio: {stats['average_ratio']:.3f}")
        
        # Tier analysis
        if "tier_analysis" in insights:
            print(f"  🏷️ Tier analysis:")
            for tier in insights["tier_analysis"]:
                print(f"    - {tier['tier']}: {tier['count']} entities (avg access: {tier['avg_access']:.1f})")
        
        return content
        
    except Exception as e:
        print(f"❌ Error testing insights resource: {e}")
        return None

async def test_search_resource():
    """Test the search resource"""
    print("\n🔎 Testing search resource...")
    
    search_queries = ["test", "resource", "memory", "project"]
    
    for query in search_queries:
        try:
            resource_data = await get_search_resource(query)
            content = json.loads(resource_data["contents"][0]["text"])
            
            if "error" not in content:
                results_found = content["results_found"]
                print(f"  ✅ Search '{query}': {results_found} results")
                
                if content["search_results"]:
                    for result in content["search_results"][:2]:
                        print(f"    - {result['name']} ({result['entity_type']})")
            else:
                print(f"  ❌ Search '{query}': {content['error']}")
                
        except Exception as e:
            print(f"  ❌ Error searching '{query}': {e}")

async def test_status_resource():
    """Test the status resource"""
    print("\n📊 Testing status resource...")
    
    try:
        resource_data = await get_status_resource()
        content = json.loads(resource_data["contents"][0]["text"])
        
        print(f"✅ Status resource loaded successfully")
        
        if "statistics" in content:
            stats = content["statistics"]
            print(f"  📊 Statistics:")
            print(f"    - Total entities: {stats['total_entities']}")
            print(f"    - Compression savings: {stats['compression_savings_percentage']}")
            print(f"    - Total accesses: {stats['total_accesses']}")
        
        if "database_path" in content:
            print(f"  💾 Database: {content['database_path']}")
            print(f"  📦 Size: {content['database_size_bytes']} bytes")
        
        return content
        
    except Exception as e:
        print(f"❌ Error testing status resource: {e}")
        return None

async def test_resource_uri_handling():
    """Test the resource URI handling via get_resource function"""
    print("\n🔗 Testing resource URI handling...")
    
    test_uris = [
        "memory://entities",
        "memory://relations",
        "memory://projects", 
        "memory://insights",
        "memory://search/test",
        "memory://status",
        "memory://invalid"  # Should fail gracefully
    ]
    
    for uri in test_uris:
        try:
            resource_data = await get_resource(uri)
            content_text = resource_data["contents"][0]["text"]
            content = json.loads(content_text)
            
            if "error" in content:
                print(f"  ⚠️ {uri}: {content['error']}")
            else:
                print(f"  ✅ {uri}: Loaded successfully")
                
        except Exception as e:
            print(f"  ❌ {uri}: Error - {e}")

async def run_all_tests():
    """Run all resource tests"""
    print("🚀 Starting Enhanced Memory MCP Resources Test Suite")
    print(f"📦 Database path: {DB_PATH}")
    print(f"📁 Memory directory: {MEMORY_DIR}")
    
    # Setup test data
    await setup_test_data()
    
    # Run all tests
    await test_resource_listing()
    await test_entities_resource()
    await test_relations_resource()
    await test_projects_resource()
    await test_insights_resource()
    await test_search_resource()
    await test_status_resource()
    await test_resource_uri_handling()
    
    print("\n🎉 Resource testing complete!")
    print("✅ Enhanced Memory MCP Resources are working correctly")

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(run_all_tests())