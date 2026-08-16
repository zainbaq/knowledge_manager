#!/usr/bin/env python3
"""Migrate per-user vector stores from username-keyed to user-ID-keyed directories.

WHY
---
Private vector stores used to live at ``{VECTOR_DB_PATH}/{sanitised_username}``,
where the sanitiser stripped every "." from the name. Distinct accounts could
therefore collapse onto one directory - "zain.baq@gmail.com" and
"zainbaq@gmailcom" both resolved to "zainbaq@gmailcom" - so each could read,
query and delete the other's documents. Stores now live at
``{VECTOR_DB_PATH}/u/{users.id}``, which cannot collide.

USAGE
-----
Dry run first (default - reports the plan, touches nothing)::

    python scripts/migrate_user_storage.py

Apply it::

    python scripts/migrate_user_storage.py --apply

IMPORTANT
---------
``users.db`` and ``VECTOR_DB_PATH`` must be migrated as ONE consistent
snapshot: the mapping this script rebuilds is derived from the user rows, so a
users.db from a different point in time produces wrong directory assignments.
Copy both together, run this against the copy, then cut over.

The script refuses to migrate any directory that two or more users share,
because there is no safe way to decide which documents belong to whom. Those
are reported for manual resolution and left untouched.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# Make the project root importable when run as scripts/migrate_user_storage.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import USER_DB_PATH, USER_STORE_PREFIX, VECTOR_DB_PATH  # noqa: E402


def legacy_dir_name(username: str) -> str:
    """Reproduce the OLD sanitiser exactly, to locate pre-migration directories.

    Frozen here on purpose: this is a historical artefact, not live behaviour.
    api/validation.sanitize_path_component may change or disappear; this must
    keep matching the directories that are actually on disk.
    """
    sanitized = username.replace('/', '').replace('\\', '').replace('\0', '')
    return sanitized.replace('..', '').replace('.', '')


def load_users(db_path: str) -> list[tuple[int, str]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT id, username FROM users ORDER BY id").fetchall()
    finally:
        conn.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the migration. Without this flag the script only reports.",
    )
    args = parser.parse_args()

    base = Path(VECTOR_DB_PATH).resolve()
    if not base.is_dir():
        print(f"ERROR: VECTOR_DB_PATH does not exist: {base}", file=sys.stderr)
        return 1
    if not Path(USER_DB_PATH).is_file():
        print(f"ERROR: USER_DB_PATH does not exist: {USER_DB_PATH}", file=sys.stderr)
        return 1

    users = load_users(str(USER_DB_PATH))
    print(f"vector store : {base}")
    print(f"user database: {USER_DB_PATH}")
    print(f"users        : {len(users)}\n")

    # Group users by the legacy directory they resolve to, to find collisions.
    by_legacy: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for user_id, username in users:
        by_legacy[legacy_dir_name(username)].append((user_id, username))

    planned: list[tuple[Path, Path, str]] = []
    collisions: list[tuple[str, list[tuple[int, str]]]] = []
    missing: list[tuple[int, str]] = []
    already: list[tuple[int, str]] = []

    for legacy, members in by_legacy.items():
        src = base / legacy if legacy else None
        dest_root = base / USER_STORE_PREFIX

        if len(members) > 1 and src is not None and src.is_dir():
            collisions.append((legacy, members))
            continue

        for user_id, username in members:
            dest = dest_root / str(user_id)
            if dest.exists():
                already.append((user_id, username))
                continue
            if src is None or not src.is_dir():
                missing.append((user_id, username))
                continue
            planned.append((src, dest, username))

    if collisions:
        print("!! COLLIDING DIRECTORIES - NOT MIGRATED, RESOLVE BY HAND !!")
        for legacy, members in collisions:
            names = ", ".join(f"id={i} {u!r}" for i, u in members)
            print(f"   {base / legacy}")
            print(f"      shared by: {names}")
        print()

    if already:
        print(f"already migrated ({len(already)}): "
              + ", ".join(f"id={i}" for i, _ in already) + "\n")

    if missing:
        print(f"no legacy directory, nothing to move ({len(missing)}): "
              + ", ".join(f"id={i} {u!r}" for i, u in missing) + "\n")

    if not planned:
        print("Nothing to migrate.")
        return 2 if collisions else 0

    print(f"to migrate ({len(planned)}):")
    for src, dest, username in planned:
        print(f"   {username!r}\n      {src}\n   -> {dest}")
    print()

    if not args.apply:
        print("DRY RUN - nothing changed. Re-run with --apply to perform it.")
        return 2 if collisions else 0

    (base / USER_STORE_PREFIX).mkdir(parents=True, exist_ok=True)
    moved = 0
    for src, dest, username in planned:
        # Copy-then-remove rather than move, so an interrupted run leaves the
        # original intact and the script stays safely re-runnable.
        shutil.copytree(src, dest)
        shutil.rmtree(src)
        moved += 1
        print(f"migrated {username!r} -> {dest}")

    print(f"\nDone. Migrated {moved} director{'y' if moved == 1 else 'ies'}.")
    if collisions:
        print(f"WARNING: {len(collisions)} colliding director"
              f"{'y' if len(collisions) == 1 else 'ies'} left untouched (see above).")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
