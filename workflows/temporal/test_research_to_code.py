#!/usr/bin/env python3
"""
Quick Test for Research-to-Code Pipeline
=========================================

Tests the pipeline activities directly without requiring Temporal.
Useful for rapid iteration and validation.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add workflow path
sys.path.insert(0, str(Path(__file__).parent))

from research_to_code_pipeline import (
    search_papers_parallel,
    extract_paper_knowledge,
    build_knowledge_graph,
    extract_code_patterns,
    generate_architecture_plan,
    generate_module_code,
    generate_tests,
    validate_generated_code,
    store_implementation
)


async def test_pipeline(query: str, output_dir: str = None):
    """Run the full pipeline without Temporal orchestration"""

    print(f"\n{'='*60}")
    print(f"Research-to-Code Pipeline Test")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    output_dir = output_dir or f"/mnt/agentic-system/generated-implementations/test_{query.replace(' ', '_')[:20]}"

    results = {"query": query, "stages": {}, "timing": {}}

    # Stage 1: Research Acquisition
    print("\n[1/5] RESEARCH ACQUISITION...")
    start = datetime.now()

    # Use activity functions directly (they're async)
    papers = await search_papers_parallel(query, 5)
    print(f"  Found {len(papers)} papers")

    # Extract knowledge
    papers_knowledge = []
    for paper in papers[:3]:  # Limit for speed
        pk = await extract_paper_knowledge(paper)
        papers_knowledge.append(pk)
        print(f"  Extracted: {pk.get('title', '')[:50]}...")

    results["stages"]["research"] = {"papers": len(papers), "knowledge": len(papers_knowledge)}
    results["timing"]["research"] = (datetime.now() - start).total_seconds()
    print(f"  Completed in {results['timing']['research']:.1f}s")

    # Stage 2: Knowledge Graph
    print("\n[2/5] KNOWLEDGE GRAPH CONSTRUCTION...")
    start = datetime.now()

    knowledge_graph = await build_knowledge_graph(papers_knowledge)
    print(f"  Nodes: {len(knowledge_graph.get('nodes', []))}")
    print(f"  Edges: {len(knowledge_graph.get('edges', []))}")

    code_patterns = await extract_code_patterns(knowledge_graph)
    print(f"  Code patterns: {len(code_patterns)}")

    results["stages"]["knowledge_graph"] = {
        "nodes": len(knowledge_graph.get("nodes", [])),
        "patterns": len(code_patterns)
    }
    results["timing"]["knowledge_graph"] = (datetime.now() - start).total_seconds()
    print(f"  Completed in {results['timing']['knowledge_graph']:.1f}s")

    # Stage 3: Planning
    print("\n[3/5] ARCHITECTURE PLANNING...")
    start = datetime.now()

    architecture_plan = await generate_architecture_plan(knowledge_graph, code_patterns)
    print(f"  Modules planned: {len(architecture_plan.get('modules', []))}")
    print(f"  Dependencies: {architecture_plan.get('dependencies', [])}")

    results["stages"]["planning"] = {"modules": len(architecture_plan.get("modules", []))}
    results["timing"]["planning"] = (datetime.now() - start).total_seconds()
    print(f"  Completed in {results['timing']['planning']:.1f}s")

    # Stage 4: Code Generation
    print("\n[4/5] CODE GENERATION...")
    start = datetime.now()

    generated_modules = []
    for module in architecture_plan.get("modules", []):
        gen = await generate_module_code(module, architecture_plan, True)
        generated_modules.append(gen)
        print(f"  Generated: {gen.get('module_name')} ({len(gen.get('content', ''))} chars)")

    generated_tests = []
    for module in generated_modules:
        test = await generate_tests(module)
        generated_tests.append(test)

    print(f"  Tests generated: {len(generated_tests)}")

    results["stages"]["code_generation"] = {
        "modules": len(generated_modules),
        "tests": len(generated_tests)
    }
    results["timing"]["code_generation"] = (datetime.now() - start).total_seconds()
    print(f"  Completed in {results['timing']['code_generation']:.1f}s")

    # Stage 5: Validation
    print("\n[5/5] VALIDATION & STORAGE...")
    start = datetime.now()

    validation = await validate_generated_code(generated_modules, architecture_plan)
    print(f"  Validation score: {validation.get('score', 0):.2f}")
    print(f"  Passed: {validation.get('passed', False)}")

    if validation.get("issues"):
        print(f"  Issues: {validation['issues'][:3]}")
    if validation.get("suggestions"):
        print(f"  Suggestions: {validation['suggestions'][:3]}")

    storage = await store_implementation(
        output_dir,
        architecture_plan,
        generated_modules,
        generated_tests,
        validation
    )
    print(f"  Files written: {storage.get('total_files', 0)}")
    print(f"  Output: {storage.get('output_dir', '')}")

    results["stages"]["validation"] = validation
    results["output"] = storage
    results["timing"]["validation"] = (datetime.now() - start).total_seconds()
    print(f"  Completed in {results['timing']['validation']:.1f}s")

    # Summary
    total_time = sum(results["timing"].values())
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Papers analyzed: {len(papers_knowledge)}")
    print(f"Modules generated: {len(generated_modules)}")
    print(f"Validation score: {validation.get('score', 0):.2f}")
    print(f"Output directory: {storage.get('output_dir', '')}")
    print(f"{'='*60}\n")

    return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test Research-to-Code Pipeline")
    parser.add_argument("query", nargs="?", default="transformer attention mechanism",
                        help="Research query to implement")
    parser.add_argument("--output", "-o", type=str, help="Output directory")

    args = parser.parse_args()

    result = await test_pipeline(args.query, args.output)

    # Save results
    output_dir = result.get("output", {}).get("output_dir", "/tmp")
    results_path = Path(output_dir) / "pipeline_results.json"
    results_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    asyncio.run(main())
