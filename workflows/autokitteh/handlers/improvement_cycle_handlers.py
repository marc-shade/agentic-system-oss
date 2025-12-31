"""
Autonomous Improvement Cycle Handlers
Runs AGI self-improvement cycles automatically
Integrates with enhanced-memory MCP for persistent learning
"""
import os
import platform
import subprocess
import json
import time
import requests
from datetime import datetime
from pathlib import Path


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent.parent


_STORAGE_BASE = _get_storage_base()
_CONFIG_PATH = Path.home() / ".claude" / "agi" / "config.yaml"


def run_improvement_cycle(event):
    """
    Run a single AGI improvement cycle
    This is the autonomous version of manual improvement cycles
    """
    print("=" * 60)
    print(f"Autonomous Improvement Cycle - {datetime.now()}")
    print("=" * 60)

    cycle_start = time.time()
    results = {
        "timestamp": datetime.now().isoformat(),
        "status": "started",
        "entities_created": 0,
        "causal_links": 0,
        "associations": 0
    }

    try:
        # Step 1: Get current AGI status
        print("\n[1/5] Getting AGI status...")
        status = get_agi_status()
        current_cycle = status.get("improvement_cycles", 0)
        next_cycle = current_cycle + 1
        print(f"Starting cycle {next_cycle}")

        # Step 2: Run meta-learning to detect patterns
        print("\n[2/5] Running meta-learning...")
        patterns = run_meta_learning()

        # Step 3: Identify improvement focus area
        print("\n[3/5] Identifying improvement focus...")
        focus = identify_focus_area(next_cycle, patterns)
        print(f"Focus: {focus['name']} - {focus['description']}")

        # Step 4: Create improvement entities via MCP
        print("\n[4/5] Creating improvement entities...")
        entities = create_improvement_entities(focus)
        # Count created + updated entities (both are successful operations)
        created_count = entities.get("created", 0) if isinstance(entities.get("created"), int) else len(entities.get("created", []))
        updated_count = entities.get("updated", 0) if isinstance(entities.get("updated"), int) else 0
        results["entities_created"] = created_count + updated_count
        results["entity_ids"] = [r.get("id") for r in entities.get("results", [])]

        # Step 5: Build causal links and associations
        print("\n[5/5] Building knowledge graph connections...")
        links = build_knowledge_connections(entities)
        results["causal_links"] = links.get("causal_links", 0)
        results["associations"] = links.get("associations", 0)

        # Update config
        update_config(next_cycle, results)

        results["status"] = "completed"
        results["cycle_number"] = next_cycle
        results["duration_seconds"] = time.time() - cycle_start

        print(f"\n✓ Cycle {next_cycle} completed in {results['duration_seconds']:.1f}s")
        print(f"  Entities: {results['entities_created']}")
        print(f"  Causal links: {results['causal_links']}")
        print(f"  Associations: {results['associations']}")

        # Notify via voice
        notify_cycle_complete(results)

        return results

    except Exception as e:
        print(f"ERROR: Improvement cycle failed: {e}")
        import traceback
        traceback.print_exc()
        results["status"] = "error"
        results["error"] = str(e)
        return results


