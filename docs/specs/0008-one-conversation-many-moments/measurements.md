# 0008 measurements: what could be measured without Mani's model

- **Date:** 2026-11-16
- **Asked by:** muhammad: do the measurement in the sandbox and complete the research.
- **Status:** results. No code changed. Two conclusions of the 0008 design change because of them; see section 7.
  The design (`index.md`) and its review (`review.md`) were no longer in this folder when this was written, so the
  changes are listed here and not yet applied to them.

## What this is, and is not

Everything here ran in a scratch Linux shell with no model, no database and no key. That shell can reach PyPI and
github.com and cannot reach huggingface.co, so nothing that needs Mani's model or a downloaded classifier was run.
Section 8 lists what that leaves open.

| Source | What it is | Where it came from | Licence |
|---|---|---|---|
| The client's transcripts | 7 Mani chats and 2 ChatGPT chats, each with Lolly's or muhammad's verdict | `docs/client/messages/` (2026-10-18, 10-26, 11-03, 11-10) | ours |
| The two chats of 2026-11-16 | the boss chat and the safety test | pasted by muhammad; not yet in the repo | ours |
| ESConv | 1,300 emotional-support chats between crowd workers, each supporter turn labelled with a strategy, each chat rated by the person helped; plus 196 chats that failed its quality bar | github.com/thu-coai/Emotional-Support-Conversation | CC BY-NC 4.0 |
| AnnoMI | 133 transcribed counselling demonstrations, labelled high or low quality by experts, each therapist utterance labelled question, reflection or input | github.com/uccollab/AnnoMI | none stated in its README |
| C-SSRS labelled posts | 1,170 posts from r/SuicideWatch, each given a severity from 0 to 6 on the Columbia scale by the dataset's authors, plus the labels five language models gave | github.com/av9ash/llm_cssrs_code | CC BY 4.0 |

The posts are real people's words. They stayed in the scratch shell. Only counts are reported and nothing from them
is in the repo. The scripts were scratch too; section 8 says where they should live.

## 1. Lolly's verdict does not follow "ends on a question"

I had argued that forcing a question onto every reply was a main cause of "too many questions". The client's own
transcripts say otherwise.

| Group | Replies | End on a question | Words given before the last question (median) | Reply length (median words) | Her message length (median words) | Replies that apologise | Her pushbacks |
|---|---|---|---|---|---|---|---|
| Her target: two ChatGPT chats ("I wish mani sounded this way") | 24 | 96% | 49 | 68 | 12 | 4% | 0 of 24 messages |
| Mani chats she liked (3) | 33 | 94% | 38 | 50 | 36 | 18% | 7 of 33 |
| Mani chats she or muhammad disliked (6) | 64 | 86% | 24 | 36 | 8 | 28% | 19 of 64 |

Per conversation:

| Conversation | Verdict | Replies | End on a question | Reply words | Her words | Apologise |
|---|---|---|---|---|---|---|
| ChatGPT, boss (10-26) | her target | 12 | 92% | 74.5 | 16.5 | 0% |
| ChatGPT, friendship (10-26) | her target | 12 | 100% | 66 | 12 | 8% |
| Mani, email 1 (11-03) | "best direct conversation" | 17 | 94% | 56 | 30 | 29% |
| Mani, email 3 (11-03) | enjoyed until a timeout | 10 | 100% | 39 | 44 | 10% |
| Mani, email 4 (11-03) | enjoyed until a timeout and "fear" | 6 | 83% | 58.5 | 36 | 0% |
| Mani, email 2 (11-03) | "horrible" | 5 | 60% | 36 | 6 | 60% |
| Mani, sister loans (10-18) | twelve failures | 10 | 100% | 26.5 | 11 | 20% |
| Mani, chest, Lolly (11-10) | safety scared and repeated | 7 | 71% | 50 | 9 | 43% |
| Mani, chest, muhammad (11-10) | safety would not let go | 10 | 60% | 26 | 9.5 | 10% |
| Mani, boss (11-16) | thirteen failures | 15 | 100% | 34 | 5 | 27% |
| Mani, safety (11-16) | sixty failures | 17 | 94% | 42 | 10 | 29% |

What the numbers say:

- **The chats she holds up as the target ask a question in almost every reply.** So does the Mani chat she called
  the best. A question at the end is not what she objects to.
- **What moves with her verdict is how much the reply gives before it asks:** 49 words in her target, 38 in the
  Mani chats she liked, 24 in the ones she did not.
