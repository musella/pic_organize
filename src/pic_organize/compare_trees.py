import os
import sys

from pathlib import Path
from enum import Enum
from pydantic import BaseModel


class MismatchType(str, Enum):
    """
    An enumeration representing different types of mismatches that can occur
    when comparing directory trees.

    Attributes:
        SIZE: Indicates a mismatch in file sizes between the two trees.
        SYMLINK: Indicates a mismatch in symlink properties between the two trees.
        OTHER: Represents any other type of mismatch not explicitly categorized.
        MISSING: Indicates that a file is missing in one of the trees.
    """

    SIZE = "Size mismatch"
    SYMLINK = "Symlink mismatch"
    OTHER = "Other mismatch"
    MISSING = "Missing file"


class Mismatch(BaseModel):
    """
    Represents a mismatch between two directory trees.

    Attributes:
        path (Path): The file or directory path where the mismatch occurred.
        mismatch_type (MismatchType): The type of mismatch (e.g., missing file, content difference).
        details (str): Additional details about the mismatch.
    """

    path: Path
    mismatch_type: MismatchType
    details: str


def compare_trees(dir1: str | Path, dir2: str | Path) -> list[Mismatch]:
    """
    Compare two directory trees for file presence, size, and symlink properties.

    Args:
        dir1: The source directory to check files from.
        dir2: The target directory to compare against.

    Returns:
        A list of Mismatch instances representing the differences between the two trees.
    """
    dir1 = Path(dir1).resolve()
    dir2 = Path(dir2).resolve()
    mismatches: list[Mismatch] = []

    for root, _, files in os.walk(dir1):
        for file in files:
            rel_path = Path(root).relative_to(dir1) / file
            file1 = dir1 / rel_path
            file2 = dir2 / rel_path

            if not file2.exists():
                mismatches.append(
                    Mismatch(
                        path=rel_path,
                        mismatch_type=MismatchType.MISSING,
                        details="File is missing in dir2",
                    )
                )
            else:
                stat1 = file1.stat()
                stat2 = file2.stat()
                if file2.is_symlink():
                    mismatches.append(
                        Mismatch(
                            path=rel_path,
                            mismatch_type=MismatchType.SYMLINK,
                            details="Target is a symlink in dir2",
                        )
                    )
                    continue
                if stat1.st_size != stat2.st_size:
                    mismatches.append(
                        Mismatch(
                            path=rel_path,
                            mismatch_type=MismatchType.SIZE,
                            details=f"Size mismatch: {stat1.st_size} vs {stat2.st_size}",
                        )
                    )

    return mismatches


def act_on_mismatches(
    mismatches: list[Mismatch],
    dir1: Path,
    dir2: Path,
    dry_run: bool = False,
    confirm: bool = False,
):
    """
    Act on mismatches by copying files from dir1 to dir2 if missing, smaller, or symlink in dir2.
    Preserves creation and modification times.
    Args:
        mismatches: List of Mismatch objects.
        dir1: Source directory.
        dir2: Target directory.
        dry_run: If True, only print actions without performing them.
        confirm: If True, ask for confirmation before each file operation.
    """
    import shutil

    for mismatch in mismatches:
        src = dir1 / mismatch.path
        dst = dir2 / mismatch.path
        action_needed = False
        reason = ""
        if mismatch.mismatch_type == MismatchType.MISSING:
            action_needed = True
            reason = "Missing file"
        elif mismatch.mismatch_type == MismatchType.SIZE:
            # Only copy if src is larger than dst
            src_size = src.stat().st_size
            dst_size = dst.stat().st_size if dst.exists() else 0
            if src_size > dst_size:
                action_needed = True
                reason = f"Source is larger ({src_size} > {dst_size})"
        elif mismatch.mismatch_type == MismatchType.SYMLINK:
            action_needed = True
            reason = "Target is symlink"
        if action_needed:
            print(f"Copying {src} -> {dst} ({reason})", flush=True)
            if dry_run:
                continue
            if confirm:
                resp = input(f"Copy {src} to {dst}? [y/N]: ").strip().lower()
                if resp != "y":
                    print("Skipped.")
                    continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if dst.is_symlink():
                    dst.unlink()
                else:
                    try:
                        os.remove(dst)
                    except Exception:
                        pass
            shutil.copy2(src, dst)
            # Preserve creation time if possible
            try:
                st = src.stat()
                os.utime(dst, (st.st_atime, st.st_mtime))
                # shutil.copy2 already preserves times, st_ctime is not settable on most systems
            except Exception as e:
                print(f"Failed to preserve times for {dst}: {e}")


def main():
    """
    Command-line interface for comparing two directory trees.
    Usage: python compare_trees.py <dir1> <dir2>
    """
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <dir1> <dir2>")
        sys.exit(1)
    dir1, dir2 = sys.argv[1], sys.argv[2]
    mismatches = compare_trees(dir1, dir2)
    act_on_mismatches(
        mismatches,
        Path(dir1).resolve(),
        Path(dir2).resolve(),
        dry_run=False,
        confirm=False,
    )
    # if mismatches:
    #     print("Mismatches found:")
    #     for mismatch in mismatches:
    #         print(f"Path: {mismatch.path}")
    #         print(f"Type: {mismatch.mismatch_type}")
    #         print(f"Details: {mismatch.details}")
    #         print("-" * 40)
    # else:
    #     print("No mismatches found.")


if __name__ == "__main__":
    main()
