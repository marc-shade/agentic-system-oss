#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced-memory-mcp server
Tests all functionality including MCP protocol compliance, memory tiers, compression, search, and persistence
"""

import sys
import json
import subprocess
import time
import sqlite3
import threading
import signal
from pathlib import Path
from datetime import datetime
import tempfile
import os

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.details = []

    def assert_test(self, condition, test_name, error_msg=""):
        if condition:
            self.passed += 1
            print(f"  {Colors.GREEN}✓{Colors.END} {test_name}")
            return True
        else:
            self.failed += 1
            error = f"{test_name}: {error_msg}"
            self.errors.append(error)
            print(f"  {Colors.RED}✗{Colors.END} {test_name}: {Colors.RED}{error_msg}{Colors.END}")
            return False

    def add_detail(self, detail):
        self.details.append(detail)
        print(f"    {Colors.CYAN}→{Colors.END} {detail}")

    def print_summary(self):
        total = self.passed + self.failed
        if total == 0:
            print(f"\n{Colors.YELLOW}No tests were run{Colors.END}")
            return

        success_rate = (self.passed / total) * 100
        color = Colors.GREEN if success_rate >= 90 else Colors.YELLOW if success_rate >= 70 else Colors.RED
        
        print(f"\n{Colors.BOLD}=== TEST SUMMARY ==={Colors.END}")
        print(f"Total tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.END}")
        print(f"Success rate: {color}{success_rate:.1f}%{Colors.END}")
        
        if self.details:
            print(f"\n{Colors.BOLD}Key Details:{Colors.END}")
            for detail in self.details:
                print(f"  • {detail}")

class MCPServer:
    def __init__(self, python_path, server_path):
        self.python_path = python_path
        self.server_path = server_path
        self.process = None
        self.request_id = 1

    def start(self):
        """Start the MCP server process"""
        try:
            self.process = subprocess.Popen(
                [self.python_path, self.server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            time.sleep(1)  # Give server time to start
            return True
        except Exception as e:
            print(f"{Colors.RED}Failed to start server: {e}{Colors.END}")
            return False

    def send_request(self, method, params=None, timeout=10):
        """Send a request to the MCP server"""
        if not self.process:
            return None
            
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        
        if params:
            request["params"] = params
            
        self.request_id += 1
        
        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Read response with timeout
            def read_response():
                return self.process.stdout.readline()
                
            # Simple timeout implementation
            import threading
            response_data = [None]
            
            def target():
                response_data[0] = read_response()
                
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                return {"error": "timeout"}
                
            response_line = response_data[0]
            if not response_line:
                return {"error": "no_response"}
                
            return json.loads(response_line.strip())
            
        except Exception as e:
            return {"error": str(e)}

    def stop(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

def test_server_startup_and_protocol(server, result):
    """Test 1: Server startup and MCP protocol compliance"""
    print(f"\n{Colors.BOLD}=== TEST 1: Server Startup and MCP Protocol Compliance ==={Colors.END}")
    
    # Test server starts
    started = server.start()
    result.assert_test(started, "Server starts successfully")
    if not started:
        return False
    
    # Test initialize
    init_response = server.send_request("initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    })
    
    result.assert_test(
        init_response and "result" in init_response,
        "Initialize request succeeds",
        f"Response: {init_response}"
    )
    
    if init_response and "result" in init_response:
        init_result = init_response["result"]
        result.assert_test(
            "protocolVersion" in init_result,
            "Protocol version in response"
        )
        result.assert_test(
            "serverInfo" in init_result,
            "Server info in response"
        )
        result.assert_test(
            init_result["serverInfo"]["name"] == "enhanced-memory",
            "Correct server name"
        )
    
    # Test tools/list
    tools_response = server.send_request("tools/list")
    result.assert_test(
        tools_response and "result" in tools_response,
        "Tools list request succeeds"
    )
    
    if tools_response and "result" in tools_response:
        tools = tools_response["result"].get("tools", [])
        expected_tools = [
            "create_entities", "search_nodes", "read_graph", 
            "get_memory_status", "create_relations"
        ]
        
        for tool_name in expected_tools:
            has_tool = any(tool["name"] == tool_name for tool in tools)
            result.assert_test(has_tool, f"Tool '{tool_name}' available")
        
        result.add_detail(f"Available tools: {[tool['name'] for tool in tools]}")
    
    return True

def test_memory_tier_system(server, result):
    """Test 2: Memory tier system (core, working, reference, archive)"""
    print(f"\n{Colors.BOLD}=== TEST 2: Memory Tier System ==={Colors.END}")
    
    # Create entities for each tier
    test_entities = [
        {
            "name": "orchestrator_core_system",
            "entityType": "system_role",
            "observations": ["Core orchestrator functionality", "Always active"]
        },
        {
            "name": "current_project_state",
            "entityType": "project",
            "observations": ["Current project details", "Active work"]
        },
        {
            "name": "reference_documentation",
            "entityType": "reference",
            "observations": ["API documentation", "Best practices"]
        },
        {
            "name": "archive_old_project",
            "entityType": "historical",
            "observations": ["Completed project", "Historical data"]
        }
    ]
    
    create_response = server.send_request("tools/call", {
        "name": "create_entities",
        "arguments": {"entities": test_entities}
    })
    
    result.assert_test(
        create_response and "result" in create_response,
        "Create tier test entities succeeds"
    )
    
    if create_response and "result" in create_response:
        content = json.loads(create_response["result"]["content"][0]["text"])
        result.assert_test(
            content.get("success", False),
            "Entity creation successful"
        )
        result.assert_test(
            content.get("entities_created", 0) == 4,
            "All 4 entities created"
        )
        
        # Check tier classifications in results
        entities_by_tier = {}
        for entity_result in content.get("results", []):
            if "tier" in entity_result:
                tier = entity_result["tier"]
                entities_by_tier[tier] = entities_by_tier.get(tier, 0) + 1
        
        result.add_detail(f"Entities by tier: {entities_by_tier}")
        
        # Verify tier logic
        expected_tiers = {"core": 1, "working": 1, "reference": 1, "archive": 1}
        for tier, expected_count in expected_tiers.items():
            actual_count = entities_by_tier.get(tier, 0)
            result.assert_test(
                actual_count == expected_count,
                f"Tier '{tier}' has {expected_count} entity",
                f"Expected {expected_count}, got {actual_count}"
            )
    
    return True

def test_compression_functionality(server, result):
    """Test 3: Compression functionality and metrics"""
    print(f"\n{Colors.BOLD}=== TEST 3: Compression Functionality and Metrics ==={Colors.END}")
    
    # Create entity with large data to test compression
    large_observations = [
        "This is a very long observation with lots of repeated text. " * 50,
        "Another long observation with different content but still lengthy. " * 30,
        "A third observation that contains substantial information for compression testing. " * 40
    ]
    
    large_entity = {
        "name": "compression_test_entity",
        "entityType": "test",
        "observations": large_observations
    }
    
    create_response = server.send_request("tools/call", {
        "name": "create_entities",
        "arguments": {"entities": [large_entity]}
    })
    
    result.assert_test(
        create_response and "result" in create_response,
        "Create large entity for compression test"
    )
    
    if create_response and "result" in create_response:
        content = json.loads(create_response["result"]["content"][0]["text"])
        
        result.assert_test(
            content.get("success", False),
            "Large entity creation successful"
        )
        
        # Check compression metrics
        original_bytes = content.get("total_original_bytes", 0)
        compressed_bytes = content.get("total_compressed_bytes", 0)
        compression_ratio = content.get("overall_compression_ratio", 1.0)
        
        result.assert_test(
            original_bytes > 0,
            "Original size tracked",
            f"Original: {original_bytes} bytes"
        )
        
        result.assert_test(
            compressed_bytes > 0,
            "Compressed size tracked",
            f"Compressed: {compressed_bytes} bytes"
        )
        
        result.assert_test(
            compression_ratio < 1.0,
            "Compression achieved",
            f"Ratio: {compression_ratio:.3f}"
        )
        
        savings_percentage = (1 - compression_ratio) * 100
        result.add_detail(f"Compression savings: {savings_percentage:.1f}%")
        result.add_detail(f"Size reduction: {original_bytes - compressed_bytes} bytes")
        
        # Check individual entity compression
        entity_results = content.get("results", [])
        if entity_results:
            entity_result = entity_results[0]
            result.assert_test(
                "compression_ratio" in entity_result,
                "Individual compression ratio available"
            )
            result.assert_test(
                "actual_savings" in entity_result,
                "Savings percentage calculated"
            )
            result.assert_test(
                "checksum" in entity_result,
                "Integrity checksum generated"
            )
    
    return True

def test_search_capabilities(server, result):
    """Test 4: Search capabilities"""
    print(f"\n{Colors.BOLD}=== TEST 4: Search Capabilities ==={Colors.END}")
    
    # First create some searchable entities
    search_entities = [
        {
            "name": "project_alpha",
            "entityType": "project",
            "observations": ["Machine learning project", "Uses Python and TensorFlow", "Data analysis focus"]
        },
        {
            "name": "project_beta",
            "entityType": "project", 
            "observations": ["Web development project", "JavaScript and React", "Frontend focused"]
        },
        {
            "name": "team_member_alice",
            "entityType": "person",
            "observations": ["Senior developer", "Python expert", "Machine learning specialist"]
        }
    ]
    
    create_response = server.send_request("tools/call", {
        "name": "create_entities",
        "arguments": {"entities": search_entities}
    })
    
    result.assert_test(
        create_response and "result" in create_response,
        "Create searchable test entities"
    )
    
    # Test basic search
    search_response = server.send_request("tools/call", {
        "name": "search_nodes",
        "arguments": {"query": "python"}
    })
    
    result.assert_test(
        search_response and "result" in search_response,
        "Basic search request succeeds"
    )
    
    if search_response and "result" in search_response:
        content = json.loads(search_response["result"]["content"][0]["text"])
        
        result.assert_test(
            content.get("success", False),
            "Search operation successful"
        )
        
        results_found = content.get("results_found", 0)
        result.assert_test(
            results_found >= 2,
            f"Found expected results for 'python' search",
            f"Expected >= 2, found {results_found}"
        )
        
        # Check search result structure
        search_results = content.get("results", [])
        if search_results:
            first_result = search_results[0]
            expected_fields = ["id", "name", "entity_type", "tier", "access_count"]
            for field in expected_fields:
                result.assert_test(
                    field in first_result,
                    f"Search result has '{field}' field"
                )
            
            result.add_detail(f"Search returned {len(search_results)} results")
    
    # Test filtered search by entity type
    filtered_search = server.send_request("tools/call", {
        "name": "search_nodes",
        "arguments": {
            "query": "project",
            "entity_types": ["project"]
        }
    })
    
    result.assert_test(
        filtered_search and "result" in filtered_search,
        "Filtered search by entity type succeeds"
    )
    
    if filtered_search and "result" in filtered_search:
        content = json.loads(filtered_search["result"]["content"][0]["text"])
        search_results = content.get("results", [])
        
        # Verify all results are projects
        all_projects = all(r.get("entity_type") == "project" for r in search_results)
        result.assert_test(
            all_projects,
            "Filtered search returns only project entities"
        )
        
        result.add_detail(f"Filtered search returned {len(search_results)} project entities")
    
    return True

def test_cross_session_persistence(server, result):
    """Test 5: Cross-session persistence"""
    print(f"\n{Colors.BOLD}=== TEST 5: Cross-Session Persistence ==={Colors.END}")
    
    # Create some persistent entities
    persistent_entities = [
        {
            "name": "persistent_config",
            "entityType": "configuration",
            "observations": ["System configuration", "Should persist across sessions"]
        }
    ]
    
    create_response = server.send_request("tools/call", {
        "name": "create_entities",
        "arguments": {"entities": persistent_entities}
    })
    
    result.assert_test(
        create_response and "result" in create_response,
        "Create persistent entities"
    )
    
    # Get memory status before restart
    status_before = server.send_request("tools/call", {
        "name": "get_memory_status",
        "arguments": {}
    })
    
    result.assert_test(
        status_before and "result" in status_before,
        "Get memory status before restart"
    )
    
    entities_before = 0
    if status_before and "result" in status_before:
        content = json.loads(status_before["result"]["content"][0]["text"])
        entities_before = content.get("statistics", {}).get("total_entities", 0)
        result.add_detail(f"Entities before restart: {entities_before}")
    
    # Stop and restart server
    server.stop()
    time.sleep(2)
    
    restart_success = server.start()
    result.assert_test(restart_success, "Server restarts successfully")
    
    if not restart_success:
        return False
    
    # Re-initialize
    init_response = server.send_request("initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    })
    
    result.assert_test(
        init_response and "result" in init_response,
        "Re-initialize after restart"
    )
    
    # Check if data persisted
    status_after = server.send_request("tools/call", {
        "name": "get_memory_status",
        "arguments": {}
    })
    
    result.assert_test(
        status_after and "result" in status_after,
        "Get memory status after restart"
    )
    
    if status_after and "result" in status_after:
        content = json.loads(status_after["result"]["content"][0]["text"])
        entities_after = content.get("statistics", {}).get("total_entities", 0)
        
        result.assert_test(
            entities_after >= entities_before,
            "Entity count preserved across restart",
            f"Before: {entities_before}, After: {entities_after}"
        )
        
        result.add_detail(f"Entities after restart: {entities_after}")
    
    # Search for specific persistent entity
    search_persistent = server.send_request("tools/call", {
        "name": "search_nodes",
        "arguments": {"query": "persistent_config"}
    })
    
    if search_persistent and "result" in search_persistent:
        content = json.loads(search_persistent["result"]["content"][0]["text"])
        found_persistent = content.get("results_found", 0) > 0
        result.assert_test(
            found_persistent,
            "Persistent entity found after restart"
        )
    
    return True

def test_integration_points(server, result):
    """Test 6: Integration points with orchestrator"""
    print(f"\n{Colors.BOLD}=== TEST 6: Integration Points with Orchestrator ==={Colors.END}")
    
    # Test create relations functionality
    relation_entities = [
        {
            "name": "orchestrator_master",
            "entityType": "system",
            "observations": ["Main orchestrator node", "Coordination hub"]
        },
        {
            "name": "worker_node_1",
            "entityType": "system",
            "observations": ["Worker node", "Task execution"]
        }
    ]
    
    create_response = server.send_request("tools/call", {
        "name": "create_entities",
        "arguments": {"entities": relation_entities}
    })
    
    result.assert_test(
        create_response and "result" in create_response,
        "Create entities for relations test"
    )
    
    # Create relations
    relations_response = server.send_request("tools/call", {
        "name": "create_relations",
        "arguments": {
            "relations": [
                {
                    "from": "orchestrator_master",
                    "to": "worker_node_1",
                    "relationType": "manages"
                }
            ]
        }
    })
    
    result.assert_test(
        relations_response and "result" in relations_response,
        "Create relations request succeeds"
    )
    
    if relations_response and "result" in relations_response:
        content = json.loads(relations_response["result"]["content"][0]["text"])
        
        result.assert_test(
            content.get("success", False),
            "Relations creation successful"
        )
        
        relations_created = content.get("relations_created", 0)
        result.assert_test(
            relations_created == 1,
            "Expected number of relations created"
        )
    
    # Test read_graph to verify relations
    graph_response = server.send_request("tools/call", {
        "name": "read_graph",
        "arguments": {}
    })
    
    result.assert_test(
        graph_response and "result" in graph_response,
        "Read graph request succeeds"
    )
    
    if graph_response and "result" in graph_response:
        content = json.loads(graph_response["result"]["content"][0]["text"])
        
        entities = content.get("entities", [])
        relations = content.get("relations", [])
        
        result.assert_test(
            len(entities) > 0,
            "Graph contains entities"
        )
        
        result.assert_test(
            len(relations) > 0,
            "Graph contains relations"
        )
        
        # Check specific relation
        manages_relation = any(
            r.get("from") == "orchestrator_master" and 
            r.get("to") == "worker_node_1" and 
            r.get("relationType") == "manages"
            for r in relations
        )
        
        result.assert_test(
            manages_relation,
            "Specific 'manages' relation found in graph"
        )
        
        result.add_detail(f"Graph contains {len(entities)} entities and {len(relations)} relations")
    
    # Test comprehensive memory status
    status_response = server.send_request("tools/call", {
        "name": "get_memory_status",
        "arguments": {}
    })
    
    result.assert_test(
        status_response and "result" in status_response,
        "Memory status request succeeds"
    )
    
    if status_response and "result" in status_response:
        content = json.loads(status_response["result"]["content"][0]["text"])
        
        # Check status structure
        required_sections = ["statistics", "tier_distribution", "type_distribution"]
        for section in required_sections:
            result.assert_test(
                section in content,
                f"Status includes '{section}' section"
            )
        
        stats = content.get("statistics", {})
        result.add_detail(f"Total entities: {stats.get('total_entities', 0)}")
        result.add_detail(f"Compression savings: {stats.get('compression_savings_percentage', '0%')}")
        result.add_detail(f"Total accesses: {stats.get('total_accesses', 0)}")
    
    return True

def test_database_integrity(result):
    """Test 7: Database integrity and structure"""
    print(f"\n{Colors.BOLD}=== TEST 7: Database Integrity and Structure ==={Colors.END}")
    
    db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
    
    result.assert_test(
        db_path.exists(),
        "Database file exists",
        f"Path: {db_path}"
    )
    
    if not db_path.exists():
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ["entities", "observations", "relations"]
        for table in expected_tables:
            result.assert_test(
                table in tables,
                f"Table '{table}' exists"
            )
        
        # Check entities table structure
        cursor.execute("PRAGMA table_info(entities)")
        entity_columns = [col[1] for col in cursor.fetchall()]
        
        expected_entity_columns = [
            "id", "name", "entity_type", "tier", "compressed_data",
            "original_size", "compressed_size", "compression_ratio", 
            "checksum", "access_count", "created_at", "last_accessed"
        ]
        
        for column in expected_entity_columns:
            result.assert_test(
                column in entity_columns,
                f"Entities table has '{column}' column"
            )
        
        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        expected_indexes = ["idx_entities_name", "idx_entities_type", "idx_entities_accessed"]
        for index in expected_indexes:
            result.assert_test(
                index in indexes,
                f"Index '{index}' exists"
            )
        
        # Check data integrity
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM observations")
        observation_count = cursor.fetchone()[0]
        
        result.add_detail(f"Database contains {entity_count} entities and {observation_count} observations")
        
        # Check for data corruption
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        
        result.assert_test(
            integrity_result == "ok",
            "Database integrity check passes",
            f"Result: {integrity_result}"
        )
        
        conn.close()
        
    except Exception as e:
        result.assert_test(False, "Database access and integrity check", str(e))
        return False
    
    return True

def main():
    """Run comprehensive test suite"""
    print(f"{Colors.BOLD}{Colors.BLUE}=== ENHANCED MEMORY MCP SERVER COMPREHENSIVE TEST SUITE ==={Colors.END}")
    print(f"Testing SQLite-based enhanced memory server with real compression and persistence")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    result = TestResult()
    
    # Determine Python path
    current_dir = Path(__file__).parent
    venv_python = current_dir.parent / ".venv_mcp" / "bin" / "python"
    server_path = current_dir / "server.py"
    
    if venv_python.exists():
        python_path = str(venv_python)
        result.add_detail(f"Using virtual environment Python: {python_path}")
    else:
        python_path = sys.executable
        result.add_detail(f"Using system Python: {python_path}")
    
    result.add_detail(f"Server path: {server_path}")
    
    # Initialize server
    server = MCPServer(python_path, str(server_path))
    
    try:
        # Run all tests
        tests = [
            test_server_startup_and_protocol,
            test_memory_tier_system,
            test_compression_functionality,
            test_search_capabilities,
            test_cross_session_persistence,
            test_integration_points
        ]
        
        for test_func in tests:
            try:
                test_func(server, result)
            except Exception as e:
                result.assert_test(False, f"{test_func.__name__}", str(e))
        
        # Test database integrity (doesn't need running server)
        test_database_integrity(result)
        
    finally:
        # Clean up
        server.stop()
    
    # Print final results
    result.print_summary()
    
    # Return exit code based on results
    return 0 if result.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())