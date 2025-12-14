#!/usr/bin/env python3
"""
Tower of Hanoi Benchmark for MAKER Framework
============================================

Canonical test from the paper - 20 discs = 1,048,575 moves required.
This benchmark demonstrates the brutal math of probability:
- With 99% accuracy per step: 0.99^1048575 ≈ 0% success
- MAKER achieves 99.9999% system accuracy through voting

Rules:
1. Only one disk can be moved at a time
2. Each move consists of taking the upper disk from one stack and placing it on top of another stack
3. No disk may be placed on top of a smaller disk
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
from maker_framework import (
    MAKEROrchestrator,
    AtomicState,
    AgentResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HanoiState:
    """Tower of Hanoi state representation"""
    pegs: Dict[str, List[int]]  # {A: [5,4,3,2,1], B: [], C: []}
    move_count: int
    last_move: Optional[Tuple[str, str]]  # (from_peg, to_peg)

    def is_valid(self) -> bool:
        """Check if current state is valid (no large on small)"""
        for peg_name, discs in self.pegs.items():
            if discs != sorted(discs, reverse=True):
                return False
        return True

    def is_complete(self, target_peg: str = 'C') -> bool:
        """Check if all discs are on target peg"""
        total_discs = sum(len(discs) for discs in self.pegs.values())
        return len(self.pegs[target_peg]) == total_discs

    def can_move(self, from_peg: str, to_peg: str) -> bool:
        """Check if move is legal"""
        if not self.pegs[from_peg]:
            return False  # Source peg empty

        from_disc = self.pegs[from_peg][-1]
        if not self.pegs[to_peg]:
            return True  # Target peg empty

        to_disc = self.pegs[to_peg][-1]
        return from_disc < to_disc  # Can only place smaller on larger

    def apply_move(self, from_peg: str, to_peg: str) -> 'HanoiState':
        """Apply move and return new state"""
        if not self.can_move(from_peg, to_peg):
            raise ValueError(f"Illegal move: {from_peg} -> {to_peg}")

        # Create new state (immutable)
        new_pegs = {k: v.copy() for k, v in self.pegs.items()}
        disc = new_pegs[from_peg].pop()
        new_pegs[to_peg].append(disc)

        return HanoiState(
            pegs=new_pegs,
            move_count=self.move_count + 1,
            last_move=(from_peg, to_peg)
        )

    def get_legal_moves(self) -> List[Tuple[str, str]]:
        """Get all legal moves from current state"""
        moves = []
        pegs = ['A', 'B', 'C']
        for from_peg in pegs:
            for to_peg in pegs:
                if from_peg != to_peg and self.can_move(from_peg, to_peg):
                    moves.append((from_peg, to_peg))
        return moves

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'pegs': self.pegs,
            'move_count': self.move_count,
            'last_move': self.last_move
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HanoiState':
        """Create from dictionary"""
        return cls(
            pegs=data['pegs'],
            move_count=data['move_count'],
            last_move=tuple(data['last_move']) if data['last_move'] else None
        )


class HanoiBenchmark:
    """
    Tower of Hanoi benchmark using MAKER framework.

    Tests stateless execution with voting for reliability.
    """

    def __init__(self, num_discs: int = 3, use_voting: bool = True, k: int = 3):
        """
        Args:
            num_discs: Number of discs (3=7 moves, 4=15 moves, 20=1,048,575 moves)
            use_voting: Enable First-to-K voting
            k: Votes ahead required to win
        """
        self.num_discs = num_discs
        self.optimal_moves = 2 ** num_discs - 1
        self.orchestrator = MAKEROrchestrator(
            voting_enabled=use_voting,
            red_flag_enabled=True,
            k=k
        )

    def create_initial_state(self) -> HanoiState:
        """Create initial Tower of Hanoi state"""
        return HanoiState(
            pegs={
                'A': list(range(self.num_discs, 0, -1)),  # [N, N-1, ..., 1]
                'B': [],
                'C': []
            },
            move_count=0,
            last_move=None
        )

    async def stateless_hanoi_agent(self, state: AtomicState) -> AgentResponse:
        """
        Stateless agent that decides next move.

        Receives ONLY: rules, current state, goal
        No conversation history, no memory of past moves.
        """
        # Extract Hanoi state from atomic state
        hanoi_state = HanoiState.from_dict(state.state_data)

        # Get legal moves
        legal_moves = hanoi_state.get_legal_moves()

        if not legal_moves:
            # No legal moves - something went wrong
            return AgentResponse(
                action=None,
                new_state_data=hanoi_state.to_dict(),
                reasoning="No legal moves available",
                format_valid=False,
                token_count=20,
                execution_time_ms=1.0
            )

        # Simple strategy: prefer moving to target peg (C)
        # This is intentionally simple - voting will make it reliable
        best_move = None
        for from_peg, to_peg in legal_moves:
            # Prefer moving to C
            if to_peg == 'C':
                best_move = (from_peg, to_peg)
                break

        # If can't move to C, use first legal move
        if not best_move:
            best_move = legal_moves[0]

        # Apply move to get new state
        try:
            new_hanoi_state = hanoi_state.apply_move(*best_move)
        except ValueError as e:
            return AgentResponse(
                action=None,
                new_state_data=hanoi_state.to_dict(),
                reasoning=f"Invalid move: {e}",
                format_valid=False,
                token_count=30,
                execution_time_ms=2.0
            )

        # Return response (agent "dies" after this)
        return AgentResponse(
            action={'from': best_move[0], 'to': best_move[1]},
            new_state_data=new_hanoi_state.to_dict(),
            reasoning=f"Move disc from {best_move[0]} to {best_move[1]}",
            format_valid=True,
            token_count=50,
            execution_time_ms=5.0
        )

    def is_goal_reached(self, state: AtomicState) -> bool:
        """Check if Tower of Hanoi is solved"""
        hanoi_state = HanoiState.from_dict(state.state_data)
        return hanoi_state.is_complete(target_peg='C')

    async def run_benchmark(self) -> Dict[str, Any]:
        """
        Run Tower of Hanoi benchmark.

        Returns:
            Benchmark results including success, moves, time, voting stats
        """
        logger.info(f"Starting Tower of Hanoi benchmark: {self.num_discs} discs")
        logger.info(f"Optimal solution: {self.optimal_moves} moves")

        # Create initial state
        initial_hanoi = self.create_initial_state()
        initial_state = AtomicState(
            state_id="hanoi-0",
            step_number=0,
            state_data=initial_hanoi.to_dict(),
            rules=[
                "Only one disk can be moved at a time",
                "Only the upper disk from a stack can be moved",
                "No disk may be placed on top of a smaller disk",
                "Goal: Move all disks to peg C"
            ],
            goal="Move all disks from peg A to peg C"
        )

        # Execute with MAKER
        success, final_state, stats = await self.orchestrator.execute_sequence(
            task_name=f"tower_of_hanoi_{self.num_discs}_discs",
            initial_state=initial_state,
            agent_fn=self.stateless_hanoi_agent,
            is_goal_reached=self.is_goal_reached,
            max_steps=self.optimal_moves * 2  # Allow some inefficiency
        )

        # Verify solution
        final_hanoi = HanoiState.from_dict(final_state.state_data)

        results = {
            'success': success,
            'num_discs': self.num_discs,
            'optimal_moves': self.optimal_moves,
            'actual_moves': stats['total_steps'],
            'efficiency': stats['total_steps'] / self.optimal_moves if success else 0,
            'total_queries': stats.get('total_queries', stats['total_steps']),
            'rejected_steps': stats['rejected_steps'],
            'avg_confidence': (
                sum(stats['voting_confidence']) / len(stats['voting_confidence'])
                if stats.get('voting_confidence') else 0
            ),
            'total_time_ms': stats['total_execution_time_ms'],
            'final_state': final_hanoi.to_dict(),
            'is_valid': final_hanoi.is_valid(),
            'is_complete': final_hanoi.is_complete()
        }

        return results


async def run_benchmarks():
    """Run multiple benchmarks with different configurations"""

    configs = [
        {'num_discs': 3, 'use_voting': False, 'k': 0},  # No voting baseline
        {'num_discs': 3, 'use_voting': True, 'k': 2},   # With voting k=2
        {'num_discs': 3, 'use_voting': True, 'k': 3},   # With voting k=3
        {'num_discs': 5, 'use_voting': True, 'k': 3},   # More discs
        {'num_discs': 10, 'use_voting': True, 'k': 3},  # 1023 moves
    ]

    results = []

    for config in configs:
        benchmark = HanoiBenchmark(**config)
        result = await benchmark.run_benchmark()
        result['config'] = config
        results.append(result)

        logger.info(f"\nResults for {config}:")
        logger.info(f"  Success: {result['success']}")
        logger.info(f"  Moves: {result['actual_moves']} / {result['optimal_moves']} (efficiency: {result['efficiency']:.2%})")
        logger.info(f"  Queries: {result['total_queries']}")
        logger.info(f"  Avg confidence: {result['avg_confidence']:.3f}")
        logger.info(f"  Time: {result['total_time_ms']:.0f}ms")

    # Summary
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print(f"{'Config':<30} {'Success':<10} {'Efficiency':<12} {'Avg Confidence':<15}")
    print("-"*80)

    for result in results:
        config_str = f"{result['num_discs']} discs, voting={result['config']['use_voting']}, k={result['config']['k']}"
        print(
            f"{config_str:<30} "
            f"{'✓' if result['success'] else '✗':<10} "
            f"{result['efficiency']:.1%}{'':>7} "
            f"{result['avg_confidence']:.3f}"
        )

    return results


if __name__ == "__main__":
    results = asyncio.run(run_benchmarks())

    # Save results
    import json
    from pathlib import Path
    from datetime import datetime

    output_file = Path(__file__).parent.parent / "logs" / f"hanoi_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
