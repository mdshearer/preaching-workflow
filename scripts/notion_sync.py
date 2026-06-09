#!/usr/bin/env python3
"""Two-way sync between a reflection's repo stage files and its Notion sub-pages.

Model: last-edit-wins, with a warning before any overwrite, and a hard stop
when BOTH sides changed since the last sync (a conflict you must resolve).

A manifest (.notion-sync.json in the reflection folder) records, per stage, the
state at the last successful sync: the Notion page id, the Notion page's
last_edited_time, and a hash of the repo file. That lets us tell which side
actually changed — not just which timestamp is larger.

Per stage, on `sync`:
  - Notion page missing       -> seed it (repo -> Notion)
  - only repo changed         -> push  (repo -> Notion), warn
  - only Notion changed        -> pull  (Notion -> repo), warn
  - both changed              -> CONFLICT: skip, unless --force-repo / --force-notion
  - neither changed           -> up to date

The repo stays canonical in the sense that git is the version history; this
just keeps the editable Notion surface and the repo in step. Commit pulled
changes yourself — this script does not touch git.

Note: the pull direction (Notion -> repo) is lossy — it flattens nested list
indentation (sub-bullets come back as top-level bullets). The repo is canonical;
prefer push. If you must pull, eyeball any nested lists before committing.

Usage:
    python3 scripts/notion_sync.py <folder> --parent <id> [--stage 02]
                                   [--init] [--force-repo | --force-notion] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from notion_push import (
    STAGE_TITLES,
    create_page, file_hash, get_token, load_manifest, md_hash,
    notion_pages_by_title, page_last_edited, page_to_markdown,
    push_stage, save_manifest, stage_baseline,
)


# --------------------------------------------------------------------------- #
# Pure decision helpers (unit-tested, no network)                              #
# --------------------------------------------------------------------------- #
def notion_needs_fetch(timestamp_equal: bool, repo_changed: bool) -> bool:
    """Whether we must fetch + hash the Notion page to know if it changed.

    Skip the fetch only when the page's last_edited_time matches the baseline
    AND the repo file is unchanged. We fetch when the repo changed even on a
    matching timestamp, because last_edited_time is minute-granular: a human
    edit in the same minute as the baseline could read as unchanged, and the
    one case where missing that loses data is push-over-edit (repo changed too).
    """
    return (not timestamp_equal) or repo_changed


def decide_action(repo_changed: bool, notion_changed: bool,
                  force_repo: bool, force_notion: bool) -> str:
    """Map (what changed) -> one of: push, pull, conflict, insync."""
    if repo_changed and notion_changed:
        if force_repo:
            return "push"
        if force_notion:
            return "pull"
        return "conflict"
    if repo_changed:
        return "push"
    if notion_changed:
        return "pull"
    return "insync"


# --------------------------------------------------------------------------- #
# Sync                                                                          #
# --------------------------------------------------------------------------- #
def seed(token, parent, title, path, manifest):
    pid = create_page(token, parent, title, path.read_text())
    notion_md = page_to_markdown(token, pid)
    manifest["stages"][path.name] = stage_baseline(
        pid, page_last_edited(token, pid), notion_md, path)
    print(f"  seeded  {title:18} -> Notion  {pid}")


def do_push(token, parent, title, path, pages, manifest):
    pid = push_stage(token, parent, title, path.read_text(), pages)
    notion_md = page_to_markdown(token, pid)
    manifest["stages"][path.name] = stage_baseline(
        pid, page_last_edited(token, pid), notion_md, path)
    print(f"  push →  {title:18} repo updated Notion (page kept)")


def do_pull(token, page_id, last_edited, title, path, manifest):
    md = page_to_markdown(token, page_id)
    path.write_text(md)
    manifest["stages"][path.name] = stage_baseline(
        page_id, last_edited, md, path)
    print(f"  ← pull  {title:18} Notion overwrote {path.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="reflection folder, e.g. reflections/2026-01-01-my-text")
    ap.add_argument("--parent", required=True, help="Notion parent page id")
    ap.add_argument("--stage", help="only this stage, e.g. 02")
    ap.add_argument("--force-repo", action="store_true",
                    help="on conflict, repo wins")
    ap.add_argument("--force-notion", action="store_true",
                    help="on conflict, Notion wins")
    ap.add_argument("--init", action="store_true",
                    help="record current repo+Notion as the in-sync baseline, "
                         "moving no content (use right after a fresh push)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"Not a directory: {folder}")

    token = get_token()
    manifest = load_manifest(folder)
    manifest["parent"] = args.parent
    pages = notion_pages_by_title(token, args.parent)

    files = sorted(folder.glob("[0-9][0-9]-*.md"))
    if args.stage:
        files = [f for f in files if f.name.startswith(args.stage)]
    if not files:
        sys.exit(f"No matching stage files in {folder}")

    conflicts = []
    for path in files:
        title = STAGE_TITLES.get(path.name[:2], path.stem)
        state = manifest["stages"].get(path.name)
        npage = pages.get(title)
        repo_hash = file_hash(path)

        if npage is None:
            print(f"  [{title}] not in Notion")
            if not args.dry_run:
                seed(token, args.parent, title, path, manifest)
            continue

        if state is None:
            if args.init:
                notion_md = page_to_markdown(token, npage["id"])
                manifest["stages"][path.name] = stage_baseline(
                    npage["id"], npage["last_edited"], notion_md, path)
                print(f"  baseline {title:18} (no content moved)")
            else:
                print(f"  ⚠ untracked {title:18} no sync baseline — "
                      f"run with --init first (can't tell which side changed)")
            continue

        # Migration: an older manifest entry has no notion_md_hash. Backfill it
        # from the current page (everything is in-sync at upgrade time).
        if "notion_md_hash" not in state:
            notion_md = page_to_markdown(token, npage["id"])
            state = dict(state)
            state["notion_md_hash"] = md_hash(notion_md)
            state["notion_edit"] = npage["last_edited"]
            manifest["stages"][path.name] = state
            print(f"  backfilled notion_md_hash  {title}")

        repo_changed = repo_hash != state.get("repo_hash")
        timestamp_equal = npage["last_edited"] == state.get("notion_edit")

        if notion_needs_fetch(timestamp_equal, repo_changed):
            notion_changed = (md_hash(page_to_markdown(token, npage["id"]))
                              != state.get("notion_md_hash"))
        else:
            notion_changed = False

        action = decide_action(repo_changed, notion_changed,
                               args.force_repo, args.force_notion)

        if action == "conflict":
            conflicts.append(title)
            print(f"  ⚠ CONFLICT  {title:18} both sides changed — skipped")
            continue
        if action == "insync":
            print(f"  ✓ in sync  {title}")
            continue
        if args.dry_run:
            print(f"  [dry] would {action}  {title}")
            continue
        if action == "push":
            do_push(token, args.parent, title, path, pages, manifest)
        else:
            do_pull(token, npage["id"], npage["last_edited"], title, path,
                    manifest)

    if not args.dry_run:
        save_manifest(folder, manifest)

    if conflicts:
        print(f"\n⚠ {len(conflicts)} conflict(s): {', '.join(conflicts)}")
        print("  Resolve by re-running with --force-repo or --force-notion,")
        print("  or reconcile by hand first.")


if __name__ == "__main__":
    main()
