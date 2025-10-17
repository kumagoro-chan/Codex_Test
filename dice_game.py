#!/usr/bin/env python3
"""
Reproduce the dice game from "The Goal".

Each round:
  1. The first buffer receives `release_rate` units (raw material).
  2. Every stage rolls a die to determine its capacity.
  3. Actual output = min(available WIP, capacity); leftovers stay in the stage buffer.
Collect round-by-round history and aggregate statistics such as average throughput,
WIP, cycle time, and starved/blocked ratios per stage.
"""

from __future__ import annotations

import argparse
import random
import statistics
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StageOutcome:
    stage: int
    roll: int
    available: int
    processed: int
    buffer_after: int
    starved: bool
    blocked: bool


@dataclass
class RoundOutcome:
    round_index: int
    throughput: int
    wip: int
    stage_outcomes: List[StageOutcome]


@dataclass
class SimulationSummary:
    rounds: List[RoundOutcome]
    avg_throughput: float
    throughput_stdev: float
    avg_wip: float
    total_throughput: int
    stage_starved_ratio: List[float]
    stage_blocked_ratio: List[float]


class DiceGame:
    """Stateful simulator for the dice game pipeline."""

    def __init__(
        self,
        stages: int = 5,
        die_sides: int = 6,
        release_rate: int = 4,
        initial_buffer: int = 3,
        seed: Optional[int] = None,
    ) -> None:
        if stages < 1:
            raise ValueError("stages must be >= 1")
        if die_sides < 2:
            raise ValueError("die_sides must be >= 2")
        if release_rate < 0:
            raise ValueError("release_rate must be >= 0")
        if initial_buffer < 0:
            raise ValueError("initial_buffer must be >= 0")

        self.stages = stages
        self.die_sides = die_sides
        self.release_rate = release_rate
        self.buffers = [initial_buffer for _ in range(stages)]
        self.rng = random.Random(seed)

    def play_round(self, round_index: int) -> RoundOutcome:
        """Simulate one round and return its outcome."""

        self.buffers[0] += self.release_rate
        incoming = 0
        stage_outcomes: List[StageOutcome] = []

        for index in range(self.stages):
            available = self.buffers[index] + incoming
            roll = self.rng.randint(1, self.die_sides)
            processed = min(available, roll)
            buffer_after = available - processed
            starved = available < roll
            blocked = buffer_after > 0

            stage_outcomes.append(
                StageOutcome(
                    stage=index,
                    roll=roll,
                    available=available,
                    processed=processed,
                    buffer_after=buffer_after,
                    starved=starved,
                    blocked=blocked,
                )
            )

            self.buffers[index] = buffer_after
            incoming = processed

        throughput = incoming
        wip = sum(self.buffers)
        return RoundOutcome(
            round_index=round_index,
            throughput=throughput,
            wip=wip,
            stage_outcomes=stage_outcomes,
        )

    def simulate(self, rounds: int) -> SimulationSummary:
        """Run several rounds and aggregate statistics."""

        if rounds < 1:
            raise ValueError("rounds must be >= 1")

        history: List[RoundOutcome] = []
        for i in range(rounds):
            history.append(self.play_round(i + 1))

        throughput_series = [r.throughput for r in history]
        wip_series = [r.wip for r in history]

        avg_throughput = statistics.mean(throughput_series)
        throughput_stdev = (
            statistics.pstdev(throughput_series)
            if len(throughput_series) > 1
            else 0.0
        )
        avg_wip = statistics.mean(wip_series)
        total = sum(throughput_series)

        starved_counts = [0 for _ in range(self.stages)]
        blocked_counts = [0 for _ in range(self.stages)]
        for round_outcome in history:
            for stage_outcome in round_outcome.stage_outcomes:
                if stage_outcome.starved:
                    starved_counts[stage_outcome.stage] += 1
                if stage_outcome.blocked:
                    blocked_counts[stage_outcome.stage] += 1

        rounds_float = float(rounds)
        starved_ratio = [c / rounds_float for c in starved_counts]
        blocked_ratio = [c / rounds_float for c in blocked_counts]

        return SimulationSummary(
            rounds=history,
            avg_throughput=avg_throughput,
            throughput_stdev=throughput_stdev,
            avg_wip=avg_wip,
            total_throughput=total,
            stage_starved_ratio=starved_ratio,
            stage_blocked_ratio=blocked_ratio,
        )


