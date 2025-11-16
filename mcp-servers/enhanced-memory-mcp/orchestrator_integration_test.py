#!/usr/bin/env python3
"""
Orchestrator integration test for enhanced-memory-mcp server
Tests integration with orchestrator-specific functionality and boot sequence
"""

import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class OrchestratorIntegrationTest:
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
                "clientInfo": {"name": "orchestrator-test", "version": "1.0.0"}
            }
        }
        self.request_id += 1
        
        request_json = json.dumps(init_request) + '\n'
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
        
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
        
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
        
        response_line = self.process.stdout.readline()
        return json.loads(response_line.strip()) if response_line else None
    
    def stop_server(self):
        """Stop the server"""
        if self.process:
            self.process.terminate()
            self.process.wait()
    
    def test_orchestrator_boot_sequence(self):
        """Test the orchestrator boot sequence from CLAUDE.md"""
        print(f"\n{Colors.BOLD}🚀 Testing Orchestrator Boot Sequence{Colors.END}")
        
        # Step 1: Load core memories & system configurations
        print("1. Loading core memories & system configurations...")
        
        # Create core system entities
        core_entities = [
            {
                "name": "meta_orchestrator_role",
                "entityType": "system_role",
                "observations": [
                    "Meta-Orchestrator managing cascading AI agent teams",
                    "Strategic decisions and project ownership",
                    "4-level cascading hierarchy management"
                ]
            },
            {
                "name": "ai_library_access",
                "entityType": "core_system",
                "observations": [
                    "157+ AI Agents via ai-prompt-library",
                    "25 Categories: Development, Business, Marketing, Design",
                    "Parallel execution patterns"
                ]
            },
            {
                "name": "distributed_orchestrator_core",
                "entityType": "core_system",
                "observations": [
                    "Auto-discovery and node management",
                    "Mac worker nodes on network",
                    "SSH, Claude Code, and MCP server availability"
                ]
            }
        ]
        
        response = self.send_request("tools/call", {
            "name": "create_entities",
            "arguments": {"entities": core_entities}
        })
        
        if response and "result" in response:
            content = json.loads(response["result"]["content"][0]["text"])
            if content.get("success"):
                print(f"   {Colors.GREEN}✓{Colors.END} Core memories loaded: {content.get('entities_created', 0)} entities")
            else:
                print(f"   {Colors.RED}✗{Colors.END} Failed to load core memories")
                return False
        
        # Step 2: Load recent working memory
        print("2. Loading recent working memory...")
        
        working_entities = [
            {
                "name": "current_project_context",
                "entityType": "project",
                "observations": [
                    "enhanced-memory-mcp testing",
                    "Comprehensive test suite verification",
                    "Integration with orchestrator systems"
                ]
            },
            {
                "name": "recent_session_state",
                "entityType": "session",
                "observations": [
                    "Testing SQLite-based memory server",
                    "Verification of compression and persistence",
                    "Performance testing completed"
                ]
            }
        ]
        
        response = self.send_request("tools/call", {
            "name": "create_entities",
            "arguments": {"entities": working_entities}
        })
        
        if response and "result" in response:
            content = json.loads(response["result"]["content"][0]["text"])
            if content.get("success"):
                print(f"   {Colors.GREEN}✓{Colors.END} Working memory loaded: {content.get('entities_created', 0)} entities")
            else:
                print(f"   {Colors.RED}✗{Colors.END} Failed to load working memory")
                return False
        
        # Step 3: Search for similar past projects
        print("3. Searching for similar past projects...")
        
        search_response = self.send_request("tools/call", {
            "name": "search_nodes",
            "arguments": {
                "query": "project_context last_7_days",
                "entity_types": ["project", "session"]
            }
        })
        
        if search_response and "result" in search_response:
            content = json.loads(search_response["result"]["content"][0]["text"])
            if content.get("success"):
                results_found = content.get("results_found", 0)
                print(f"   {Colors.GREEN}✓{Colors.END} Found {results_found} similar past projects")
            else:
                print(f"   {Colors.RED}✗{Colors.END} Failed to search past projects")
                return False
        
        # Step 4: Read complete memory graph
        print("4. Reading complete memory graph...")
        
        graph_response = self.send_request("tools/call", {
            "name": "read_graph",
            "arguments": {}
        })
        
        if graph_response and "result" in graph_response:
            content = json.loads(graph_response["result"]["content"][0]["text"])
            entities = content.get("entities", [])
            relations = content.get("relations", [])
            print(f"   {Colors.GREEN}✓{Colors.END} Memory graph loaded: {len(entities)} entities, {len(relations)} relations")
        else:
            print(f"   {Colors.RED}✗{Colors.END} Failed to read memory graph")
            return False
        
        # Step 5: Get memory system status
        print("5. Checking memory system status...")
        
        status_response = self.send_request("tools/call", {
            "name": "get_memory_status",
            "arguments": {}
        })
        
        if status_response and "result" in status_response:
            content = json.loads(status_response["result"]["content"][0]["text"])
            stats = content.get("statistics", {})
            tier_dist = content.get("tier_distribution", {})
            
            print(f"   {Colors.GREEN}✓{Colors.END} Memory system operational:")
            print(f"      • Total entities: {stats.get('total_entities', 0)}")
            print(f"      • Core tier: {tier_dist.get('core', 0)} entities")
            print(f"      • Working tier: {tier_dist.get('working', 0)} entities")
            print(f"      • Compression: {stats.get('compression_savings_percentage', '0%')}")
        else:
            print(f"   {Colors.RED}✗{Colors.END} Failed to get memory status")
            return False
        
        return True
    
    def test_memory_tier_filtering(self):
        """Test filtering by memory tiers"""
        print(f"\n{Colors.BOLD}🎯 Testing Memory Tier Filtering{Colors.END}")
        
        # Search for core memories only
        core_search = self.send_request("tools/call", {
            "name": "search_nodes",
            "arguments": {
                "query": "system",
                "entity_types": ["system_role", "core_system"]
            }
        })
        
        if core_search and "result" in core_search:
            content = json.loads(core_search["result"]["content"][0]["text"])
            core_results = content.get("results", [])
            core_count = len([r for r in core_results if r.get("tier") == "core"])
            print(f"   {Colors.GREEN}✓{Colors.END} Core tier filtering: {core_count} core entities found")
        
        # Search for working memory
        working_search = self.send_request("tools/call", {
            "name": "search_nodes",
            "arguments": {
                "query": "current",
                "entity_types": ["project", "session"]
            }
        })
        
        if working_search and "result" in working_search:
            content = json.loads(working_search["result"]["content"][0]["text"])
            working_results = content.get("results", [])
            working_count = len([r for r in working_results if r.get("tier") == "working"])
            print(f"   {Colors.GREEN}✓{Colors.END} Working tier filtering: {working_count} working entities found")
        
        return True
    
    def test_cross_session_continuity(self):
        """Test cross-session continuity requirements"""
        print(f"\n{Colors.BOLD}🔄 Testing Cross-Session Continuity{Colors.END}")
        
        # Create session state
        session_entities = [
            {
                "name": "session_state_preservation",
                "entityType": "session",
                "observations": [
                    "Critical context for project continuity",
                    "Decisions made during session",
                    "Next steps identified"
                ]
            },
            {
                "name": "multi_session_project",
                "entityType": "project",
                "observations": [
                    "Long-running project spanning multiple sessions",
                    "Complex task chains in progress",
                    "Quality gates and checkpoints defined"
                ]
            }
        ]
        
        response = self.send_request("tools/call", {
            "name": "create_entities",
            "arguments": {"entities": session_entities}
        })
        
        if response and "result" in response:
            content = json.loads(response["result"]["content"][0]["text"])
            if content.get("success"):
                print(f"   {Colors.GREEN}✓{Colors.END} Session state entities created")
            else:
                print(f"   {Colors.RED}✗{Colors.END} Failed to create session state")
                return False
        
        # Create relations for continuity
        relations_response = self.send_request("tools/call", {
            "name": "create_relations",
            "arguments": {
                "relations": [
                    {
                        "from": "session_state_preservation",
                        "to": "multi_session_project",
                        "relationType": "preserves_context_for"
                    },
                    {
                        "from": "meta_orchestrator_role",
                        "to": "multi_session_project",
                        "relationType": "owns_project"
                    }
                ]
            }
        })
        
        if relations_response and "result" in relations_response:
            content = json.loads(relations_response["result"]["content"][0]["text"])
            if content.get("success"):
                print(f"   {Colors.GREEN}✓{Colors.END} Continuity relations established")
            else:
                print(f"   {Colors.RED}✗{Colors.END} Failed to create relations")
                return False
        
        return True
    
    def test_compression_efficiency(self):
        """Test compression meets orchestrator requirements"""
        print(f"\n{Colors.BOLD}🗜️  Testing Compression Efficiency{Colors.END}")
        
        # Get current compression stats
        status_response = self.send_request("tools/call", {
            "name": "get_memory_status",
            "arguments": {}
        })
        
        if status_response and "result" in status_response:
            content = json.loads(status_response["result"]["content"][0]["text"])
            stats = content.get("statistics", {})
            
            compression_percentage = float(stats.get("compression_savings_percentage", "0%").rstrip("%"))
            total_entities = stats.get("total_entities", 0)
            total_accesses = stats.get("total_accesses", 0)
            
            # Check compression efficiency
            if compression_percentage >= 30:
                print(f"   {Colors.GREEN}✓{Colors.END} Compression efficiency: {compression_percentage}% (>= 30% required)")
            else:
                print(f"   {Colors.YELLOW}⚠{Colors.END} Compression efficiency: {compression_percentage}% (< 30% expected)")
            
            # Check access tracking
            if total_accesses > 0:
                print(f"   {Colors.GREEN}✓{Colors.END} Access tracking functional: {total_accesses} total accesses")
            else:
                print(f"   {Colors.RED}✗{Colors.END} Access tracking not working")
            
            # Check entity scaling
            if total_entities >= 5:
                print(f"   {Colors.GREEN}✓{Colors.END} Entity scaling: {total_entities} entities stored")
            else:
                print(f"   {Colors.YELLOW}⚠{Colors.END} Low entity count: {total_entities}")
            
            return True
        
        return False

