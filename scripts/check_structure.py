# scripts/check_structure.py
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    required_paths = [
        "src",
        "src/layer1_ingestion",
        "src/layer2_storage",
        "scripts",
        "data",
        "data/raw",
        "tests",
        "docs",
        "scripts/test_normalize.py",
        "scripts/test_embedding.py",
    ]

    missing = [p for p in required_paths if not (repo_root / p).exists()]

    import_errors: list[str] = []
    try:
        from src.layer1_ingestion import normalize_bot_log  # noqa: F401
    except Exception as e:
        import_errors.append(f"layer1_ingestion import failed: {type(e).__name__}: {e}")

    try:
        # модуль может называться иначе, но в вашей записи он существует как слой
        import src.layer2_storage  # noqa: F401
    except Exception as e:
        import_errors.append(f"layer2_storage import failed: {type(e).__name__}: {e}")

    if missing or import_errors:
        print("STRUCTURE FAIL")
        if missing:
            print("Missing paths:")
            for p in missing:
                print(f"- {p}")
        if import_errors:
            print("Import errors:")
            for msg in import_errors:
                print(f"- {msg}")
        return 1

    print("STRUCTURE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