- **The disliked chats are the ones where she writes little:** a median of 8 words a message, against 36 in the
  liked Mani chats. ChatGPT met messages of a median 12 words and drew no pushback at all. Mani meets short
  messages with a short reply and another question.
- **Apologies go the same way:** 4%, 18%, 28%.

How the counts were made: the greeting, the style tap and the opener are left out. "Ends on a question" is the last
character. "Words given before" counts the words before the sentence holding the last question mark. Apologies and
pushbacks are word patterns, so they are rough; at least two of the pushbacks counted in the tables are plain
answers that begin with "no".

## 2. What people do when they support someone (ESConv)

| | |
|---|---|
| Supporter replies that end on a question, per conversation | median 36%; a quarter of conversations are under 24%, a quarter over 46%, one in ten over 60% |
| Conversations where every reply ends on a question | 4 of 1,300 |
| Conversations where at most half do | 82% |
| By thirds of the conversation | 60% of replies end on a question in the first third, 28% in the middle, 14% in the last |
| What replaces the question | suggestions rise from 7% of supporter turns in the first third to 24% in the middle; reassurance from 13% to 17% |
| After a message of five words or fewer | 40% of replies end on a question, against 31 to 33% after longer ones |

Against the rating each helped person gave for empathy (1,150 rated conversations, rank correlation): the share of
replies ending on a question, 0.00; reflection, +0.04; reassurance, +0.08; suggestions, −0.07; words per reply,
+0.15. The 173 usable chats that failed the dataset's quality bar have shorter supporter replies, a median of 15
words against 20.5.

So people ask in about a third of their replies and less as a conversation goes on, nobody asks every time, and
within that range asking more or less has no relation to how understood the other person felt. Saying more does, a
little.

## 3. What separates good counselling from bad (AnnoMI)

Sessions with at least five therapist utterances: 109 rated high quality, 21 rated low.

| Per session, median | High quality | Low quality |
|---|---|---|
| Therapist replies that contain a question | 36% | 33% |
| Therapist utterances that contain a reflection | 31% | 6% |
| Replies that reflect and ask nothing | 23% | 0% |
| Utterances that give information or advice | 11% | 50% |
| Utterances that give advice | 0% | 21% |
| Reflections for every question | 1.00 | 0.14 |
| Sessions where every reply has a question | none | none |

Good and bad sessions ask the same amount. The difference is reflection: saying back what the person means, with or
without a question after it. Bad sessions replace it with advice.

## 4. The phrase screen against real statements (C-SSRS posts)

`safety.screen`, the real function, run over every post.

| Severity given by the dataset's authors | Posts | Screen flags | Flags as crisis |
|---|---|---|---|
| 0 Not about suicide | 351 | 11 (3%) | 6 |
| 1 Wish to be dead | 200 | 27 (14%) | 12 |
| 2 Thoughts of killing oneself | 302 | 125 (41%) | 114 |
| 3 Thinking about how | 72 | 12 (17%) | 9 |
| 4 Some intention to act | 37 | 15 (41%) | 13 |
| 5 A plan worked out, with intent | 50 | 14 (28%) | 12 |
| 6 Has done or prepared something | 158 | 34 (22%) | 28 |

- **The screen flags 28% of posts with any suicidal content** (227 of 819), and **26% of those with intent, a plan or
  an act** (63 of 245).
- On short posts, which are closer to a chat message, it flags 11 of 47 with 15 words or fewer.
- 37 of its 60 phrases never matched one of the 819 posts. Six phrases do nearly all the catching ("kill myself",
  "want to die", "killing myself", "end my life", "commit suicide", "do not want to be here").

The same file carries the labels five language models gave when the dataset's authors ran them in 2025 with the
Columbia questions as the prompt.

| Model | Said "not about suicide" on severity 2 to 6 | On severity 4 to 6 | Said suicidal on severity 0 |
|---|---|---|---|
| o4-mini | 13 of 611 (2%) | 3 of 241 | 41 of 350 (12%) |
| claude-3-7-sonnet | 8 of 618 (1%) | 3 of 245 | 81 of 351 (23%) |
| gemini-1.5-pro | 1 of 618 | 0 of 245 | 163 of 351 (46%) |
| llama-4-maverick | 8 of 615 (1%) | 1 of 242 | 89 of 351 (25%) |
| mistral-large | 5 of 619 (1%) | 1 of 245 | 102 of 351 (29%) |

