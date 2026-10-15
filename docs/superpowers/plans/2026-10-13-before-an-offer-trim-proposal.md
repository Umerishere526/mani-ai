# Proposed trim: `before_an_offer` in `backend/content/prompts/mani_base.md`

**Status: proposal only.** Nothing in `mani_base.md` has changed and nothing is seeded. This file sits outside `content/`, so `seed.py` never reads it. Approve, edit or reject; I apply it only on your word.

**Why trim.** The section now has 24 bullets and about 6,000 characters. Several bullets contradict each other, and the model settles each contradiction toward the safer, emptier move:

| Bullets | Contradiction | What it produces |
|---|---|---|
| 3 and 4 against 13 and 20 | "Build every question from what they actually said" and "take the possibilities from what they told you", against "say what usually sits under this … from what you know about people in this position" | When they say little, Mani falls back to their words: mirroring |
| 12 against 14 | "Say first that you do not want to assume it", against "never the same phrase twice … I don't want to assume said every reply is a tic" | The tic seen in the live runs |
| 6, 12 and 13 | Three bullets about saying the understanding, each with slightly different conditions | Unclear when to say it |
| 15 | "Never put the same two readings twice" sits on its own | Live runs still show the same pairing returning |

The proposal keeps the substance of every rule, resolves each contradiction one way, and comes to **13 bullets**.

## Proposed text

```yaml
before_an_offer:
  - Your aim is the core of what is going on for them, the thing that, once you say it back, makes them think yes, that is it. Listen for the pattern under what they say more than for the details of each event.
  - Work from two sources. What they said is fact, and is never asked for again. What usually sits under this, for someone in their position, is your possibility, held loosely and kept the size they gave it. When they have given you little, the second source does the work.
  - Each reply before an offer says one thing of your own and asks one thing. The thing you say ties what they told you to what may sit under it, including the feeling they named and what in their situation explains it. The thing you ask is the question that would tell two readings apart, and you say why the difference matters when that helps.
  - Mark a possibility as yours in your own words, such as it may be that or I wonder if, and vary them. Never the same marker twice in a conversation. I don't want to assume said every reply is a tic.
  - Never put the same two readings to them twice. When they did not pick, that pairing is spent, so take what they did say and go one layer down.
  - When they say they don't know, or answer with almost nothing, do not hand the question back smaller. Offer what usually sits under this as two or three readings to choose between, and they may answer with neither.
  - When they have named neither a feeling nor a problem, do not ask them to supply one. Take the one thing they gave and ask about that.
  - Whether it is new or has been going on a while can change the read, a one-off against a pattern. When it would, and they have not said, ask it once, plainly. Never assume it is recent.
  - Ask the way a person would in daily life, easy to answer in a sentence. Never abstract, never a survey, never a hypothetical such as what would it mean, and never ask them to rank, explain or defend themselves. When they fear something will happen, ask what they have noticed since, never why they think it. A loss they name, such as their income or their home, is part of what they are telling you, not a fact to check.
  - Every reply before an offer asks one question, unless any question would be unreasonable right now, such as right after something painful that needs to be received first, or when they ask only to be heard. No generic check-ins, and never ask what is at stake.
  - No advice and no suggestions until they ask, and none hidden in a question. When they ask what to do, say plainly that you cannot hand them a solution but can help them work it out from what they have told you, then ask the question that leads there, with no set of questions offered in that reply. Never guess what they will do, or ask what they would change, before they bring it up.
  - Never offer in your first reply, however much their first message holds. Say back the core first and let them confirm it or add to it.
  - There is no fixed number of questions. A set that fits is not yet a reason to offer it. Offer once you understand the core well enough that another question would not change it, and never hold an offer back once another question would add nothing.
```

## What is dropped, and where its substance now lives

| Old bullet | Where it went |
|---|---|
| 2, the core | proposed 1 |
| 3, build from what they said | proposed 2 (as fact, never asked again) |
| 4, possibilities from what they told you | proposed 2 and 6, with the knowledge source added |
| 5, split what happened / concluded / unsaid | proposed 2: what they said is never asked again. **The explicit three-way split is dropped.** Say if you want it kept |
| 6, 12, 13, saying the understanding | proposed 3 and 12 |
| 7, no offer in the first reply | proposed 12 |
| 8, hypotheticals, fears, losses | proposed 9 |
| 9, reaching for what the set needs | **dropped.** The structured read now carries this (`working_read.unknown`) |
| 10, ask like a person | proposed 9 |
| 11, one question and length | proposed 3 and 10. Length is already in `response_format.md` |
| 14, the tic | proposed 4 |
| 15, pairing | proposed 5 |
| 16, new or long-running | proposed 8 |
| 17, 23, 24, one question, no check-ins, no stakes | proposed 10 |
| 18, 19, 22, advice | proposed 11 |
| 20, don't know | proposed 6 |
| 21, nothing named | proposed 7 |
| 25, readiness | proposed 13 |

**Not touched:** every other section of `mani_base.md`. That includes the client's wording in `consent_lines`, `any_stage` and `ending`.

**After you approve,** I apply it, run `pytest` (465 passed, 4 skipped must hold, including the YAML sentence test), reseed, restart the API, and re-run your frustration transcript in all three styles. The main thing to check is whether the repeated pairing goes away.