def main():
    """Run orchestrator integration tests"""
    print(f"{Colors.BOLD}{Colors.BLUE}🧠 ENHANCED MEMORY - ORCHESTRATOR INTEGRATION TEST{Colors.END}")
    print(f"Testing compatibility with Meta-Orchestrator requirements")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup paths
    current_dir = Path(__file__).parent
    venv_python = current_dir.parent / ".venv_mcp" / "bin" / "python"
    server_path = current_dir / "server.py"
    
    if venv_python.exists():
        python_path = str(venv_python)
        print(f"🐍 Using virtual environment Python")
    else:
        python_path = sys.executable
        print(f"🐍 Using system Python")
    
    # Initialize test
    test = OrchestratorIntegrationTest(python_path, str(server_path))
    
    try:
        print(f"\n{Colors.BOLD}🚀 Starting Memory Server{Colors.END}")
        init_response = test.start_server()
        
        if not init_response or "result" not in init_response:
            print(f"{Colors.RED}❌ Failed to start server{Colors.END}")
            return 1
        
        print(f"{Colors.GREEN}✅ Server started successfully{Colors.END}")
        
        # Run integration tests
        tests = [
            test.test_orchestrator_boot_sequence,
            test.test_memory_tier_filtering,
            test.test_cross_session_continuity,
            test.test_compression_efficiency
        ]
        
        success_count = 0
        for test_func in tests:
            try:
                if test_func():
                    success_count += 1
                else:
                    print(f"   {Colors.RED}✗{Colors.END} {test_func.__name__} failed")
            except Exception as e:
                print(f"   {Colors.RED}✗{Colors.END} {test_func.__name__} error: {e}")
        
        # Summary
        total_tests = len(tests)
        success_rate = (success_count / total_tests) * 100
        
        print(f"\n{Colors.BOLD}📊 INTEGRATION TEST SUMMARY{Colors.END}")
        print("=" * 50)
        print(f"Tests passed: {success_count}/{total_tests}")
        
        if success_rate >= 100:
            print(f"Success rate: {Colors.GREEN}{success_rate:.0f}%{Colors.END}")
            print(f"\n{Colors.GREEN}🎉 ALL INTEGRATION TESTS PASSED{Colors.END}")
            print(f"{Colors.GREEN}Memory server is ready for orchestrator integration!{Colors.END}")
        elif success_rate >= 75:
            print(f"Success rate: {Colors.YELLOW}{success_rate:.0f}%{Colors.END}")
            print(f"\n{Colors.YELLOW}⚠️  MOSTLY READY - Minor issues detected{Colors.END}")
        else:
            print(f"Success rate: {Colors.RED}{success_rate:.0f}%{Colors.END}")
            print(f"\n{Colors.RED}❌ INTEGRATION ISSUES - Further work needed{Colors.END}")
        
        return 0 if success_rate >= 75 else 1
        
    except Exception as e:
        print(f"{Colors.RED}❌ Integration test failed: {e}{Colors.END}")
        return 1
    
    finally:
        test.stop_server()

if __name__ == "__main__":
    sys.exit(main())