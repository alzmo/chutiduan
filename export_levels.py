"""Batch-export candidate levels as JSON files for solver-side consumption."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from generator import build_level_id, generate_level, validate_generated_level

# Export parameters (edit directly if needed)
LEVEL_COUNT = 10
COLOR_COUNT = 6
MAX_STACK_HEIGHT = 4
TARGET_BLOCK_COUNT = 72
OUTPUT_DIR = Path("levels")
MAX_GENERATION_ATTEMPTS_PER_LEVEL = 50


def _build_file_name(index: int) -> str:
    return f"level_{index:04d}.json"


def _generate_valid_level(level_id: str) -> Dict:
    last_reason = "unknown"
    for _ in range(MAX_GENERATION_ATTEMPTS_PER_LEVEL):
        level = generate_level(
            level_id=level_id,
            color_count=COLOR_COUNT,
            max_stack_height=MAX_STACK_HEIGHT,
            target_block_count=TARGET_BLOCK_COUNT,
        )
        ok, reason = validate_generated_level(level)
        if ok:
            return level
        last_reason = reason

    raise RuntimeError(
        f"failed to generate a valid level for {level_id} after "
        f"{MAX_GENERATION_ATTEMPTS_PER_LEVEL} attempts; last reason: {last_reason}"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exported: List[Dict] = []

    for index in range(1, LEVEL_COUNT + 1):
        level_id = build_level_id(index)
        level = _generate_valid_level(level_id)

        file_name = _build_file_name(index)
        output_path = OUTPUT_DIR / file_name

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(level, f, ensure_ascii=False, indent=2)
            f.write("\n")

        exported.append(
            {
                "file_name": file_name,
                "level_id": level["id"],
                "blocks_count": len(level["blocks"]),
                "basket_length": len(level["basketSequence"]),
            }
        )

    print(f"Generated {len(exported)} levels")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")
    print("Level files:")
    for item in exported:
        print(
            f"- {item['file_name']} "
            f"(id={item['level_id']}, "
            f"blocks={item['blocks_count']}, "
            f"basketSequence={item['basket_length']})"
        )


if __name__ == "__main__":
    main()
