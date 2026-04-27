"""Generate candidate levels and export each as a JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from generator import build_level_id, generate_level, validate_generated_level

# Export parameters (edit directly if needed)
LEVEL_COUNT = 5
COLOR_COUNT = 3
MAX_STACK_HEIGHT = 2
TARGET_BLOCK_COUNT = 24
MAX_GENERATION_ATTEMPTS_PER_LEVEL = 50
LEVELS_DIR = Path("levels")


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
    LEVELS_DIR.mkdir(parents=True, exist_ok=True)
    exported: List[Dict] = []

    for index in range(1, LEVEL_COUNT + 1):
        level_id = build_level_id(index)
        level = _generate_valid_level(level_id)
        file_name = f"level_{index:04d}.json"
        file_path = LEVELS_DIR / file_name

        with file_path.open("w", encoding="utf-8") as output_file:
            json.dump(level, output_file, ensure_ascii=False, indent=2)

        exported.append(
            {
                "level_id": level["id"],
                "blocks_count": len(level["blocks"]),
                "basket_length": len(level["basketSequence"]),
                "file_name": file_name,
            }
        )

        print(f"===== {level['id']} =====")
        print(f"blocks: {len(level['blocks'])}")
        print(f"basketSequence: {len(level['basketSequence'])}")
        print(f"file: {file_name}")

    print(f"Generated {len(exported)} valid levels")


if __name__ == "__main__":
    main()
