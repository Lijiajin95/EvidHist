"""Keep the product API snapshot synchronized before generating frontend contract types."""

import argparse
import json
from pathlib import Path

from evidhist.api import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = Path("contracts/openapi.json")
    current = (
        json.dumps(create_app().openapi(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != current:
            print("API contract drift: update the snapshot and review client compatibility.")
            return 1
        print("API contract snapshot matches the running schema.")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(current, encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
