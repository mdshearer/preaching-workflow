# preaching-workflow

A workflow for preparing sermons and reflections **in your own voice**, with an AI collaborator (Claude Code) that works as a *tutor*, not a ghost-writer.

It gives you a staged process (devotional → exegetical → hermeneutical → homiletical → critique → final cut), a "Constitution" that refuses the ways AI-assisted preaching tends to go wrong, and a Critic that scores your draft on voice *and* theological completeness without rewriting a word of it. The point is not throughput. The point is to help you see the text — and your own voice — more clearly.

## Why it exists

AI will happily write you a sermon. The result is fluent, generic, and not yours — and it shortcuts the very work (sitting with a text until it grabs you) that preaching is supposed to be. This workflow inverts that: the AI asks questions, holds the discipline, and scores the draft, but **you** write the words. Your voice is captured up front from samples of how you actually speak and write, and every stage is measured against it.

## Quickstart

1. **Clone this repo** and open it in [Claude Code](https://claude.com/claude-code) (or another Claude coding agent).
2. Say: **"help me get started."** Claude runs the `setup-preacher` onboarding skill — it asks for two or three samples of your real writing or speaking, builds your `frameworks/voice-profile.md` from them, and scaffolds your first reflection's brief.
3. Work the stages with Claude in tutor mode: `01-brief` → `02-devotional` → … → `07-final`. Read the Constitution first.

That's it. No build step, no dependencies for the core workflow. (The optional Notion sync needs Python 3 + `certifi` — see `CLAUDE.md`.)

## What's in here

- **`PREACHING-CONSTITUTION.md`** — supreme law: voice non-negotiables, theological frame, process discipline, the Critic's scoring instrument. Read first.
- **`CLAUDE.md`** — the operational guide: stage flow, what to read at each stage, the optional Notion sync, the onboarding gate.
- **`frameworks/`** — the voice instrument, the 100-point voice rubric, a synthesis of Darrell Johnson's theology of preaching, blank stage templates, and an example voice profile.
- **`exemplars/`** — one fully-fictional worked reflection through all seven stages, so you can see the method end-to-end before you run it.
- **`scripts/`** — optional, on-demand Notion sync (treat Notion as an editing surface while the repo stays canonical).
- **`.claude/skills/`** — the onboarding interview and the Notion-review discipline.

## Make it yours

This is a **template**. The voice work is built to be filled with *your* voice — the example profile and exemplar use a fictional preacher you should replace. The theological frame draws on one particular teacher (Darrell Johnson); if you preach from a different tradition, swap the references and keep the discipline. See `NOTICE.md` for attribution and licensing.

## Licensing (short version)

- **Prose, frameworks, and docs:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — use and adapt freely, with attribution. See `LICENSE-CONTENT`.
- **Code (`scripts/`):** [MIT](https://opensource.org/license/mit) — see `LICENSE-CODE`.

Full attribution and a disclaimer of affiliation are in `NOTICE.md`.