def _print_verbose(prefix: str, summary: SimulationSummary) -> None:
    print(prefix)
    for round_outcome in summary.rounds:
        rolls = [s.roll for s in round_outcome.stage_outcomes]
        processed = [s.processed for s in round_outcome.stage_outcomes]
        buffers = [s.buffer_after for s in round_outcome.stage_outcomes]
        print(
            f"  Round {round_outcome.round_index:>2}: "
            f"throughput={round_outcome.throughput:>2} "
            f"WIP={round_outcome.wip:>3} "
            f"rolls={rolls} "
            f"out={processed} "
            f"buf={buffers}"
        )
    print()


def _print_summary(summaries: List[SimulationSummary]) -> None:
    reps = len(summaries)
    rounds = len(summaries[0].rounds)
    avg_throughputs = [s.avg_throughput for s in summaries]
    avg_wips = [s.avg_wip for s in summaries]
    totals = [s.total_throughput for s in summaries]

    overall_avg_throughput = statistics.mean(avg_throughputs)
    overall_avg_wip = statistics.mean(avg_wips)
    overall_total = statistics.mean(totals)
    throughput_sd_between = (
        statistics.pstdev(avg_throughputs) if reps > 1 else 0.0
    )
    cycle_time = (
        overall_avg_wip / overall_avg_throughput
        if overall_avg_throughput > 0
        else float("nan")
    )

    print("=== Dice Game Summary ===")
    print(f"Replications           : {reps}")
    print(f"Rounds per replication : {rounds}")
    print(f"Average throughput     : {overall_avg_throughput:.3f} / round")
    print(
        f"Throughput stdev (intra): "
        f"{statistics.mean(s.throughput_stdev for s in summaries):.3f}"
    )
    print(f"Throughput stdev (inter): {throughput_sd_between:.3f}")
    print(f"Average WIP            : {overall_avg_wip:.3f}")
    if overall_avg_throughput > 0:
        print(f"Average cycle time     : {cycle_time:.3f} rounds (Little's Law)")
    else:
        print("Average cycle time     : undefined (zero throughput)")
    print(f"Average total output   : {overall_total:.2f} units\n")

    stage_count = len(summaries[0].stage_starved_ratio)
    for stage in range(stage_count):
        starved = statistics.mean(s.stage_starved_ratio[stage] for s in summaries)
        blocked = statistics.mean(s.stage_blocked_ratio[stage] for s in summaries)
        print(
            f"Stage {stage + 1}: starved {starved * 100:5.1f}% | "
            f"blocked {blocked * 100:5.1f}%"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Simulate the dice game from "The Goal".'
    )
    parser.add_argument("--stages", type=int, default=5, help="number of stations")
    parser.add_argument("--rounds", type=int, default=20, help="rounds per replication")
    parser.add_argument("--die-sides", type=int, default=6, help="faces on the die")
    parser.add_argument(
        "--release-rate",
        type=int,
        default=4,
        help="raw units released to stage 1 each round",
    )
    parser.add_argument(
        "--initial-buffer",
        type=int,
        default=3,
        help="initial WIP per stage",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="base random seed (replications add index offset)",
    )
    parser.add_argument(
        "--replications",
        type=int,
        default=1,
        help="run multiple independent simulations",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print round-by-round details",
    )

    args = parser.parse_args()

    summaries: List[SimulationSummary] = []
    for rep in range(args.replications):
        seed = args.seed + rep if args.seed is not None else None
        game = DiceGame(
            stages=args.stages,
            die_sides=args.die_sides,
            release_rate=args.release_rate,
            initial_buffer=args.initial_buffer,
            seed=seed,
        )
        summary = game.simulate(args.rounds)
        summaries.append(summary)

        if args.verbose:
            prefix = f"--- Replication {rep + 1} ---"
            _print_verbose(prefix, summary)

    _print_summary(summaries)


if __name__ == "__main__":
    main()
