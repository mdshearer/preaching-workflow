#!/usr/bin/env python3
"""Read-only review brief for a reflection's Notion sub-pages.

Pulls, per stage, BOTH things you need before deciding what to fold back into
the repo, and changes nothing on either side:

  1. A COMMENTS SUMMARY at the very top — every comment across every stage, with
     the full sentence it is anchored to — so the human feedback (the signal of
     a review) can never be buried beneath a long diff.
  2. Then, per stage: a text diff of the Notion page against the repo file (so
     you can see what was edited on Notion since the last push, without a
     destructive pull), with that stage's comments repeated inline for context.

This is the "review and discuss" step that sits *before* notion_sync. It never
writes: not to Notion, not to the repo, not to the manifest. Once you've decided
each edit/comment in conversation, apply the change to the repo file and push
(or run notion_sync --force-repo / --force-notion) as a separate, deliberate act.

Diff legend (unified diff, repo as the "before"):
    -  line present in the REPO but not on Notion  (Notion dropped/changed it)
    +  line present on NOTION but not in the repo   (a Notion edit to fold back)

Usage:
    python3 scripts/notion_review.py <folder> --parent <id> [--stage 02] [--context N]
"""
from __future__ import annotations

import argparse
import difflib
import sys

from notion_push import STAGE_TITLES, get_token
from notion_sync import notion_pages_by_title, page_to_markdown
from notion_comments import collect_page_comments, render_records

from pathlib import Path


def show_diff(repo_md: str, notion_md: str, title: str, context: int) -> bool:
    """Print a unified diff repo->Notion. Return True if they differ."""
    repo_lines = repo_md.splitlines(keepends=True)
    notion_lines = notion_md.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        repo_lines, notion_lines,
        fromfile=f"{title} (repo)", tofile=f"{title} (Notion)",
        n=context,
    ))
    if not diff:
        print("  ✓ Notion and repo match — no edits to fold back.")
        return False
    print("  ── diff (repo → Notion) ──")
    for ln in diff:
        print("  " + ln.rstrip("\n"))
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="reflection folder, e.g. reflections/2026-01-01-my-text")
    ap.add_argument("--parent", required=True, help="Notion parent page id")
    ap.add_argument("--stage", help="only this stage, e.g. 02")
    ap.add_argument("--context", type=int, default=3,
                    help="diff context lines (default 3)")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"Not a directory: {folder}")

    token = get_token()
    pages = notion_pages_by_title(token, args.parent)

    files = sorted(folder.glob("[0-9][0-9]-*.md"))
    if args.stage:
        files = [f for f in files if f.name.startswith(args.stage)]
    if not files:
        sys.exit(f"No matching stage files in {folder}")

    print(f"Reflection: {folder}")
    print(f"Parent page: {args.parent}")
    print("Read-only — nothing is written to Notion, the repo, or the manifest.")

    # ---- pass 1: collect comments across every stage (comments-first) ----
    # The human's comments are the signal of a review pass; a long diff must not
    # be able to bury them. Gather them all before printing anything else.
    records_by_title: dict[str, list[dict]] = {}
    total_comments = 0
    for path in files:
        title = STAGE_TITLES.get(path.name[:2], path.stem)
        npage = pages.get(title)
        if npage is None:
            continue
        recs = collect_page_comments(token, npage["id"], title)
        records_by_title[title] = recs
        total_comments += len(recs)

    print(f"\n{'#'*60}\n# COMMENTS SUMMARY — {total_comments} total\n{'#'*60}")
    if total_comments == 0:
        print("  (no comments on any stage)")
    else:
        for path in files:
            title = STAGE_TITLES.get(path.name[:2], path.stem)
            recs = records_by_title.get(title) or []
            if not recs:
                continue
            print(f"\n  {title}")
            for line in render_records(recs, full_anchor=True):
                print("  " + line)
        print("\n  ↓ each comment's full anchor + the stage diff are repeated below")

    # ---- pass 2: per-stage diff + the same comments inline, for context ----
    for path in files:
        title = STAGE_TITLES.get(path.name[:2], path.stem)
        npage = pages.get(title)
        print(f"\n{'='*60}\n{title}   <- {path.name}\n{'='*60}")
        if npage is None:
            print("  (not on Notion yet — nothing to review)")
            continue

        notion_md = page_to_markdown(token, npage["id"])
        repo_md = path.read_text()
        show_diff(repo_md, notion_md, title, args.context)

        recs = records_by_title.get(title) or []
        print(f"\n  comments ({len(recs)}):")
        if recs:
            print("\n".join("  " + l for l in render_records(recs, full_anchor=True)))
        else:
            print("    (none)")


if __name__ == "__main__":
    main()