- Of the 182 posts at severity 4 to 6 that the screen missed, all five models recognised 172.
- Of the 20 posts at severity 2 to 6 that at least one model missed, the screen flagged 3.

So a phrase list catches about a quarter of what people actually write, and a language model about 99%. As a second
look under the model, the list rescued 3 posts in 619. The models' weakness is the other direction: they called 12
to 46% of the posts labelled "not about suicide" suicidal, on a forum where that is the expected subject.

## 5. The repo's own counts do not see her complaints

`reply_checks.repeats` (the last question asked again) and `reply_checks.repeats_their_words` (the first sentence is
their message said back) both read 0% on the boss chat, where she wrote "you asked me this already" and where point
3 is "it kept restating what the user had already said". Across all eleven conversations they fire on 1 reply each.
Both compare words, and what she objects to is the same thing asked or said in different words. A count of shared
words cannot see that; it needs a reader.

## 6. The logic tests that could run

Twelve unit test files that touch only the pure modules (`walk`, `safety`, `pause`, `converse`, `picture`,
`understanding`, `reply_checks`, `repairs`, `schema`, `text`, `body`, `techniques`): **320 passed**, 1 could not run
because it imports the `openai` package, which the scratch shell does not have. This is Python 3.10 with two shims,
not the project's 3.14, so it is a check of the logic and not the project's test run. The other unit files and the
integration tests need newer syntax or a database.

## 7. What this changes in the design

The design named five root causes and a set of decisions (D1 to D13). These are the changes the measurements call
for.

1. **Root cause 2 was wrong as stated.** "Every way out of a reply is a question" is true of the code, and it is
   not what the client's verdict follows. The measured difference is that Mani gives too little before it asks,
   most of all when the person writes little. `voice.md` tells Directive to be "usually short" and to "acknowledge
   the difficulty in a few genuine words, then ask a question"; her own target for Directive gives 49 words first.
2. **Decision D1 stays, with a smaller claim.** A reply should be allowed to end without a question: no human
   supporter asks every time, and a goodbye and a crisis need it. It should not be expected to fix "too many
   questions". That depends on what the reply gives.
3. **Reflection, not the question count, is the thing to measure.** It is what separates good sessions from bad in
   AnnoMI, and it matches her words: "there wasn't much support beyond interpreting what I was saying".
4. **Decision D10 gets numbers.** The phrase list is not a floor in any useful sense. The guarantee that a failed
   model call still gets words (1b) matters more than I had put it, because the list would cover about one message
   in four. Retiring the list is now a concrete test: run these 1,170 posts through Mani's own safety judgment.
5. **The scenario set needs people who say little.** Every chat she disliked has short messages. A set built from
   long, forthcoming messages would have shown none of this.
6. **Two of the counts the design planned to use are blind** (section 5 above). "Words given before the last
   question" and "share of replies that apologise" should be added; they are cheap and they follow her verdict.
7. **A new decision for Lolly:** how much a Directive reply gives before it asks. Her styles document says short;
   her 2026-10-26 target shows otherwise.

## 8. What could not be measured here

| What | Why not | What it takes |
|---|---|---|
| How Mani behaves on any scenario, today or after a change | needs the model, the database and a key | the baseline run in the spec, with muhammad's yes |
| Mani's own safety judgment on the 1,170 posts | same | one cheap run; it also sends real people's posts to the provider, which is a decision to make first |
| The three classifiers on Hugging Face (two for a person's message, one for Mani's reply) | the shell cannot reach huggingface.co, and PyTorch did not install in time | a run on muhammad's machine |
| CBT-Bench against Mani's framework replies | needs the model | later, with the framework slice |

The three scratch scripts (transcript counts, ESConv and AnnoMI, the screen) belong in `backend/scripts/` beside
`scenario_check.py` when the measurement step is built. The transcript counts are the start of that step's counts.

## 9. Limits

- **Eleven conversations, three kinds of verdict.** The table in section 1 is a description, not a test. The chats
  come from different builds, and the disliked group includes two safety chats.
- **ESConv is crowd workers supporting each other**, filtered for quality, in short chat turns. AnnoMI is
  motivational interviewing, one method among many, and mostly about habits. Neither is Mani's setting.
- **The posts are forum posts**, longer than a chat message, labelled by the dataset's authors. The five models are
  not Mani's model and were asked a different question than Mani asks itself.
- **Correlations in section 2 are small** and say nothing about cause.
