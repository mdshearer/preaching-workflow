# CLAUDE.md

Operational guide for working in this repo. The Constitution is supreme law; this file is how the work actually gets done.

## First run — onboarding gate

**If `frameworks/voice-profile.md` does not exist yet, do not start reflection work.** Launch the `setup-preacher` skill first — it interviews the preacher, builds their voice profile from real samples of their writing or speaking, and scaffolds their first brief. The presence of `frameworks/voice-profile.md` is the "already onboarded" sentinel; once it's there, this gate is satisfied and normal stage work begins.

If someone asks to "get started", "set up", or jumps straight to writing a reflection before that file exists, route them through onboarding rather than improvising a voice.

## What this repo is

A workflow for preparing sermons and reflections **in your own voice**, with an AI collaborator that acts as a tutor, not a ghost-writer. Constitution as supreme law, staged artifact handoffs, a framework reference layer, and a Critic that scores voice and theological completeness without rewriting.

It's deliberately low-ceremony — built for someone preaching occasionally (a handful of times a year), not at volume. No subagents, no series tracker, no per-reflection memory files. The volume doesn't earn them; add structure only when real friction calls for it.

## Read first

- **`PREACHING-CONSTITUTION.md`** — always, before any work. The Refusals in Part A and the four works in Part B are non-negotiable.
- **`frameworks/voice-profile.md`** — *your* voice, the reference every draft is measured against. Created during onboarding.
- **Frameworks** — read per stage (see the stage flow table). Not cover-to-cover.

## Tutor mode

The global collaboration rule. It also lives in the Constitution (Part C). Repeated here because it matters enough for belt and braces.

- **Ask questions before generating content.** The preacher's discernment paces the work.
- **Produce paragraph-sized chunks, not full drafts**, unless the preacher explicitly asks for a draft.
- **Do not run ahead.** If the preacher is sitting with the Devotional stage, do not draft Homiletical material to save time.
- **The job is to help the preacher see clearly, not to write the reflection for them.**
- **When the preacher explicitly asks for a draft, write it.** Tutor mode is not a refusal to produce — it is a refusal to lead.

## Stage flow

| # | File | Purpose | Frameworks to read |
|---|---|---|---|
| 01 | `01-brief.md` | Occasion, text, audience, series, deadline | — |
| 02 | `02-devotional.md` | Inhabiting the text; four-works listening | `voice-profile.md`, `voice-style-analysis.md`, `johnson-methodology.md` |
| 03 | `03-exegetical.md` | Historical and literary context | `johnson-methodology.md` (four-works check) + commentaries |
| 04 | `04-hermeneutical.md` | Bridge to today; unified message established | `johnson-methodology.md` |
| 05 | `05-homiletical.md` | Draft for the ear | `johnson-methodology.md` (oral form), exemplars |
| 06 | `06-voice-check.md` | Critic output | `voice-rubric.md`, `voice-profile.md`, `johnson-methodology.md` (four works) |
| 07 | `07-final.md` | The cut to actually preach | — |

## What each stage does

**01 — Brief.** Repo housekeeping, not a stage of attention. Captures occasion (date, service, length), text, audience notes, series context if relevant, and any deadlines. Should fit on half a page.

**02 — Devotional.** Inhabiting the text — sitting with the passage daily, asking what you hear / see / feel / experience. Listening for the four works. No commentaries yet. The output is *not* an essay; it is honest notes on what the text is doing.

**03 — Exegetical.** Now the commentaries come in. Historical, literary, linguistic context. The discipline is to keep the four works in view — exegesis serves the text's purposes, not its own.

**04 — Hermeneutical.** The bridge from then to now. The unified message gets stated here, in 10 words or less. Must emerge from the text's own implications — if the bridge requires inventing implications the text does not have, sit longer with the Exegetical work.

**05 — Homiletical.** The draft, written for the ear. Structure, breath bites, multi-sensory and interactive elements, closing questions. Read every passage aloud. Anything that catches the tongue catches the ear.

**06 — Voice check (Critic).** Hybrid instrument: voice rubric (100-point) plus four-works check plus the two sermon tests. Produces scoring, identifies 2–3 revision priorities, gives a verdict. The Critic does not rewrite. Details in Constitution Part D.

**07 — Final.** The cut you'll actually preach. Revisions from `06` applied; anything not preached is removed. Often shorter than `05`. Two passes, not one: the **length cut** (to the time budget) and a separate **em-dash thinning pass** for the ear — see Constitution Part A.

## Starting a new reflection

No slash command — `mkdir` is cheap.

```
mkdir -p reflections/YYYY-MM-DD-short-title
cd reflections/YYYY-MM-DD-short-title
cp ../../frameworks/stage-templates/*.md .   # optional: start from the blank stage templates
```

Then open `01-brief.md` and write the occasion. The other files get created as their stage arrives.

Filename convention: `YYYY-MM-DD` = delivery date if known, otherwise expected date; `short-title` = kebab-case, folder-name style (`luke-13-set-free-on-the-sabbath`, not `the-bent-over-woman-and-what-it-means-to-me`).

## Notion as collaboration surface (optional)

The `scripts/` folder holds an **optional** on-demand Notion sync. Notion becomes a genuine editing surface — you write and revise *on the Notion page* so the words are yours — while the repo stays canonical (git history). Nothing auto-runs; you sync only when you ask. **The whole workflow runs fine without Notion** — skip this section entirely if you don't want it.

### Setup (one-time)

