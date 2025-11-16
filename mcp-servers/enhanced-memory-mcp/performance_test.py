#!/usr/bin/env python3
"""
Performance test for enhanced-memory-mcp server
Tests the system under load with many entities and operations
"""

import sys
import json
import subprocess
import time
import threading
from pathlib import Path
from datetime import datetime

class PerformanceTest:
    def __init__(self, python_path, server_path):
        self.python_path = python_path
        self.server_path = server_path
        self.process = None
        self.request_id = 1
        
    def start_server(self):
        """Start the MCP server"""
        self.process = subprocess.Popen(
            [self.python_path, self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        time.sleep(2)
        
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "perf-test", "version": "1.0.0"}
            }
        }
        self.request_id += 1
        
        request_json = json.dumps(init_request) + '\n'
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
        
        # Read response
        response_line = self.process.stdout.readline()
        return json.loads(response_line.strip()) if response_line else None
    
    def send_request(self, method, params=None):
        """Send a request to the server"""
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        
        if params:
            request["params"] = params
        
        self.request_id += 1
        
        start_time = time.time()
        
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
        
        response_line = self.process.stdout.readline()
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # ms
        
        if response_line:
            response = json.loads(response_line.strip())
            return response, response_time
        else:
            return None, response_time
    
    def stop_server(self):
        """Stop the server"""
        if self.process:
            self.process.terminate()
            self.process.wait()
    
    def test_bulk_entity_creation(self, num_entities=100):
        """Test creating many entities"""
        print(f"\n🧪 Testing bulk entity creation ({num_entities} entities)")
        
        entities = []
        for i in range(num_entities):
            entities.append({
                "name": f"perf_test_entity_{i}",
                "entityType": "performance_test",
                "observations": [
                    f"Entity {i} observation 1 with some content",
                    f"Entity {i} observation 2 with different content", 
                    f"Entity {i} observation 3 with even more content for testing compression"
                ]
            })
        
        start_time = time.time()
        response, response_time = self.send_request("tools/call", {
            "name": "create_entities",
            "arguments": {"entities": entities}
        })
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000
        
        print(f"  ⏱️  Total time: {total_time:.1f}ms")
        print(f"  ⚡ Response time: {response_time:.1f}ms")
        print(f"  📊 Throughput: {num_entities / (total_time / 1000):.1f} entities/sec")
        
        if response and "result" in response:
            content = json.loads(response["result"]["content"][0]["text"])
            if content.get("success"):
                print(f"  ✅ Created {content.get('entities_created', 0)} entities")
                print(f"  🗜️  Overall compression: {content.get('overall_savings', '0%')}")
                print(f"  💾 Size reduction: {content.get('total_original_bytes', 0) - content.get('total_compressed_bytes', 0)} bytes")
            else:
                print("  ❌ Bulk creation failed")
        
        return response_time
    
    def test_concurrent_searches(self, num_searches=50):
        """Test concurrent search operations"""
        print(f"\n🔍 Testing concurrent searches ({num_searches} searches)")
        
        search_queries = [
            "entity", "test", "performance", "observation", "content",
            "Entity", "Test", "Performance", "Observation", "Content"
        ]
        
        response_times = []
        
        start_time = time.time()
        for i in range(num_searches):
            query = search_queries[i % len(search_queries)]
            response, response_time = self.send_request("tools/call", {
                "name": "search_nodes",
                "arguments": {"query": query}
            })
            response_times.append(response_time)
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        print(f"  ⏱️  Total time: {total_time:.1f}ms")
        print(f"  📊 Avg response time: {avg_response_time:.1f}ms")
        print(f"  ⚡ Min response time: {min_response_time:.1f}ms")
        print(f"  🐌 Max response time: {max_response_time:.1f}ms")
        print(f"  🔍 Search throughput: {num_searches / (total_time / 1000):.1f} searches/sec")
        
        return avg_response_time
    
    def test_memory_status_performance(self):
        """Test memory status retrieval performance"""
        print(f"\n📊 Testing memory status performance")
        
        response_times = []
        
        for i in range(10):
            response, response_time = self.send_request("tools/call", {
                "name": "get_memory_status",
                "arguments": {}
            })
            response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        print(f"  📊 Avg response time: {avg_response_time:.1f}ms")
        
        if response and "result" in response:
            content = json.loads(response["result"]["content"][0]["text"])
            stats = content.get("statistics", {})
            print(f"  🏪 Total entities: {stats.get('total_entities', 0)}")
            print(f"  🗜️  Compression savings: {stats.get('compression_savings_percentage', '0%')}")
            print(f"  📈 Total accesses: {stats.get('total_accesses', 0)}")
            print(f"  💿 Database size: {content.get('database_size_bytes', 0) / 1024:.1f} KB")
        
        return avg_response_time
    
    def test_graph_read_performance(self):
        """Test full graph read performance"""
        print(f"\n🕸️  Testing graph read performance")
        
        response_times = []
        
        for i in range(5):
            response, response_time = self.send_request("tools/call", {
                "name": "read_graph",
                "arguments": {}
            })
            response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        print(f"  📊 Avg response time: {avg_response_time:.1f}ms")
        
        if response and "result" in response:
            content = json.loads(response["result"]["content"][0]["text"])
            entities = content.get("entities", [])
            relations = content.get("relations", [])
            print(f"  🎯 Entities in graph: {len(entities)}")
            print(f"  🔗 Relations in graph: {len(relations)}")
        
        return avg_response_time

def main():
    """Run performance tests"""
    print("🚀 ENHANCED MEMORY MCP SERVER PERFORMANCE TEST")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup paths
    current_dir = Path(__file__).parent
    venv_python = current_dir.parent / ".venv_mcp" / "bin" / "python"
    server_path = current_dir / "server.py"
    
    if venv_python.exists():
        python_path = str(venv_python)
        print(f"🐍 Using virtual environment Python: {python_path}")
    else:
        python_path = sys.executable
        print(f"🐍 Using system Python: {python_path}")
    
    # Initialize test
    test = PerformanceTest(python_path, str(server_path))
    
    try:
        print("\n🚀 Starting server...")
        init_response = test.start_server()
        
        if not init_response or "result" not in init_response:
            print("❌ Failed to start server")
            return 1
        
        print("✅ Server started successfully")
        
        # Run performance tests
        tests = [
            ("Small batch", lambda: test.test_bulk_entity_creation(10)),
            ("Medium batch", lambda: test.test_bulk_entity_creation(50)),
            ("Large batch", lambda: test.test_bulk_entity_creation(100)),
            ("Search performance", lambda: test.test_concurrent_searches(25)),
            ("Status performance", lambda: test.test_memory_status_performance()),
            ("Graph read", lambda: test.test_graph_read_performance())
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
                results[test_name] = None
        
        # Summary
        print(f"\n📋 PERFORMANCE SUMMARY")
        print("=" * 50)
        for test_name, result in results.items():
            if result is not None:
                print(f"  {test_name:<20}: {result:>8.1f}ms")
            else:
                print(f"  {test_name:<20}: {'FAILED':>8}")
        
        print(f"\n✅ Performance test completed successfully")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return 1
    
    finally:
        test.stop_server()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())