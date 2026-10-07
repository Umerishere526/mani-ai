---
type: journal
date: 2026-10-06
apps: [backend]
tags: [journal, backend, prompts, lessons]
---

# Building spec 0011 (Lolly's review): what bit

- **A rule can live in two prompts.** The "never say its name" rule was in `mani_base.md` and again in `composer.framework_index`'s closing line. Changing only the base prompt would have sent the model two contradicting instructions. When a prompt rule changes, grep `mani/prompts/composer.py` and `context.py` notes for the same rule.
- **A guard written for a path outlives the path.** The check in block skipped the body question whenever the model's own text asked "what would you like to do next", which only made sense for the old described early route. With that route gone, a model asking "what next" at the end of a framework would have skipped the mandatory somatic step. Found because a test scripted exactly that reply.
- **Order of locals in `orchestrator.send` matters.** `their_question` read `skipped` before it was assigned; only an integration test reached the path. Compute new turn flags next to the ones they depend on.
- **"What do you mean?" is not their question.** It is the client's request to hear the step again, which has its own hold. Anything keyed on "?" in their message must exclude `context.asks_to_hear_again`.
- **Test replies are examples too.** A scripted reply "A lot of people wonder that." modelled the general claim the new prompt forbids. Scripted model text should be something Mani is allowed to say.
- **The base prompt cap is real pressure.** The new rules needed 138 lines against 130 after tightening; the cap was raised by exactly that, never by compressing safety or clinical lines.

Related: [[lolly-meetings-chat-objections-land-on-her-own-lines-2026-10-06]], [[client-documents-build-lessons-2026-10-06]].
