#!/usr/bin/env python3
"""Read comments on a reflection's Notion sub-pages and print them with context.

Notion has two kinds of comment, and both are collected here:
  - page-level comments (the box at the top of a page)
  - inline comments (anchored to a specific block — these attach to the block
    id, not the page, so we walk the block tree and query each one)

Output is grouped per stage sub-page, each comment shown with the text it is
anchored to, so the feedback is legible without opening Notion. This is a
read-only step: comments feed a *repo* edit, never a direct Notion edit.

Usage:
    python3 scripts/notion_comments.py --parent <page-id> [--stage 02]
"""
from __future__ import annotations

import argparse
import sys
import time

from notion_push import api_call, get_token

RATE = 0.5  # gentle on the public-API burst limit; api_call also retries 429


def block_plain_text(block: dict) -> str:
    """Best-effort plain text for any block type that carries rich_text."""
    btype = block.get("type", "")
    payload = block.get(btype, {})
    rt = payload.get("rich_text") or payload.get("title") or []
    if isinstance(rt, list):
        return "".join(seg.get("plain_text", "") for seg in rt).strip()
    return ""


def walk_blocks(token: str, block_id: str, depth: int = 0):
    """Yield (block, depth) for every descendant block, depth-first."""
    cursor = None
    while True:
        path = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        res = api_call(token, "GET", path)
        time.sleep(RATE)
        for blk in res.get("results", []):
            yield blk, depth
            if blk.get("has_children") and blk.get("type") != "child_page":
                yield from walk_blocks(token, blk["id"], depth + 1)
        if res.get("has_more"):
            cursor = res.get("next_cursor")
        else:
            break


def get_comments(token: str, block_id: str) -> list[dict]:
    res = api_call(token, "GET", f"/comments?block_id={block_id}")
    time.sleep(RATE)
    return res.get("results", [])


def comment_text(c: dict) -> str:
    return "".join(seg.get("plain_text", "") for seg in c.get("rich_text", [])).strip()


def collect_page_comments(token: str, page_id: str, title: str) -> list[dict]:
    """Return structured comment records for a page: page-level + inline.

    Each record is {stage, kind, anchor, date, text}. ``anchor`` is the FULL
    text of the block the comment is attached to — never truncated here, because
    a comment is useless without the sentence it lands on. Truncation, if any, is
    a presentation choice left to the renderer.
    """
    records: list[dict] = []

    # page-level comments (the box at the top of a page) — no anchor
    for c in get_comments(token, page_id):
        records.append({
            "stage": title, "kind": "page", "anchor": "",
            "date": c.get("created_time", "")[:10], "text": comment_text(c),
        })

    # inline comments, anchored to specific blocks
    for blk, _depth in walk_blocks(token, page_id):
        if blk.get("type") == "child_page":
            continue
        cs = get_comments(token, blk["id"])
        if not cs:
            continue
        anchor = block_plain_text(blk) or "(non-text block)"
        for c in cs:
            records.append({
                "stage": title, "kind": "inline", "anchor": anchor,
                "date": c.get("created_time", "")[:10], "text": comment_text(c),
            })
    return records


def render_records(records: list[dict], full_anchor: bool = False) -> list[str]:
    """Format comment records for printing. Consecutive comments on the same
    block share one ``on:`` anchor line. ``full_anchor`` keeps the whole
    sentence; otherwise it is clipped to 90 chars (the standalone-tool default)."""
    lines: list[str] = []
    last_anchor = object()  # sentinel so the first inline always prints its anchor
    for r in records:
        if r["kind"] == "page":
            lines.append(f"  [page] {r['date']}")
            lines.append(f"    “{r['text']}”")
            last_anchor = object()
            continue
        anchor = r["anchor"]
        if not full_anchor:
            anchor = anchor[:90] + ("…" if len(anchor) > 90 else "")
        if anchor != last_anchor:
            lines.append(f"  on: “{anchor}”")
            last_anchor = anchor
        lines.append(f"    • {r['date']}  “{r['text']}”")
    return lines


def report_page(token: str, page_id: str, title: str) -> int:
    records = collect_page_comments(token, page_id, title)
    print(f"\n=== {title} ===")
    if records:
        print("\n".join(render_records(records)))
    else:
        print("  (no comments)")
    return len(records)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", required=True, help="Notion parent page id")
    ap.add_argument("--stage", help="only this stage, e.g. 02")
    args = ap.parse_args()

    token = get_token()

    children = api_call(token, "GET",
                        f"/blocks/{args.parent}/children?page_size=100")
    subpages = [
        (b["id"], b["child_page"]["title"])
        for b in children.get("results", [])
        if b.get("type") == "child_page"
    ]
    if args.stage:
        subpages = [(i, t) for i, t in subpages if t.startswith(args.stage)]
    if not subpages:
        sys.exit("No matching sub-pages found under parent.")

    total = 0
    for pid, title in subpages:
        total += report_page(token, pid, title)

    print(f"\n{total} comment(s) total.")


if __name__ == "__main__":
    main()
