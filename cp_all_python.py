#!/usr/bin/env python3

from pathlib import Path
import shutil
import sys


def copy_python_prefix_files(source_root: Path, dest_root: Path) -> None:
    if not source_root.exists() or not source_root.is_dir():
        raise ValueError(f"Source directory does not exist or is not a directory: {source_root}")

    for path in source_root.rglob("*"):
        if path.is_file() and path.name.startswith("Python"):
            relative_path = path.relative_to(source_root)
            target_path = dest_root / relative_path

            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target_path)

            print(f"Copied: {path} -> {target_path}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python copy_python_files.py <source_dir> <destination_dir>")
        sys.exit(1)

    source_root = Path(sys.argv[1]).resolve()
    dest_root = Path(sys.argv[2]).resolve()

    copy_python_prefix_files(source_root, dest_root)
    print("Done.")


if __name__ == "__main__":
    main()
