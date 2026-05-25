#!/usr/bin/env python3
"""Check for gitignored files in staged changes."""

import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    files = result.stdout.strip().split("\n")
    if not files or files == [""]:
        return 0

    ignored_files = []
    for f in files:
        r = subprocess.run(
            ["git", "check-ignore", f],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            ignored_files.append(f)

    if ignored_files:
        print("\nERROR: Refusing to commit gitignored files:")
        for f in ignored_files:
            print(f"  {f}")
        print("\nUnstage them: git reset HEAD -- <file>")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
