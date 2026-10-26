---
type: journal
date: 2026-10-22
tags: [journal, prompts, styles, voice, lessons]
---

> Superseded 2026-10-26 (no example conversation in any style file: Directive now carries Lolly's two ChatGPT chats) - see [[heart-of-it-replaces-the-three-steps-2026-10-26]].

# The three styles read the same (2026-10-22)

muhammad: Directive, Supportive and Reflective felt 100 percent the same.

## Cause (hypothesis, not measured)

`mani_base.md` gave one voice to every style: the client's sample conversation (`example`, "Copy how it talks") and a
line that blended Supportive and Reflective for everyone ("Supportive but not over-reassuring, curious but not
interrogating"). Each style file was one sentence, so the model, which follows examples over rules
([[client-sample-voice-and-confirmed-check-2026-10-13]]), copied the sample in all three.

## What changed

- Removed the `example` and the blending line from `mani_base.md`; the shared shape stays (mirror, one question,
  options, two to five short sentences, banned phrases, no dashes). The base prompt went from 11062 to 9170 characters.
- Each style file now carries the client's one-line summary, what each reply is for, what to do and avoid, the
  reply shape it reaches for (`reply_shapes`, which the `style` field records first) and how it differs from the other
  two. No example conversations: they were removed on 2026-10-13 because they competed with the shared sample, and
  muhammad chose descriptions only.
- Deleted the scenario flag for the example's borrowed details (`borrowed_from_the_example`) with its test.

## muhammad's drafts, and what was changed in them

His own drafts gave Directive and Supportive advice and next steps, Reflective underlying beliefs, Supportive named
feelings and invented strengths ("That sounds really discouraging", "it doesn't erase the work you've put in"), and
told Directive not to restate. Each breaks a rule that binds Mani (no advice they did not ask for, never name a feeling
they did not use, the client's Reflective list "does not introduce meanings, emotions, motives or conclusions the user
has not expressed", a reply before the check ends on one question). They also quoted stock phrases and examples, which
the client says never to use to signal a style and which the model copies. Kept: the structure and the client's wording.

## Still to learn

Not run against the real model. Run `scenario_check.py` on one scenario in all three styles (cost stated and muhammad's
yes first) to see whether the voices differ, and whether the case-note voice came back. If the styles still match, the
next step is one short client conversation per style, not more rules.

See [[styles-from-client-document-2026-10-12]], [[measure-before-tuning-prompts]].
