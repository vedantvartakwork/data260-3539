#!/usr/bin/env python3
"""Print concise screenshot evidence from the saved five-turn demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def print_turn(record: dict[str, object]) -> None:
    usage = record["usage"]
    assert isinstance(usage, dict)
    print(f"Turn {record['turn']}")
    print(f"Prompt: {record['prompt']}")
    print(record["response"])
    print(
        "Tokens: "
        f"input={usage['input_tokens']}, "
        f"output={usage['output_tokens']}, "
        f"total={usage['total_tokens']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()

    data = json.loads(Path("reports/hw01/raw/five_turn_demo.json").read_text(encoding="utf-8"))
    turns = data["turns"]
    selected = turns[:3] if args.part == 1 else turns[3:]

    print(f"Saved model: {data['model']}")
    print(f"Model turns: {data['model_turns']}; /stats commands: {data['stats_commands']}\n")
    for record in selected:
        print_turn(record)
        if "stats_after_turn" in record:
            print(f"/stats after turn {record['turn']}: {json.dumps(record['stats_after_turn'])}")
        print()

    if args.part == 2:
        print(f"Final totals: {json.dumps(data['final_stats'])}")


if __name__ == "__main__":
    main()
