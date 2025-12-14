#!/usr/bin/env python3
"""
Run MAKER Tower of Hanoi Benchmark with Diverse AI Providers

Tests MAKER voting with:
- Claude Haiku (40%)
- Codex (30%)
- Gemini (20%)
- Ollama Cloud (10%)
"""

import asyncio
import json
from maker_framework import MAKEROrchestrator, AtomicState, AgentResponse
from maker_headless_providers import HeadlessMultiProvider, AIProvider


class HanoiState:
    """Tower of Hanoi game state"""
    def __init__(self, num_discs: int):
        self.num_discs = num_discs
        self.pegs = {
            'A': list(range(num_discs, 0, -1)),  # [3, 2, 1] for 3 discs
            'B': [],
            'C': []
        }
        self.move_count = 0

    def to_dict(self):
        return {
            'pegs': self.pegs.copy(),
            'num_discs': self.num_discs,
            'move_count': self.move_count
        }

    def is_solved(self):
        """Check if all discs are on peg C"""
        return len(self.pegs['C']) == self.num_discs

    def apply_move(self, move):
        """Apply a move (from_peg, to_peg)"""
        if isinstance(move, dict):
            from_peg = move.get('from')
            to_peg = move.get('to')
        elif isinstance(move, (list, tuple)) and len(move) == 2:
            from_peg, to_peg = move
        else:
            return False

        if not from_peg or not to_peg:
            return False

        # Validate move
        if not self.pegs.get(from_peg):
            return False

        disc = self.pegs[from_peg][-1]
        if self.pegs.get(to_peg) and self.pegs[to_peg] and self.pegs[to_peg][-1] < disc:
            return False  # Can't place larger disc on smaller

        # Execute move
        self.pegs[from_peg].pop()
        self.pegs.setdefault(to_peg, []).append(disc)
        self.move_count += 1
        return True


async def create_diverse_hanoi_agent(provider_executor: HeadlessMultiProvider):
    """
    Create a MAKER agent function that rotates through diverse providers.

    Each call will use a different provider from the distribution.
    """
    # Get provider distribution for multiple queries
    provider_cycle = provider_executor.get_provider_distribution(20)
    current_index = [0]  # Mutable to modify in closure

    async def hanoi_agent(state: AtomicState) -> AgentResponse:
        """Stateless Hanoi agent using rotating providers"""

        # Get next provider from cycle
        provider = provider_cycle[current_index[0] % len(provider_cycle)]
        current_index[0] += 1

        try:
            # Execute with specific provider
            response = await provider_executor.execute_with_provider(provider, state)
            return response
        except Exception as e:
            # Fallback to Codex if provider fails
            print(f"Warning: {provider.value} failed, using Codex fallback")
            return await provider_executor.execute_with_provider(AIProvider.CODEX, state)

    return hanoi_agent


async def run_benchmark_with_voting(num_discs: int = 3):
    """Run Tower of Hanoi with multi-provider voting"""
    print(f"\n{'='*80}")
    print(f"🎯 MAKER Tower of Hanoi Benchmark: {num_discs} discs")
    print(f"{'='*80}\n")

    # Initialize
    hanoi = HanoiState(num_discs)
    provider_executor = HeadlessMultiProvider()

    # Create orchestrator with voting
    orchestrator = MAKEROrchestrator(
        voting_enabled=True,
        k=2,  # K=2 for faster voting
        red_flag_enabled=True
    )

    # Create diverse agent
    agent_fn = await create_diverse_hanoi_agent(provider_executor)

    # Initial state
    initial_state = AtomicState(
        state_id=f"hanoi-{num_discs}-0",
        step_number=0,
        state_data=hanoi.to_dict(),
        rules=[
            "Only move one disc at a time",
            "Never place a larger disc on a smaller disc",
            "Move from peg X to peg Y",
            "Return action as: {'from': 'X', 'to': 'Y'}"
        ],
        goal=f"Move all {num_discs} discs from peg A to peg C"
    )

    # Goal check
    def is_goal_reached(state: AtomicState) -> bool:
        return len(state.state_data['pegs']['C']) == num_discs

    # Execute
    print("🚀 Starting MAKER execution with diverse AI providers...")
    print(f"   Voting: K=2, Providers: Claude(40%), Codex(30%), Gemini(20%), Ollama(10%)\n")

    success, final_state, stats = await orchestrator.execute_sequence(
        task_name=f"hanoi_{num_discs}_discs_diverse",
        initial_state=initial_state,
        agent_fn=agent_fn,
        is_goal_reached=is_goal_reached,
        max_steps=2 ** num_discs - 1 + 10  # Optimal + buffer
    )

    # Results
    print(f"\n{'='*80}")
    print("📊 BENCHMARK RESULTS")
    print(f"{'='*80}")
    print(f"Success: {'✅ YES' if success else '❌ NO'}")
    print(f"Moves: {stats['total_steps']}")
    print(f"Optimal: {2**num_discs - 1}")
    print(f"Efficiency: {(2**num_discs - 1) / stats['total_steps'] * 100:.1f}%")

    if stats.get('voting_confidence'):
        avg_confidence = sum(stats['voting_confidence']) / len(stats['voting_confidence'])
        print(f"Avg Voting Confidence: {avg_confidence:.4f}")

    print(f"Total Queries: {stats.get('total_queries', 0)}")
    print(f"{'='*80}\n")

    return success


async def main():
    """Run benchmarks with diverse providers"""
    print("\n🎮 MAKER Framework - Multi-Provider Voting Test")
    print("=" * 80)
    print("Testing diverse AI providers:")
    print("  • Claude Code Haiku (40%)")
    print("  • OpenAI Codex (30%)")
    print("  • Gemini CLI (20%)")
    print("  • Ollama Cloud gpt-oss:20b-cloud (10%)")
    print("=" * 80)

    # Test with 3 discs first
    await run_benchmark_with_voting(num_discs=3)


if __name__ == "__main__":
    asyncio.run(main())
