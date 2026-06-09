#!/usr/bin/env python3
"""Push reflection stage artifacts into a Notion workspace.

One-way, on-demand. The repo is canonical; Notion is a view/comment surface.
Each numbered stage file (NN-*.md) in a reflection folder becomes a sub-page
under the given Notion parent page, titled "NN — Stage".

Re-running updates the existing stage sub-pages in place (same page id, URL,
and position); a stage with no sub-page yet is created. Idempotent.

After a successful (non-dry-run) push, the sync manifest (.notion-sync.json) is
re-baselined for every pushed stage — page id, Notion last_edited_time, and repo
file hash — so a subsequent `notion_sync` sees them as in-sync rather than
phantom-conflicting. (This is why notion_sync imports the manifest helpers from
here.)

Auth: set the NOTION_TOKEN environment variable to a Notion internal-integration
token (https://www.notion.so/my-integrations). Never hard-code it; never commit
it. If you keep secrets in a manager (1Password, Vault, etc.), export it just for
the command, e.g.:  NOTION_TOKEN="$(op read op://vault/notion/credential)" python3 ...

Usage:
    python3 scripts/notion_push.py <reflection-folder> --parent <page-id> [--stage 03] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ModuleNotFoundError:
    # python.org Python ships no CA bundle; if TLS verification fails, install
    # certifi (`pip install certifi`). We fall back to the system default here.
    _SSL_CTX = ssl.create_default_context()

NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"

STAGE_TITLES = {
    "01": "01 — Brief",
    "02": "02 — Devotional",
    "03": "03 — Exegetical",
    "04": "04 — Hermeneutical",
    "05": "05 — Homiletical",
    "06": "06 — Voice Check",
    "07": "07 — Final",
}

MAX_TEXT = 2000  # Notion rich_text hard limit per chunk
MANIFEST = ".notion-sync.json"  # shared with notion_sync
RATE = 0.5  # polite pause after listing a parent's children


# --------------------------------------------------------------------------- #
# Auth + HTTP                                                                  #
# --------------------------------------------------------------------------- #
def get_token() -> str:
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if not tok:
        sys.exit(
            "NOTION_TOKEN is not set. Create an internal integration at "
            "https://www.notion.so/my-integrations, share your reflection's "
            "parent page with it, then export the token:\n"
            "    export NOTION_TOKEN='secret_...'\n"
        )
    return tok


def api_call(token: str, method: str, path: str, body: dict | None = None,
             max_retries: int = 5) -> dict:
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Notion-Version", NOTION_VERSION)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                wait = float(e.headers.get("Retry-After", 2)) + 0.5
                time.sleep(wait)
                continue
            detail = e.read().decode()
            sys.exit(f"Notion API {e.code} on {method} {path}:\n{detail}")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            # Transient network blip (e.g. connection reset mid-request). The
            # in-place update fires many sequential calls, so retry with backoff
            # rather than abandoning the page half-updated.
            if attempt < max_retries:
                time.sleep(1.5 ** attempt + 0.5)
                continue
            sys.exit(f"Notion API connection error on {method} {path}: {e}")


# --------------------------------------------------------------------------- #
# Inline markdown -> rich_text                                                 #
# --------------------------------------------------------------------------- #
INLINE_RE = re.compile(
    r"(\*\*.+?\*\*|\*.+?\*|`.+?`|\[.+?\]\(.+?\))", re.DOTALL
)
LINK_RE = re.compile(r"\[(.+?)\]\((.+?)\)", re.DOTALL)


def rich_text(text: str) -> list[dict]:
    """Convert a span of markdown to Notion rich_text objects."""
    if not text:
        return []
    out: list[dict] = []
    for part in INLINE_RE.split(text):
        if not part:
            continue
        ann = {}
        content = part
        link = None
        if part.startswith("**") and part.endswith("**"):
            ann["bold"] = True
            content = part[2:-2]
        elif part.startswith("*") and part.endswith("*"):
            ann["italic"] = True
            content = part[1:-1]
        elif part.startswith("`") and part.endswith("`"):
            ann["code"] = True
            content = part[1:-1]
        else:
            m = LINK_RE.fullmatch(part)
            if m:
                content, link = m.group(1), m.group(2)
        # chunk to respect the 2000-char limit
        for i in range(0, len(content), MAX_TEXT):
            chunk = content[i:i + MAX_TEXT]
            t = {"type": "text", "text": {"content": chunk}}
            if link:
                t["text"]["link"] = {"url": link}
            if ann:
                t["annotations"] = dict(ann)
            out.append(t)
    return out


def _block(kind: str, text: str, **extra) -> dict:
    payload = {"rich_text": rich_text(text)}
    payload.update(extra)
    return {"object": "block", "type": kind, kind: payload}


# --------------------------------------------------------------------------- #
# Block-level markdown -> Notion blocks                                        #
# --------------------------------------------------------------------------- #
def md_to_blocks(md: str) -> list[dict]:
    lines = md.split("\n")
    blocks: list[dict] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # code fence
        if stripped.startswith("```"):
            lang = stripped[3:].strip() or "plain text"
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code = "\n".join(buf)
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"type": "text",
                                   "text": {"content": code[:MAX_TEXT]}}],
                    "language": lang if lang in _NOTION_LANGS else "plain text",
                },
            })
            continue

        # blank line
        if not stripped:
            i += 1
            continue

        # divider
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # table
        if stripped.startswith("|") and i + 1 < n and re.match(
            r"^\s*\|?[\s:\-|]+\|?\s*$", lines[i + 1]
        ):
            tbl_lines = []
            while i < n and lines[i].strip().startswith("|"):
                tbl_lines.append(lines[i].strip())
                i += 1
            blocks.append(_table_block(tbl_lines))
            continue

        # headings
        m = re.match(r"^(#{1,3})\s+(.*)", stripped)
        if m:
            level = len(m.group(1))
            blocks.append(_block(f"heading_{level}", m.group(2)))
            i += 1
            continue

        # blockquote (merge consecutive)
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append(_block("quote", "\n".join(buf)))
            continue

        # bulleted list
        m = re.match(r"^[-*+]\s+(.*)", stripped)
        if m:
            blocks.append(_block("bulleted_list_item", m.group(1)))
            i += 1
            continue

        # numbered list
        m = re.match(r"^\d+\.\s+(.*)", stripped)
        if m:
            blocks.append(_block("numbered_list_item", m.group(1)))
            i += 1
            continue

        # paragraph (merge consecutive non-blank, non-special lines)
        buf = [line]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith(("#", ">", "```", "|", "- ", "* ", "+ "))
                    or re.match(r"^\d+\.\s", nxt)
                    or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", nxt)):
                break
            buf.append(lines[i])
            i += 1
        blocks.append(_block("paragraph", " ".join(b.strip() for b in buf)))

    return blocks


def _table_block(tbl_lines: list[str]) -> dict:
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    header = cells(tbl_lines[0])
    rows = [cells(r) for r in tbl_lines[2:]]  # skip separator row
    width = len(header)

    def row_block(vals: list[str]) -> dict:
        vals = (vals + [""] * width)[:width]
        return {
            "type": "table_row",
            "table_row": {"cells": [rich_text(v) for v in vals]},
        }

    children = [row_block(header)] + [row_block(r) for r in rows]
    return {
        "object": "block", "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": True,
            "has_row_header": False,
            "children": children,
        },
    }


_NOTION_LANGS = {
    "plain text", "python", "javascript", "typescript", "bash", "shell",
    "json", "yaml", "markdown", "html", "css", "sql", "ruby", "go",
}


# --------------------------------------------------------------------------- #
# Sync manifest (shared with notion_sync)                                       #
# --------------------------------------------------------------------------- #
def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def md_hash(md: str) -> str:
    """Hash of a page's rendered markdown — the content fingerprint we compare
    against to tell whether Notion actually changed (vs a timestamp drift)."""
    return hashlib.sha256(md.encode()).hexdigest()


def stage_baseline(page_id: str, notion_edit: str, notion_md: str,
                   repo_file: Path) -> dict:
    """The per-stage in-sync baseline. Single source of truth for the manifest
    entry shape, so every push/pull/seed/re-baseline writes the same fields."""
    return {
        "page_id": page_id,
        "notion_edit": notion_edit,
        "notion_md_hash": md_hash(notion_md),
        "repo_hash": file_hash(repo_file),
    }


def load_manifest(folder: Path) -> dict:
    f = folder / MANIFEST
    if f.exists():
        return json.loads(f.read_text())
    return {"parent": None, "stages": {}}


def save_manifest(folder: Path, m: dict) -> None:
    (folder / MANIFEST).write_text(json.dumps(m, indent=2) + "\n")


def notion_pages_by_title(token: str, parent: str) -> dict[str, dict]:
    res = api_call(token, "GET", f"/blocks/{parent}/children?page_size=100")
    time.sleep(RATE)
    out = {}
    for b in res.get("results", []):
        if b.get("type") == "child_page":
            out[b["child_page"]["title"]] = {
                "id": b["id"],
                "last_edited": b.get("last_edited_time", ""),
            }
    return out


# --------------------------------------------------------------------------- #
# Notion blocks -> markdown (page rendering, used by push re-baseline + sync)  #
# --------------------------------------------------------------------------- #
def rt_to_md(rich: list[dict]) -> str:
    out = []
    for seg in rich:
        t = seg.get("plain_text", "")
        ann = seg.get("annotations", {})
        href = seg.get("href")
        if ann.get("code"):
            t = f"`{t}`"
        if ann.get("bold"):
            t = f"**{t}**"
        if ann.get("italic"):
            t = f"*{t}*"
        if href:
            t = f"[{t}]({href})"
        out.append(t)
    return "".join(out)


def fetch_children(token: str, block_id: str) -> list[dict]:
    blocks, cursor = [], None
    while True:
        path = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        res = api_call(token, "GET", path)
        time.sleep(RATE)
        blocks.extend(res.get("results", []))
        if res.get("has_more"):
            cursor = res.get("next_cursor")
        else:
            break
    return blocks


def blocks_to_md(token: str, block_id: str, indent: int = 0) -> list[str]:
    lines: list[str] = []
    pad = "  " * indent
    num = 0
    for blk in fetch_children(token, block_id):
        bt = blk.get("type")
        data = blk.get(bt, {})
        rich = data.get("rich_text", [])
        text = rt_to_md(rich)

        if bt == "numbered_list_item":
            num += 1
        else:
            num = 0

        if bt == "paragraph":
            lines.append(pad + text if text else "")
        elif bt in ("heading_1", "heading_2", "heading_3"):
            hashes = "#" * int(bt[-1])
            lines.append(f"{hashes} {text}")
        elif bt == "bulleted_list_item":
            lines.append(f"{pad}- {text}")
        elif bt == "numbered_list_item":
            lines.append(f"{pad}{num}. {text}")
        elif bt == "to_do":
            box = "x" if data.get("checked") else " "
            lines.append(f"{pad}- [{box}] {text}")
        elif bt == "quote":
            for ln in (text or "").split("\n"):
                lines.append(f"> {ln}")
        elif bt == "callout":
            emoji = (data.get("icon") or {}).get("emoji", "")
            lines.append(f"> {emoji} {text}".rstrip())
        elif bt == "divider":
            lines.append("---")
        elif bt == "code":
            lang = data.get("language", "")
            lines.append(f"```{lang}")
            lines.append(rt_to_md(data.get("rich_text", [])))
            lines.append("```")
        elif bt == "table":
            lines.extend(_table_to_md(token, blk["id"]))
            continue  # children already consumed
        elif bt == "child_page":
            continue  # don't descend into nested pages
        else:
            if text:
                lines.append(pad + text)

        if blk.get("has_children") and bt not in ("table", "child_page"):
            lines.append("")  # breathing room before nested content
            lines.extend(blocks_to_md(token, blk["id"], indent + 1))

        # blank line after block-level prose for readability
        if bt in ("paragraph", "heading_1", "heading_2", "heading_3",
                  "quote", "callout", "code", "divider"):
            lines.append("")

    return lines


def _table_to_md(token: str, table_id: str) -> list[str]:
    rows = fetch_children(token, table_id)
    md_rows = []
    for r in rows:
        cells = r.get("table_row", {}).get("cells", [])
        md_rows.append("| " + " | ".join(rt_to_md(c) for c in cells) + " |")
    if not md_rows:
        return []
    width = md_rows[0].count("|") - 1
    sep = "| " + " | ".join(["---"] * width) + " |"
    return [md_rows[0], sep] + md_rows[1:] + [""]


def page_to_markdown(token: str, page_id: str) -> str:
    lines = blocks_to_md(token, page_id)
    # collapse 3+ blank lines to 1, strip trailing
    out, blanks = [], 0
    for ln in lines:
        if ln.strip() == "":
            blanks += 1
            if blanks > 1:
                continue
        else:
            blanks = 0
        out.append(ln.rstrip())
    return "\n".join(out).strip() + "\n"


def rebaseline_manifest(token: str, folder: Path, parent: str,
                        artifacts: list[tuple[str, Path]]) -> None:
    """Record the just-pushed stages as the in-sync baseline.

    Only the pushed stages are touched. Re-fetches the live pages once to
    capture fresh ids/timestamps, and renders each to markdown so the baseline
    carries its notion_md_hash for content-based change detection."""
    manifest = load_manifest(folder)
    manifest["parent"] = parent
    pages = notion_pages_by_title(token, parent)
    for title, f in artifacts:
        info = pages.get(title, {})
        pid = info.get("id")
        notion_md = page_to_markdown(token, pid) if pid else ""
        manifest["stages"][f.name] = stage_baseline(
            pid, info.get("last_edited", ""), notion_md, f)
    save_manifest(folder, manifest)


# --------------------------------------------------------------------------- #
# Push                                                                          #
# --------------------------------------------------------------------------- #
def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def create_page(token: str, parent: str, title: str, md: str) -> str:
    """Create a new stage sub-page from markdown. Returns the new page id."""
    blocks = md_to_blocks(md)
    first, rest = blocks[:100], blocks[100:]
    page = api_call(token, "POST", "/pages", {
        "parent": {"page_id": parent},
        "properties": {"title": [{"text": {"content": title}}]},
        "children": first,
    })
    pid = page["id"]
    for batch in chunked(rest, 100):
        api_call(token, "PATCH", f"/blocks/{pid}/children", {"children": batch})
        time.sleep(0.34)
    return pid


def _clear_page_children(token: str, page_id: str) -> int:
    """Delete every direct child block of a page. Returns the count deleted.

    Collects ids across all pages of children first, then deletes — so we never
    mutate the list while paginating it."""
    ids: list[str] = []
    cursor = None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        res = api_call(token, "GET", path)
        ids.extend(b["id"] for b in res.get("results", []))
        if res.get("has_more"):
            cursor = res.get("next_cursor")
        else:
            break
    for bid in ids:
        api_call(token, "DELETE", f"/blocks/{bid}")
        time.sleep(0.34)
    return len(ids)


def update_page_in_place(token: str, page_id: str, title: str, md: str) -> None:
    """Replace a stage page's title + body without recreating the page.

    Keeps the page id, URL, and position among its siblings. Replaces the whole
    body, so block-anchored (inline) comments clear — by design; they are
    reviewed and folded into the repo before a push."""
    api_call(token, "PATCH", f"/pages/{page_id}",
             {"properties": {"title": [{"text": {"content": title}}]}})
    _clear_page_children(token, page_id)
    for batch in chunked(md_to_blocks(md), 100):
        api_call(token, "PATCH", f"/blocks/{page_id}/children",
                 {"children": batch})
        time.sleep(0.34)


def push_stage(token: str, parent: str, title: str, md: str,
               existing: dict[str, dict]) -> str:
    """Update the sub-page with this title in place if it exists, else create.

    `existing` is the title -> {"id", "last_edited"} map from
    notion_pages_by_title. Returns the page id (unchanged on update)."""
    info = existing.get(title)
    if info:
        update_page_in_place(token, info["id"], title, md)
        return info["id"]
    return create_page(token, parent, title, md)


def page_last_edited(token: str, page_id: str) -> str:
    """The page's current last_edited_time (one GET /pages call)."""
    return api_call(token, "GET", f"/pages/{page_id}").get("last_edited_time", "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="reflection folder, e.g. reflections/2026-01-01-my-text")
    ap.add_argument("--parent", required=True,
                    help="Notion parent page id (share the page with your integration first)")
    ap.add_argument("--stage", help="only this stage, e.g. 03 (updates just that sub-page in place)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"Not a directory: {folder}")

    artifacts = []
    for f in sorted(folder.glob("[0-9][0-9]-*.md")):
        num = f.name[:2]
        title = STAGE_TITLES.get(num, f.stem)
        artifacts.append((title, f))

    if args.stage:
        want = args.stage.zfill(2)
        artifacts = [(t, f) for t, f in artifacts if f.name[:2] == want]
        if not artifacts:
            sys.exit(f"No stage {want} artifact (NN-*.md) found in {folder}")

    if not artifacts:
        sys.exit(f"No NN-*.md stage artifacts found in {folder}")

    print(f"Reflection: {folder}")
    print(f"Parent page: {args.parent}")
    print(f"Artifacts ({len(artifacts)}):")
    for title, f in artifacts:
        print(f"  {title:24}  <- {f.name}")

    if args.dry_run:
        print("\n[dry-run] no changes made.")
        # show block counts to sanity-check the converter
        for title, f in artifacts:
            blocks = md_to_blocks(f.read_text())
            print(f"  {title:24}  -> {len(blocks)} blocks")
        return

    token = get_token()
    pages = notion_pages_by_title(token, args.parent)

    print("\nPushing (in place where the sub-page already exists)...")
    for title, f in artifacts:
        pid = push_stage(token, args.parent, title, f.read_text(), pages)
        print(f"  ✓ {title:24}  {pid}")
        time.sleep(0.34)

    rebaseline_manifest(token, folder, args.parent, artifacts)
    print(f"  ✓ re-baselined {MANIFEST} ({len(artifacts)} stage(s))")

    print("\nDone.")


if __name__ == "__main__":
    main()