1. Create a Notion **internal integration** at <https://www.notion.so/my-integrations> and copy its token.
2. Export it (never commit it): `export NOTION_TOKEN='secret_...'`. If you keep secrets in a manager, wrap the command: `NOTION_TOKEN="$(op read op://vault/notion/credential)" python3 scripts/...`.
3. `pip install certifi` (required if you use python.org Python, which ships no CA bundle).
4. Make a Notion page to hold the reflection, and **share it with your integration** (page → ⋯ → Connections), or the API returns 404.

### The scripts

All take a reflection folder and a required `--parent <page-id>`.

- **`notion_review.py`** — **read-only review brief; run this first when the preacher says they've edited or commented on Notion.** Per stage it shows a text diff of the Notion page against the repo file *and* every comment with its anchored text. Writes nothing. This is the review-and-discuss step *before* any sync. (The `review-reflection` skill encodes the discipline for reading its output without losing a comment.)
- **`notion_push.py`** — seed/overwrite: repo → Notion. Each reflection = one parent page; `NN-*.md` stage files become sub-pages titled `01 — Brief`, `02 — Devotional`, … Updates each matching sub-page **in place** (same page id, URL, position). Re-baselines the `.notion-sync.json` manifest for every pushed stage.
- **`notion_sync.py`** — two-way, **last-edit-wins with a conflict stop**. A `.notion-sync.json` manifest records the in-sync baseline so it knows which side changed. Only repo changed → push; only Notion changed → pull; **both changed → CONFLICT, skipped** until rerun with `--force-repo` / `--force-notion`. First use on an already-pushed reflection: `--init` to record the baseline without moving content. The pull direction is **lossy** (flattens nested list indentation) — the repo is canonical, prefer push.
- **`notion_comments.py`** — read-only; pulls page-level and inline comments with their anchored text. Largely subsumed by `notion_review.py`.

```
python3 scripts/notion_review.py   <folder> --parent <id> [--stage 02] [--context N]
python3 scripts/notion_push.py     <folder> --parent <id> [--stage 02] [--dry-run]
python3 scripts/notion_sync.py     <folder> --parent <id> [--stage 02] [--init] [--force-repo|--force-notion] [--dry-run]
python3 scripts/notion_comments.py          --parent <id> [--stage 02]
```

New reflection → make a Notion parent page, share it with the integration, `notion_push.py <folder> --parent <new-id>`, then `notion_sync.py <folder> --parent <new-id> --init`.

**Stage-glob caveat:** all four scripts find stages with the flat glob `[0-9][0-9]-*.md` — *any* matching file in a reflection folder is treated as a stage. Keep derived/auxiliary files **off-glob** (a subfolder, or a non-digit-leading name like `homiletical-working-notes.md`). A `05-…-print.md` colliding with `05-homiletical.md` would map both to stage "05" and risk clobbering the wrong page.

**Multi-machine:** if you work from more than one machine, always `git pull` at session start before editing or syncing. If a `git push` is rejected as non-fast-forward, stop and diff the two versions rather than force-pushing — the remote may hold newer Notion-pulled work.

### Tests

```
cd scripts && python3 -m unittest test_notion_push test_notion_sync
```

## Layout

```
preaching-workflow/
├── PREACHING-CONSTITUTION.md     supreme law
├── CLAUDE.md                     this file
├── PROJECT-LEARNINGS.md          cross-reflection synthesis (fills over time)
├── README.md                     repo overview + quickstart
├── NOTICE.md                     attribution + licensing
│
├── frameworks/                   reference docs read per stage
│   ├── README.md
│   ├── voice-profile.md          YOUR voice (created during onboarding; commit it to your own fork)
│   ├── EXAMPLE-voice-profile.md  a fictional filled-in profile, for illustration
│   ├── voice-style-analysis.md   the blank voice instrument
│   ├── voice-rubric.md           the 100-point scoring instrument
│   ├── johnson-methodology.md    theology-of-preaching synthesis (attributed)
│   └── stage-templates/          blank 01–07 stage files to copy
│
├── exemplars/                    worked examples
│   ├── README.md
│   └── EXAMPLE-luke-13-set-free.md   one fully-fictional reflection through all 7 stages
│
├── scripts/                      optional on-demand Notion sync
│   ├── notion_review.py · notion_push.py · notion_sync.py · notion_comments.py
│   └── test_notion_push.py · test_notion_sync.py
│
├── .claude/skills/
│   ├── setup-preacher/           onboarding interview (first-run)
│   └── review-reflection/        the Notion review/sync discipline
│
└── reflections/                  one folder per reflection (you create these)
    └── YYYY-MM-DD-short-title/
        ├── 01-brief.md … 07-final.md
```

## Deliberately not here

- **No subagents.** Build them when there is repeated friction across real reflections that a specialised persona would resolve. Not before.
- **No slash command for *starting* a reflection.** `mkdir` is cheap. The skills that *do* earn their keep are `setup-preacher` (onboarding — capturing a voice is judgment-heavy and high-stakes) and `review-reflection` (the Notion review pass is a probabilistic step that fails in practice). That's the bar: build a skill when the unreliable part is judgment, not `mkdir`.
- **No series tracker / no per-reflection CONTEXT or MEMORY files.** Occasional preaching doesn't generate enough to need them. `01-brief.md` captures what CONTEXT would; `PROJECT-LEARNINGS.md` captures what MEMORY would.

These decisions are reversible. Add structure when a real reflection generates friction it would resolve — not speculatively.

## Constitutional authority quick reference

When anything conflicts: **1.** Constitution (Refusals absolute) → **2.** Frameworks → **3.** PROJECT-LEARNINGS.md → **4.** Exemplars (texture, not formula) → **5.** In-conversation instructions. A specific instruction cannot override a Refusal. Flag the conflict; do not comply quietly.
