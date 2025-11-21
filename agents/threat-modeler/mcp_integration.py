#!/usr/bin/env python3
"""
MCP Integration for Threat Modeler
Stores threat models in enhanced-memory-mcp for cross-agent access
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class ThreatModelMCPIntegration:
    """
    Integrates threat modeler with enhanced-memory-mcp
    Stores and retrieves threat models for the autonomous security system
    """

    def __init__(self):
        self.entity_type = "security_threat_model"

    def threat_model_to_memory_entity(self, threat_model_path: str) -> Dict:
        """
        Convert threat model JSON to enhanced-memory entity format
        """
        with open(threat_model_path) as f:
            threat_model = json.load(f)

        # Extract key information for observations
        observations = []

        # Basic metadata
        observations.append(f"repository: {threat_model['repository_path']}")
        observations.append(f"model_id: {threat_model['model_id']}")
        observations.append(f"timestamp: {threat_model['timestamp']}")

        # Security objectives
        for obj in threat_model['security_objectives']:
            observations.append(
                f"security_objective: [{obj['priority']}] {obj['description']} "
                f"(category: {obj['category']})"
            )

        # Attack surface summary
        attack_surface_summary = {}
        for component in threat_model['attack_surface']:
            comp_type = component['type']
            attack_surface_summary[comp_type] = attack_surface_summary.get(comp_type, 0) + 1

        for comp_type, count in attack_surface_summary.items():
            observations.append(f"attack_surface_{comp_type}: {count} components")

        # Risk distribution
        for level, components in threat_model['risk_priorities'].items():
            observations.append(f"risk_{level}: {len(components)} components")

        # Create entity structure
        entity_name = f"threat-model-{Path(threat_model['repository_path']).name}"

        entity = {
            "name": entity_name,
            "entityType": self.entity_type,
            "observations": observations
        }

        # Store full threat model as JSON in a separate observation
        entity["observations"].append(
            f"full_model_json: {json.dumps(threat_model)}"
        )

        return entity

    def generate_mcp_command(self, threat_model_path: str) -> str:
        """
        Generate the MCP command to store threat model in enhanced-memory
        This will be executed by the orchestrator
        """
        entity = self.threat_model_to_memory_entity(threat_model_path)

        # Format for MCP tool call
        mcp_command = {
            "tool": "mcp__enhanced_memory__create_entities",
            "parameters": {
                "entities": [entity]
            }
        }

        return json.dumps(mcp_command, indent=2)

    def create_cli_script(self, threat_model_path: str, output_path: str = None):
        """
        Create a shell script that can be executed to store in MCP
        """
        if output_path is None:
            output_path = Path(threat_model_path).parent / "store_in_memory.sh"

        entity = self.threat_model_to_memory_entity(threat_model_path)

        # Create Python script that uses MCP
        script_content = f"""#!/usr/bin/env python3
# Auto-generated MCP storage script for threat model
# Generated: {datetime.now().isoformat()}

import json

# Threat model entity for enhanced-memory
entity = {json.dumps(entity, indent=4)}

# This would be called via MCP in the orchestrator:
# mcp__enhanced_memory__create_entities([entity])

print("Threat model entity prepared for enhanced-memory storage:")
print(json.dumps(entity, indent=2))
print()
print("To store in enhanced-memory, use this entity in the orchestrator's MCP call.")
"""

        with open(output_path, 'w') as f:
            f.write(script_content)

        import os
        os.chmod(output_path, 0o755)

        return output_path


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python mcp_integration.py <threat_model.json> [output_script]")
        sys.exit(1)

    threat_model_path = sys.argv[1]
    output_script = sys.argv[2] if len(sys.argv) > 2 else None

    print("="*70)
    print("THREAT MODEL → ENHANCED MEMORY MCP INTEGRATION")
    print("="*70)
    print()

    integrator = ThreatModelMCPIntegration()

    # Generate entity
    entity = integrator.threat_model_to_memory_entity(threat_model_path)
    print(f"[+] Generated memory entity: {entity['name']}")
    print(f"    Entity type: {entity['entityType']}")
    print(f"    Observations: {len(entity['observations'])}")
    print()

    # Generate MCP command
    mcp_command = integrator.generate_mcp_command(threat_model_path)
    print("[+] MCP Command:")
    print(mcp_command)
    print()

    # Create CLI script
    script_path = integrator.create_cli_script(threat_model_path, output_script)
    print(f"[+] MCP storage script created: {script_path}")
    print()

    print("[✓] Ready for enhanced-memory integration!")
    print()
    print("Next steps:")
    print("  1. Review the generated entity structure above")
    print(f"  2. Execute: {script_path}")
    print("  3. Or use the MCP command in the orchestrator")


if __name__ == "__main__":
    main()
