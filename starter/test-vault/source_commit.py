"""Identify a clean Git checkout for an execution receipt."""

import subprocess
import sys
from pathlib import Path


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL,
    ).strip()


def source_commit(root, inputs=()):
    root = Path(root).resolve()
    try:
        if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise ValueError("run the receipt tools from the intended Git checkout root")
        if git(root, "status", "--porcelain=v1", "--untracked-files=no"):
            raise ValueError("commit tracked changes before writing or verifying receipts")
        for path in inputs:
            relative = Path(path).resolve().relative_to(root)
            git(root, "ls-files", "--error-unmatch", "--", relative.as_posix())
        return git(root, "rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("receipt source must be tracked in the intended Git checkout") from error


if __name__ == "__main__":
    try:
        print(source_commit(Path.cwd(), (Path(__file__), *sys.argv[1:])))
    except ValueError as error:
        raise SystemExit(str(error))