def run_consolidation(event):
    """
    Run memory consolidation to promote patterns to semantic concepts
    """
    print("=" * 60)
    print(f"Memory Consolidation - {datetime.now()}")
    print("=" * 60)

    try:
        # Call enhanced-memory consolidation via HTTP
        response = requests.post(
            "http://localhost:8101/consolidate",
            json={
                "time_window_hours": 24,
                "min_pattern_frequency": 3,
                "min_confidence": 0.6
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✓ Consolidation complete")
            print(f"  Patterns extracted: {result.get('patterns_found', 0)}")
            print(f"  Promoted to semantic: {result.get('patterns_promoted', 0)}")
            return result
        else:
            print(f"Consolidation API returned {response.status_code}")
            return {"status": "error", "code": response.status_code}

    except requests.exceptions.ConnectionError:
        # Fallback: run consolidation script directly
        print("MCP not available, running local consolidation...")
        return run_local_consolidation()
    except Exception as e:
        print(f"ERROR: Consolidation failed: {e}")
        return {"status": "error", "message": str(e)}


def run_local_consolidation():
    """Run consolidation via local script when MCP unavailable"""
    try:
        result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "run_consolidation.py")],
            capture_output=True,
            text=True,
            timeout=120
        )
        print(result.stdout)
        return {"status": "completed" if result.returncode == 0 else "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_agi_status():
    """Get current AGI status from config"""
    try:
        import yaml
        with open(_CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        return config.get("metrics", {})
    except Exception as e:
        print(f"Could not read config: {e}")
        return {}


def run_meta_learning():
    """Run meta-learning to detect patterns"""
    try:
        result = subprocess.run(
            ["python3", "-c", """
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
from meta_learning_engine import MetaLearningEngine
engine = MetaLearningEngine()
patterns = engine.detect_patterns(lookback_days=1)
import json
print(json.dumps({"patterns_detected": len(patterns)}))
"""],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        return {"patterns_detected": 0}
    except Exception as e:
        print(f"Meta-learning failed: {e}")
        return {"patterns_detected": 0}


def identify_focus_area(cycle_number, patterns):
    """Identify focus area for improvement based on cycle number and patterns"""
    # Rotating focus areas for continuous improvement
    focus_areas = [
        {"name": "reasoning_enhancement", "description": "Improving logical reasoning capabilities"},
        {"name": "memory_optimization", "description": "Optimizing memory storage and retrieval"},
        {"name": "causal_reasoning", "description": "Strengthening causal inference"},
        {"name": "pattern_recognition", "description": "Enhancing pattern detection"},
        {"name": "meta_cognition", "description": "Improving self-awareness and reflection"},
        {"name": "knowledge_integration", "description": "Cross-domain knowledge synthesis"},
        {"name": "planning_improvement", "description": "Better goal decomposition and planning"},
        {"name": "learning_efficiency", "description": "Faster and more effective learning"}
    ]

    return focus_areas[cycle_number % len(focus_areas)]


def create_improvement_entities(focus):
    """Create improvement entities via enhanced-memory MCP"""
    try:
        # Generate entities based on focus area
        entities = generate_entities_for_focus(focus)

        response = requests.post(
            "http://localhost:8101/create_entities",
            json={"entities": entities},
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Entity creation returned {response.status_code}")
            return {"created": []}

    except Exception as e:
        print(f"Entity creation failed: {e}")
        return {"created": []}


def generate_entities_for_focus(focus):
    """Generate relevant entities based on focus area"""
    focus_entities = {
        "reasoning_enhancement": [
            {"name": "deductive_chain_optimization", "entityType": "reasoning_pattern",
             "observations": ["Optimizes multi-step logical inference chains"]},
            {"name": "abductive_hypothesis_generation", "entityType": "reasoning_pattern",
             "observations": ["Improves best explanation inference"]}
        ],
        "memory_optimization": [
            {"name": "episodic_compression", "entityType": "memory_technique",
             "observations": ["Compress episodic memories efficiently"]},
            {"name": "semantic_retrieval_optimization", "entityType": "memory_technique",
             "observations": ["Faster semantic memory access"]}
        ],
        "causal_reasoning": [
            {"name": "intervention_reasoning", "entityType": "causal_pattern",
             "observations": ["Reason about causal interventions"]},
            {"name": "counterfactual_inference", "entityType": "causal_pattern",
             "observations": ["What-if scenario reasoning"]}
        ],
        "pattern_recognition": [
            {"name": "temporal_pattern_detection", "entityType": "pattern_technique",
             "observations": ["Detect patterns across time"]},
            {"name": "cross_domain_pattern_matching", "entityType": "pattern_technique",
             "observations": ["Match patterns across domains"]}
        ],
        "meta_cognition": [
            {"name": "uncertainty_calibration", "entityType": "meta_skill",
             "observations": ["Better uncertainty estimation"]},
            {"name": "knowledge_gap_detection", "entityType": "meta_skill",
             "observations": ["Identify what we don't know"]}
        ],
        "knowledge_integration": [
            {"name": "cross_domain_synthesis", "entityType": "integration_pattern",
             "observations": ["Combine knowledge across fields"]},
            {"name": "analogy_transfer", "entityType": "integration_pattern",
             "observations": ["Transfer knowledge via analogy"]}
        ],
        "planning_improvement": [
            {"name": "hierarchical_planning", "entityType": "planning_pattern",
             "observations": ["Multi-level goal decomposition"]},
            {"name": "adaptive_replanning", "entityType": "planning_pattern",
             "observations": ["Adjust plans based on feedback"]}
        ],
        "learning_efficiency": [
            {"name": "few_shot_learning", "entityType": "learning_pattern",
             "observations": ["Learn from minimal examples"]},
            {"name": "curriculum_learning", "entityType": "learning_pattern",
             "observations": ["Progressive difficulty learning"]}
        ]
    }

    return focus_entities.get(focus["name"], [])


def build_knowledge_connections(entities):
    """Build causal links and associations for new entities"""
    # Use "results" list (which contains entity details with IDs)
    created = entities.get("results", [])
    if not created:
        return {"causal_links": 0, "associations": 0}

    causal_links = 0
    associations = 0

    try:
        # Create causal links between entities
        for i, entity in enumerate(created[:-1]):
            response = requests.post(
                "http://localhost:8101/create_causal_link",
                json={
                    "cause_entity_id": entity.get("id"),
                    "effect_entity_id": created[i + 1].get("id"),
                    "strength": 0.7,
                    "relationship_type": "direct"
                },
                timeout=10
            )
            if response.status_code == 200:
                causal_links += 1

        # Create associations
        if len(created) >= 2:
            response = requests.post(
                "http://localhost:8101/create_association",
                json={
                    "entity_a_id": created[0].get("id"),
                    "entity_b_id": created[-1].get("id"),
                    "association_type": "semantic",
                    "association_strength": 0.6
                },
                timeout=10
            )
            if response.status_code == 200:
                associations += 1

    except Exception as e:
        print(f"Connection building failed: {e}")

    return {"causal_links": causal_links, "associations": associations}


def update_config(cycle_number, results):
    """Update AGI config with cycle results"""
    try:
        import yaml

        with open(_CONFIG_PATH) as f:
            config = yaml.safe_load(f)

        config["metrics"]["improvement_cycles"] = cycle_number
        config["metrics"][f"cycle_{cycle_number}_timestamp"] = datetime.now().isoformat()

        with open(_CONFIG_PATH, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"Config updated: cycle {cycle_number}")

    except Exception as e:
        print(f"Config update failed: {e}")


def notify_cycle_complete(results):
    """Send voice notification about cycle completion"""
    try:
        message = f"Improvement cycle {results.get('cycle_number', '?')} complete. "
        message += f"Created {results['entities_created']} entities, "
        message += f"{results['causal_links']} causal links."

        print(f"NOTIFICATION: {message}")

        # Would use voice-mode MCP in production
        return True
    except Exception as e:
        print(f"Notification failed: {e}")
        return False
