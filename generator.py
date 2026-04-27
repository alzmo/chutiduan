"""Minimal candidate level generator.

This module only generates level data for downstream solver consumption.
It does NOT perform solvability checks or difficulty analysis.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

BOARD_SIZE = 8
CELL_COUNT = BOARD_SIZE * BOARD_SIZE


@dataclass(frozen=True)
class LevelGeneratorConfig:
    """Configuration for level generation."""

    color_count: int
    max_stack_height: int
    target_block_count: int


class LevelGenerationError(ValueError):
    """Raised when level parameters cannot produce a valid level."""


def build_level_id(index: int) -> str:
    """Create a normalized level id, e.g. LEVEL_0001."""
    if index <= 0:
        raise ValueError("index must be positive")
    return f"LEVEL_{index:04d}"


def generate_level(
    level_id: str,
    color_count: int,
    max_stack_height: int,
    target_block_count: int,
    *,
    seed: Optional[int] = None,
    max_attempts: int = 200,
) -> Dict:
    """Generate a candidate level.

    Public interface required by the task.

    Args:
        level_id: Unique level id (e.g. LEVEL_0001).
        color_count: Number of color types (COLOR_1...COLOR_N).
        max_stack_height: Max layers per cell.
        target_block_count: Desired total block count.
        seed: Optional random seed for reproducibility.
        max_attempts: Retry count to avoid illegal output.

    Returns:
        A dict containing id, size, blocks, basketSequence.

    Raises:
        LevelGenerationError: If params are infeasible or retries are exhausted.
    """
    cfg = LevelGeneratorConfig(
        color_count=color_count,
        max_stack_height=max_stack_height,
        target_block_count=target_block_count,
    )
    _validate_config(cfg)

    rng = random.Random(seed)
    feasible_total = _normalize_total_block_count(cfg)

    for _ in range(max_attempts):
        heights = _random_heights(
            total_blocks=feasible_total,
            max_stack_height=cfg.max_stack_height,
            rng=rng,
        )
        color_counts = _random_color_counts(
            total_blocks=feasible_total,
            color_count=cfg.color_count,
            rng=rng,
        )
        level = _assemble_level(
            level_id=level_id,
            heights=heights,
            color_counts=color_counts,
            rng=rng,
        )
        ok, reason = validate_generated_level(level)
        if ok:
            return level

    raise LevelGenerationError(
        f"failed to generate valid level after {max_attempts} attempts; last reason: {reason}"
    )


def validate_generated_level(level: Dict) -> Tuple[bool, str]:
    """Sanity checks required by the task constraints."""
    if level.get("size") != BOARD_SIZE:
        return False, "size must be 8"

    blocks = level.get("blocks", [])
    basket = level.get("basketSequence", [])

    # 1) layer continuity per cell
    cell_layers: Dict[int, List[int]] = {}
    color_counter: Counter = Counter()
    for b in blocks:
        cell = b["cellId"]
        layer = b["layer"]
        color = b["color"]

        if not (1 <= cell <= CELL_COUNT):
            return False, f"invalid cellId {cell}"
        if layer < 1:
            return False, f"invalid layer {layer}"

        cell_layers.setdefault(cell, []).append(layer)
        color_counter[color] += 1

    for cell, layers in cell_layers.items():
        sorted_layers = sorted(layers)
        expected = list(range(1, len(sorted_layers) + 1))
        if sorted_layers != expected:
            return False, f"non-continuous layers at cell {cell}: {sorted_layers}"

    # 2) color counts must be multiples of 3
    for color, count in color_counter.items():
        if count % 3 != 0:
            return False, f"{color} count {count} is not divisible by 3"

    # 3) basketSequence counts must equal color_count / 3
    basket_counter = Counter(basket)
    for color, count in color_counter.items():
        if basket_counter[color] != count // 3:
            return (
                False,
                f"basket count mismatch for {color}: {basket_counter[color]} != {count // 3}",
            )

    # no extra color in basketSequence
    for color in basket_counter:
        if color not in color_counter and basket_counter[color] != 0:
            return False, f"basket has unknown color {color}"

    return True, "ok"


def _validate_config(cfg: LevelGeneratorConfig) -> None:
    if cfg.color_count <= 0:
        raise LevelGenerationError("color_count must be > 0")
    if cfg.max_stack_height <= 0:
        raise LevelGenerationError("max_stack_height must be > 0")
    if cfg.target_block_count < 0:
        raise LevelGenerationError("target_block_count must be >= 0")

    capacity = CELL_COUNT * cfg.max_stack_height
    if capacity < 3:
        raise LevelGenerationError("board capacity is too small to place valid color triples")


def _normalize_total_block_count(cfg: LevelGeneratorConfig) -> int:
    """Choose a feasible total block count close to target.

    Requirements:
    - cannot exceed board capacity
    - must be divisible by 3 (sum of color counts)
    """
    capacity = CELL_COUNT * cfg.max_stack_height
    total = min(cfg.target_block_count, capacity)
    total -= total % 3

    if total == 0 and cfg.target_block_count > 0 and capacity >= 3:
        total = 3

    if total > capacity:
        raise LevelGenerationError("normalized total exceeds capacity")

    if total % 3 != 0:
        raise LevelGenerationError("cannot normalize to a multiple of 3")

    return total


def _random_heights(total_blocks: int, max_stack_height: int, rng: random.Random) -> List[int]:
    heights = [0] * CELL_COUNT
    remaining = total_blocks

    # Randomly drop blocks into cells while respecting max height.
    # This guarantees each occupied cell has layers 1..height.
    available_cells = list(range(CELL_COUNT))
    while remaining > 0:
        if not available_cells:
            raise LevelGenerationError("no available cells left while blocks remain")
        idx = rng.choice(available_cells)
        heights[idx] += 1
        remaining -= 1
        if heights[idx] >= max_stack_height:
            available_cells.remove(idx)

    return heights


def _random_color_counts(total_blocks: int, color_count: int, rng: random.Random) -> Dict[str, int]:
    """Randomly assign colors; every color count is a multiple of 3."""
    triple_units = total_blocks // 3
    units = [0] * color_count
    for _ in range(triple_units):
        units[rng.randrange(color_count)] += 1

    return {f"COLOR_{i + 1}": units[i] * 3 for i in range(color_count)}


def _assemble_level(
    level_id: str,
    heights: List[int],
    color_counts: Dict[str, int],
    rng: random.Random,
) -> Dict:
    color_pool: List[str] = []
    for color, count in color_counts.items():
        color_pool.extend([color] * count)
    rng.shuffle(color_pool)

    blocks: List[Dict] = []
    ptr = 0
    for cell_idx, height in enumerate(heights):
        cell_id = cell_idx + 1
        for layer in range(1, height + 1):
            blocks.append(
                {
                    "code": f"{cell_id}.{layer}.{color_pool[ptr]}",
                    "cellId": cell_id,
                    "layer": layer,
                    "color": color_pool[ptr],
                }
            )
            ptr += 1

    # Keep output stable/readable: sort by cellId then layer.
    blocks.sort(key=lambda b: (b["cellId"], b["layer"]))

    basket_sequence: List[str] = []
    for color, count in color_counts.items():
        basket_sequence.extend([color] * (count // 3))
    rng.shuffle(basket_sequence)

    return {
        "id": level_id,
        "size": BOARD_SIZE,
        "blocks": blocks,
        "basketSequence": basket_sequence,
    }


if __name__ == "__main__":
    # Simple demo entry: generate and print one sample level.
    sample = generate_level(
        level_id=build_level_id(1),
        color_count=6,
        max_stack_height=4,
        target_block_count=72,
        seed=42,
    )
    ok, msg = validate_generated_level(sample)
    print(json.dumps(sample, ensure_ascii=False, indent=2))
    print(f"\nvalidation: {ok} ({msg})")
