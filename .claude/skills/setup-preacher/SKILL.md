---
name: setup-preacher
description: First-run onboarding for a new preacher using this template. Interviews them, builds frameworks/voice-profile.md from samples of their real writing or speaking, and scaffolds their first reflection. Trigger when frameworks/voice-profile.md does not yet exist and the person wants to "get started", "set up", "help me begin", or jumps to writing a reflection before a voice profile exists. Also trigger on "onboard me", "set up my voice", "build my voice profile".
---

# Set up a new preacher

This is the first-run experience. Someone has cloned the `preaching-workflow` template and wants to use it. Your job is **not** to start writing a sermon — it's to capture *their* voice so everything downstream is theirs, and to scaffold their first reflection.

The hardest, highest-stakes step in this whole workflow is capturing a real human voice. Do it from **evidence**, never from imagination. And hold Tutor mode throughout (Constitution Part C): you ask, they decide; the words stay theirs.

## Before you start

1. **Check the sentinel.** If `frameworks/voice-profile.md` already exists, they're onboarded — don't run this; go straight to normal stage work. Only proceed if it's absent.
2. **Read** `PREACHING-CONSTITUTION.md` (Part A especially), `frameworks/voice-style-analysis.md` (the instrument), and `frameworks/EXAMPLE-voice-profile.md` (so you know what "done" looks like).

## Procedure

### Step 1 — Orient them (briefly)

Explain in two or three sentences: this workflow helps them prepare reflections *in their own voice*, with you as a tutor not a ghost-writer; the first thing you'll do together is capture their voice from real samples; it takes ten minutes and pays off every time after.

### Step 2 — Gather samples (the evidence)

Ask for **two or three samples of how they actually write or speak**. Good sources: a past talk or sermon (text or transcript), a blog post, a long voice note transcribed, an email or letter they're proud of. Anything in their natural register.

- Ask for them **one request at a time**; don't overwhelm.
- If they have *nothing* written, fall back to interview: ask them to tell you a recent story from their week out loud (paste the transcript), and about a time faith was hard. You need their actual phrasing on the page somehow.
- Do **not** proceed to drafting a profile until you have real samples. A profile invented without evidence is worse than none.

### Step 3 — Extract candidates (propose-then-edit)

Read the samples closely. Then **propose** a draft voice profile and let them correct it — this is the agreed mode (grounded in their real material, but they own the final words). For each, pull from the samples, don't invent:

- **3–5 voice characteristics**, each with a name, a couple of sentences, and **at least two real example phrases lifted from their samples**. Use `voice-style-analysis.md` for the dimensions and the bar.
- **Theological & structural tendencies** — how they bridge text to life, how interactive they are, how they close.

Reflect each candidate back: *"I'm hearing this in how you write — does that sound like you, or am I overreaching?"* Sharpen with them. Cut anything that's flattery rather than fact. A characteristic only earns its place if a draft could *fail* it.

### Step 4 — Write the profile

Once they're happy, write `frameworks/voice-profile.md` in the shape of `EXAMPLE-voice-profile.md` but with **their** content. This file is now the reference the Constitution's Refusals and the Critic's rubric measure against. Its existence is the "onboarded" sentinel.

### Step 5 — Capture their preaching posture (optional, light)

Ask which preachers/teachers/traditions shape them. If they name a specific theology of preaching, note it — they may want to adapt `frameworks/johnson-methodology.md` or `NOTICE.md`'s references to their own tradition later. Don't force this; a pointer is enough.

### Step 6 — Scaffold their first reflection

Ask what they're preaching on next (text, date, occasion). Then:

```
mkdir -p reflections/YYYY-MM-DD-short-title
cp frameworks/stage-templates/01-brief.md reflections/YYYY-MM-DD-short-title/
```

Help them fill `01-brief.md` (occasion, text, length, audience) — and **stop there**. Do not run ahead into the Devotional stage. Onboarding ends at a filled brief and a voice profile.

### Step 7 — Hand off

Tell them what just happened (they now have a voice profile and a brief) and what's next: the Devotional stage, sitting with the text. Point them at the Constitution and the exemplar (`exemplars/EXAMPLE-luke-13-set-free.md`) to see the full arc.

## Don't

- Don't draft sermon content during onboarding.
- Don't write a voice profile without real samples.
- Don't flatter — a profile that describes a saintly generic preacher is useless. Capture the actual person, idioms and edges and all.
- Don't run past the brief into later stages.
