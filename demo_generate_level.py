"""Very simple demo script for generator module."""

from generator import build_level_id, generate_level, validate_generated_level


if __name__ == "__main__":
    level = generate_level(
        level_id=build_level_id(1),
        color_count=5,
        max_stack_height=4,
        target_block_count=60,
        seed=7,
    )
    ok, msg = validate_generated_level(level)
    print(f"level id: {level['id']}")
    print(f"size: {level['size']}x{level['size']}")
    print(f"block count: {len(level['blocks'])}")
    print(f"basket length: {len(level['basketSequence'])}")
    print(f"validation: {ok} ({msg})")
    print("first 5 blocks:", level["blocks"][:5])
    print("basketSequence:", level["basketSequence"])
