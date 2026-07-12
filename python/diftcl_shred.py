#!/usr/bin/env python3
"""Securely overwrite and delete locally written files (cross-platform).

DIFTCL audits often produce local artifacts from confidential legal documents
(extracted text, review packets, JSON). This helper best-effort "shreds" those
artifacts: it overwrites file contents with random (then zero) bytes, truncates,
renames, and removes the file. It is stdlib-only and runs the same on Windows,
macOS, and Linux.

IMPORTANT LIMITATION: on SSDs, flash media, and copy-on-write or journaled
filesystems (APFS, Btrfs, ZFS, NTFS with shadow copies), wear-leveling and
snapshots mean an in-place overwrite does NOT guarantee the original data blocks
are destroyed. Treat this as defense-in-depth, not a forensic guarantee. For
true guarantees use full-disk encryption and/or device-level secure erase.

Safety:
- Dry-run by default. Pass --yes to actually overwrite and delete.
- Refuses obviously dangerous targets (filesystem/drive roots, very short paths).
- Use --root to restrict deletion to a directory subtree.

Usage (use `python` or `py` on Windows):
    python3 diftcl_shred.py PATH [PATH ...] [--yes] [--passes N]
                            [--root DIR] [--keep-empty-dirs] [--quiet]
"""

from __future__ import annotations

import argparse
import os
import sys

# Emit UTF-8 even when piped on Windows so non-ASCII paths display correctly.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass
from pathlib import Path


CHUNK = 1 << 20  # 1 MiB


def iter_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        if target.is_dir() and not target.is_symlink():
            for sub in sorted(target.rglob("*")):
                if sub.is_file() and not sub.is_symlink():
                    files.append(sub)
        elif target.is_file() or target.is_symlink():
            files.append(target)
    return files


def is_dangerous(path: Path) -> str:
    try:
        resolved = path.resolve()
    except OSError:
        return "path cannot be resolved"
    # Drive/filesystem root, e.g. "C:\\" or "/".
    if resolved == resolved.anchor or resolved.parent == resolved:
        return "refusing to operate on a filesystem/drive root"
    # Very shallow paths are almost always a mistake.
    parts = [p for p in resolved.parts if p not in ("", resolved.anchor)]
    if len(parts) < 2:
        return f"path is too shallow to be safe: {resolved}"
    return ""


def within_root(path: Path, root: Path | None) -> bool:
    if root is None:
        return True
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def overwrite(path: Path, passes: int) -> None:
    size = path.stat().st_size
    flags = os.O_WRONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY  # Windows: avoid text translation.
    fd = os.open(path, flags)
    try:
        for current in range(passes + 1):
            os.lseek(fd, 0, os.SEEK_SET)
            # Final pass writes zeros; earlier passes write random bytes.
            zero = current == passes
            remaining = size
            while remaining > 0:
                n = min(CHUNK, remaining)
                os.write(fd, b"\x00" * n if zero else os.urandom(n))
                remaining -= n
            os.fsync(fd)
    finally:
        os.close(fd)


def shred_file(path: Path, passes: int, do_it: bool, quiet: bool) -> bool:
    try:
        if do_it:
            if path.is_file() and not path.is_symlink():
                overwrite(path, passes)
                # Truncate then rename to obscure the original name/size.
                os.truncate(path, 0)
                obscured = path.with_name("shred-" + os.urandom(8).hex() + ".tmp")
                path.rename(obscured)
                obscured.unlink()
            else:
                path.unlink()  # symlink or special: just remove the link.
        if not quiet:
            print(("SHREDDED " if do_it else "WOULD SHRED ") + str(path))
        return True
    except OSError as exc:
        print(f"ERROR shredding {path}: {exc}", file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", help="Files or directories to shred")
    parser.add_argument("--yes", action="store_true", help="Actually overwrite and delete (default is a dry run)")
    parser.add_argument("--passes", type=int, default=1, help="Random overwrite passes before a final zero pass (default 1)")
    parser.add_argument("--root", help="Restrict deletion to this directory subtree")
    parser.add_argument("--keep-empty-dirs", action="store_true", help="Do not remove directories left empty")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    args = parser.parse_args(argv)

    if args.passes < 0:
        parser.error("--passes must be >= 0")
    root = Path(args.root) if args.root else None
    targets = [Path(p) for p in args.paths]

    for target in targets:
        reason = is_dangerous(target)
        if reason:
            print(f"ABORT: {reason} ({target})", file=sys.stderr)
            return 2
        if not within_root(target, root):
            print(f"ABORT: {target} is outside --root {root}", file=sys.stderr)
            return 2
        if not target.exists() and not target.is_symlink():
            print(f"ABORT: path does not exist: {target}", file=sys.stderr)
            return 2

    files = iter_files(targets)
    if not files:
        print("No files to shred.")
        return 0

    if not args.yes and not args.quiet:
        print(f"DRY RUN: {len(files)} file(s) would be shredded. Re-run with --yes to delete.\n")

    failures = 0
    for f in files:
        if not within_root(f, root):
            print(f"SKIP (outside root): {f}", file=sys.stderr)
            failures += 1
            continue
        if not shred_file(f, args.passes, args.yes, args.quiet):
            failures += 1

    # Remove now-empty directories (deepest first).
    if args.yes and not args.keep_empty_dirs:
        for target in targets:
            if target.is_dir() and not target.is_symlink():
                for d in sorted(target.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                    if d.is_dir() and not any(d.iterdir()):
                        try:
                            d.rmdir()
                        except OSError:
                            pass
                if not any(target.iterdir()):
                    try:
                        target.rmdir()
                    except OSError:
                        pass

    if failures:
        print(f"\nCompleted with {failures} failure(s).", file=sys.stderr)
        return 1
    print(f"\n{'Shredded' if args.yes else 'Would shred'} {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
