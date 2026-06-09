---
name: review-reflection
description: Review the Notion edits and comments on a reflection before folding anything back into the repo. Encodes the read-only review-and-discuss pass so the probabilistic step (reading a long diff, never losing a comment, telling real edits from render noise) is reliable. Trigger on "review the notion edits", "check notion", "review the comments and edits", "is notion up to date", "what did I change on notion", "pull the feedback", "review the reflection", or before any notion_sync. Only relevant if you use the optional Notion sync.
---

# Review a reflection's Notion edits & comments

The read-only step that sits **before** any sync. It surfaces what changed on
Notion and every comment, you discuss each with the preacher, *then* you apply to
the repo and push deliberately. Nothing is written until they say so.

This skill exists because the probabilistic half (reading the output) tends to
fail in characteristic ways: a comment at the end of a long diff gets nearly
lost; a truncated Read is misread as a crashed script; intentional line-breaks
are dismissed as whitespace. The steps below are the guardrails against exactly
those.

(Only relevant if you've set up the optional Notion sync in `scripts/` — see
`CLAUDE.md`. The export `NOTION_TOKEN` must be set, and the parent page id is
required as `--parent`.)

## Procedure

1. **`git pull --ff-only` first** if you work from more than one machine; stage
   drafts have collided. If a later push is rejected non-fast-forward, **stop**
   and `git diff main:<file> origin/main:<file>` — never force-push; the remote
   may hold newer Notion-pulled work.

2. **Run the review, capturing the full output to a file:**
   ```
   python3 scripts/notion_review.py reflections/<folder> --parent <id> >/tmp/review.txt 2>&1
   ```

3. **Consume the WHOLE file — never a single Read.** The output can be large and
   the Read tool truncates. A single Read silently drops the end, which is where
   comments live. Always grep the structure first:
   ```
   grep -nE "COMMENTS SUMMARY|on:|•|^===|✓ Notion and repo match" /tmp/review.txt
   ```
   then page through with `Read offset=…` / `sed -n` for the sections you need.
   If the script ever looks "cut off", check `wc -l` and exit code before
   concluding it failed — a truncated *view* is not a broken *script*.

4. **Lead with the COMMENTS SUMMARY** (printed at the top, full anchors).
   Comments are *others'* feedback → they feed a **repo edit**, never a direct
   Notion edit, and they vanish on re-push. Surface every one with its anchored
   sentence. A comment without its sentence is noise — always pair them.

5. **Classify every diff line. Do not dump the raw diff at the preacher.**
   - **Render noise — ignore:** blank lines collapsed, `**bold**` stripped inside
     italics, heading whitespace. Notion's renderer, not an edit.
   - **Intentional line-breaks — REAL, keep:** a new paragraph break added for a
     spoken pause/hold. These *look* like whitespace but are delivery beats. When
     unsure whether a break is noise or a hold, **ask** — do not assume.
   - **Real content edits — REAL:** rewordings, cuts, insertions, checkbox flips.
   - **Repo-ahead vs Notion-ahead:** content in the repo but missing on Notion
     (`-` only) usually means the repo is *ahead* (written after the last push) —
     a **push** candidate, not feedback to fold back. Content on Notion missing
     from the repo (`+`) is a **Notion edit to fold back**. Say which is which.

6. **Tutor mode holds.** Present findings, discuss each, let the preacher decide.
   Do not apply, sync, or overwrite without an explicit go-ahead. Do not run
   ahead to later stages.

7. **Only after agreement:** apply the kept edits to the repo file(s), then push
   (or `notion_sync.py --force-repo` / `--force-notion`). Before forcing either
   direction, re-confirm with `notion_review.py` which side holds the wanted
   content — a `--force` discards the other side.
