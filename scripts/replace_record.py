#!/usr/bin/env python3
"""Safely replace one existing project-memory record using only the standard library."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import stat
import sys
import time
import uuid
from pathlib import Path
from typing import Callable


EXIT_OK = 0
EXIT_INVALID_INVOCATION = 2
EXIT_REFUSED = 3
EXIT_STALE = 4
EXIT_LOCKED = 5
EXIT_IO_ERROR = 6
MAX_REPLACE_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (0.02, 0.05)
RETRY_CEILING_SECONDS = 0.25
RESULT_SCHEMA = "project-memory/replace-record@1"


class RefusedError(Exception):
    """A safety or containment precondition was not met."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_reparse_or_symlink(path: Path) -> bool:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _resolve_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RefusedError(f"{label} cannot be resolved: {exc}") from exc
    if not resolved.is_dir():
        raise RefusedError(f"{label} is not a directory")
    return resolved


def _normalize_under(base: Path, value: Path) -> Path:
    return value if value.is_absolute() else base / value


def _validate_expected_hash(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise RefusedError("expected SHA-256 must be exactly 64 hexadecimal characters")
    return normalized


def _validate_proposed_bytes(value: bytes) -> None:
    if value.startswith(b"\xef\xbb\xbf"):
        raise RefusedError("proposed content must be UTF-8 without a BOM")
    try:
        value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RefusedError("proposed content is not valid UTF-8") from exc


class ValidatedPaths:
    def __init__(
        self,
        owner_input: Path,
        memory_input: Path,
        target_input: Path,
        owner: Path,
        memory: Path,
        target: Path,
        proposed: Path,
    ) -> None:
        self.owner_input = owner_input
        self.memory_input = memory_input
        self.target_input = target_input
        self.owner = owner
        self.memory = memory
        self.target = target
        self.proposed = proposed


def validate_paths(
    owner_root: Path,
    memory_root: Path,
    target: Path,
    proposed_content: Path,
) -> ValidatedPaths:
    owner_input = owner_root.absolute()
    owner = _resolve_directory(owner_input, "owner root")
    memory_input = _normalize_under(owner_input, memory_root).absolute()
    memory = _resolve_directory(memory_input, "memory root")
    if not _is_relative_to(memory, owner):
        raise RefusedError("resolved memory root escapes the resolved owner root")

    target_input = _normalize_under(memory_input, target).absolute()
    try:
        target_info = target_input.lstat()
    except OSError as exc:
        raise RefusedError(f"target does not exist or cannot be inspected: {exc}") from exc
    if _is_reparse_or_symlink(target_input):
        raise RefusedError("target file is a symlink or reparse point")
    if not stat.S_ISREG(target_info.st_mode):
        raise RefusedError("target is not a regular file")
    if target_input.suffix.lower() != ".md":
        raise RefusedError("target is not a Markdown memory file")
    try:
        target_resolved = target_input.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RefusedError(f"target cannot be resolved: {exc}") from exc
    if not _is_relative_to(target_resolved, owner) or not _is_relative_to(target_resolved, memory):
        raise RefusedError("resolved target escapes the resolved owner or memory root")

    proposed_input = proposed_content.absolute()
    try:
        proposed = proposed_input.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RefusedError(f"proposed-content file cannot be resolved: {exc}") from exc
    if not proposed.is_file():
        raise RefusedError("proposed-content path is not a regular file")
    if proposed == target_resolved:
        raise RefusedError("proposed-content file must be separate from the target")

    return ValidatedPaths(
        owner_input=owner_input,
        memory_input=memory_input,
        target_input=target_input,
        owner=owner,
        memory=memory,
        target=target_resolved,
        proposed=proposed,
    )


def revalidate_containment(paths: ValidatedPaths) -> None:
    owner = _resolve_directory(paths.owner_input, "owner root")
    memory = _resolve_directory(paths.memory_input, "memory root")
    if owner != paths.owner or memory != paths.memory or not _is_relative_to(memory, owner):
        raise RefusedError("owner or memory root changed during replacement")
    if _is_reparse_or_symlink(paths.target_input):
        raise RefusedError("target became a symlink or reparse point")
    try:
        target = paths.target_input.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RefusedError(f"target cannot be re-resolved: {exc}") from exc
    if target != paths.target:
        raise RefusedError("target resolution changed during replacement")
    if not target.is_file() or not _is_relative_to(target, owner) or not _is_relative_to(target, memory):
        raise RefusedError("target no longer resolves inside the owner and memory roots")


def _result(status: str, target: str, **details: object) -> dict[str, object]:
    result: dict[str, object] = {"schema": RESULT_SCHEMA, "status": status, "target": target}
    result.update(details)
    return result


def _target_label(paths: ValidatedPaths) -> str:
    return paths.target.relative_to(paths.memory).as_posix()


def _make_temp(paths: ValidatedPaths, proposed_bytes: bytes, mode: int) -> Path:
    for _ in range(8):
        temp = paths.target.parent / (
            f".{paths.target.name}.project-memory-replace-{uuid.uuid4().hex}.tmp"
        )
        try:
            with temp.open("xb") as handle:
                handle.write(proposed_bytes)
                handle.flush()
                os.fsync(handle.fileno())
                os.chmod(temp, mode)
                handle.flush()
                os.fsync(handle.fileno())
            return temp
        except FileExistsError:
            continue
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
    raise OSError("could not allocate a unique replacement sibling")


def _cleanup_temp(temp: Path | None) -> str | None:
    if temp is None or not temp.exists():
        return None
    try:
        temp.unlink()
        return None
    except OSError as exc:
        return str(exc)


def _is_transient_lock(exc: OSError) -> bool:
    if getattr(exc, "winerror", None) in {5, 32, 33}:
        return True
    return exc.errno in {errno.EACCES, errno.EBUSY, errno.EPERM}


def replace_record(
    *,
    owner_root: Path,
    memory_root: Path,
    target: Path,
    expected_sha256: str,
    proposed_content: Path,
    dry_run: bool = False,
    replace_func: Callable[[str, str], object] | None = None,
    sleep_func: Callable[[float], object] = time.sleep,
    monotonic_func: Callable[[], float] = time.monotonic,
) -> tuple[int, dict[str, object]]:
    target_for_error = str(target)
    try:
        expected = _validate_expected_hash(expected_sha256)
        paths = validate_paths(owner_root, memory_root, target, proposed_content)
        target_for_error = _target_label(paths)
        revalidate_containment(paths)
        current_hash = sha256_file(paths.target)
        if current_hash != expected:
            return EXIT_STALE, _result(
                "stale", target_for_error, expected_sha256=expected, actual_sha256=current_hash
            )
        proposed_bytes = paths.proposed.read_bytes()
        _validate_proposed_bytes(proposed_bytes)
        proposed_hash = hashlib.sha256(proposed_bytes).hexdigest()
        if dry_run:
            return EXIT_OK, _result(
                "dry-run",
                target_for_error,
                expected_sha256=expected,
                proposed_sha256=proposed_hash,
                bytes=len(proposed_bytes),
            )

        target_mode = stat.S_IMODE(paths.target.stat().st_mode)
        temp: Path | None = None
        try:
            revalidate_containment(paths)
            temp = _make_temp(paths, proposed_bytes, target_mode)
            replace = replace_func or os.replace
            started = monotonic_func()
            attempts = 0
            while attempts < MAX_REPLACE_ATTEMPTS:
                attempts += 1
                revalidate_containment(paths)
                current_hash = sha256_file(paths.target)
                if current_hash != expected:
                    cleanup_error = _cleanup_temp(temp)
                    return EXIT_STALE, _result(
                        "stale",
                        target_for_error,
                        expected_sha256=expected,
                        actual_sha256=current_hash,
                        attempts=attempts,
                        cleanup_error=cleanup_error,
                    )
                try:
                    replace(str(temp), str(paths.target))
                    temp = None
                    final_bytes = paths.target.read_bytes()
                    if final_bytes != proposed_bytes:
                        return EXIT_IO_ERROR, _result(
                            "io-error",
                            target_for_error,
                            error="replacement completed but final bytes differ from proposed bytes",
                            attempts=attempts,
                        )
                    return EXIT_OK, _result(
                        "replaced",
                        target_for_error,
                        expected_sha256=expected,
                        final_sha256=hashlib.sha256(final_bytes).hexdigest(),
                        bytes=len(final_bytes),
                        attempts=attempts,
                    )
                except OSError as exc:
                    if not _is_transient_lock(exc):
                        cleanup_error = _cleanup_temp(temp)
                        return EXIT_IO_ERROR, _result(
                            "io-error",
                            target_for_error,
                            error=str(exc),
                            attempts=attempts,
                            cleanup_error=cleanup_error,
                        )
                    elapsed = monotonic_func() - started
                    if attempts >= MAX_REPLACE_ATTEMPTS:
                        cleanup_error = _cleanup_temp(temp)
                        return EXIT_LOCKED, _result(
                            "locked",
                            target_for_error,
                            attempts=attempts,
                            elapsed_seconds=round(elapsed, 6),
                            cleanup_error=cleanup_error,
                        )
                    delay = RETRY_DELAYS_SECONDS[attempts - 1]
                    if elapsed + delay > RETRY_CEILING_SECONDS:
                        cleanup_error = _cleanup_temp(temp)
                        return EXIT_LOCKED, _result(
                            "locked",
                            target_for_error,
                            attempts=attempts,
                            elapsed_seconds=round(elapsed, 6),
                            cleanup_error=cleanup_error,
                        )
                    sleep_func(delay)
            cleanup_error = _cleanup_temp(temp)
            return EXIT_LOCKED, _result(
                "locked", target_for_error, attempts=attempts, cleanup_error=cleanup_error
            )
        except RefusedError:
            _cleanup_temp(temp)
            raise
        except OSError as exc:
            cleanup_error = _cleanup_temp(temp)
            return EXIT_IO_ERROR, _result(
                "io-error", target_for_error, error=str(exc), cleanup_error=cleanup_error
            )
    except RefusedError as exc:
        return EXIT_REFUSED, _result("refused", target_for_error, error=str(exc))
    except (OSError, UnicodeError) as exc:
        return EXIT_IO_ERROR, _result("io-error", target_for_error, error=str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Atomically replace one existing project-memory Markdown record.",
        epilog=(
            "Exit codes: 0 replaced/dry-run, 2 invalid invocation, 3 refused, "
            "4 stale, 5 locked, 6 I/O error. Output is one bounded JSON object."
        ),
    )
    parser.add_argument(
        "--owner-root",
        required=True,
        type=Path,
        help="Owner (hub) root containing the configured memory namespace.",
    )
    parser.add_argument(
        "--memory-root",
        required=True,
        type=Path,
        help="Configured memory root; relative paths resolve from --owner-root.",
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="Existing Markdown record; relative paths resolve from --memory-root.",
    )
    parser.add_argument(
        "--expected-sha256",
        required=True,
        help="Expected SHA-256 of the target's current raw bytes.",
    )
    parser.add_argument(
        "--proposed-content",
        required=True,
        type=Path,
        help="Separate UTF-8 file whose raw bytes will replace the target.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without creating files, replacing the target, or changing metadata.",
    )
    return parser.parse_args()


def main() -> int:
    if sys.version_info < (3, 10):
        print(json.dumps(_result("refused", "", error="Python 3.10 or newer is required")))
        return EXIT_REFUSED
    args = parse_args()
    code, result = replace_record(
        owner_root=args.owner_root,
        memory_root=args.memory_root,
        target=args.target,
        expected_sha256=args.expected_sha256,
        proposed_content=args.proposed_content,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
