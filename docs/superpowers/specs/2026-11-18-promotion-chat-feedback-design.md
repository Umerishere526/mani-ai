# The client's feedback on the Directive promotion chat

Short design (muhammad, 2026-11-18). Approach: option 1.

## Intent

The client reviewed one of muhammad's Directive chats reply by reply: a person passed over for a promotion, through
ABCDE to "Stronger". Her points: replies that state readings as facts, reassurance and disputing long before D, the
same point made again and again, too many observations before the question, pick-from-three questions, an abrupt
"A is for Activating Event.", an activating event that bundles the whole pattern, a causal claim that blames the
person, and a close that treats feeling better as the problem solved. muhammad decided which apply where. The
root causes are in `backend/content/prompts/mani.md` and the eval's judge, not in code (session of 2026-11-18).

## What changes

| # | Change | Styles |
|---|--------|--------|
| 1 | One or two points, then the question | Directive only |
| 2 | A reading is said as a possibility they can correct, never as a fact ("That is the core of it") | All |
| 3 | Inside the set, the belief is not argued with before D; the chat may still offer a fair perspective | All |
| 4 | Each point once: never the same reassurance or idea again in new words (R106) | All |
| 5 | One open question, never a pick-from-three | Directive only |
| 6 | One short sentence before the first stage's line, so the set doesn't start abruptly; the line stays | All |
| 7 | Step A is one specific, recent event, not the whole pattern | Directive only |
| 8 | After the feelings answer: acknowledge it, then ask whether they want to think about a next step (such as how to raise it with the person involved); the closing buttons stay | All |
| 9 | Eval rule cases from this chat | |

Also, from the investigation: never a causal claim the person has not made, least of all one that makes their
situation their fault ("That silence probably reinforced the feeling..."). All styles.

## Directive length: option 1

The rule "three or four short sentences at most" (2026-11-18) was broken in every reply of the chat. The hypothesis:
other lines say the opposite and the model follows them: "most replies do two or three of these", "usually 120 to
220 words", "usually 60 to 120 words" inside the set, and long examples. Option 1 removes those contradictions for
Directive and gives Directive its own short example, and an eval case fails a long Directive reply. Option 2, code
counting sentences and asking once more, is not built; it comes only if option 1 fails the eval.

## Where

- `mani.md`:
  - "How you listen": the first-reply line that names "what is really at stake" goes; the first-reply paragraph in
    "How a reply looks" stays (point 2).
  - "What a good reply gives": its moves are said lightly (2), never the same one twice (4), never a causal claim
    they haven't made; the possibilities question is not for Directive (5); Directive gives one or two (1).
  - "How a reply looks" and "Your style": word counts are for Supportive and Reflective; Directive gets its own short
    example (1).
  - "Inside the set of questions": no arguing with the belief before D (3); one bridge sentence before the first
    line (6); in Directive, A asks for one specific recent event (7); the closing reply asks about a next step (8).
- `mani/chat/facts.py`: the feelings-check line says "ask nothing"; it asks about a next step instead (8).
- Eval (`backend/evals/`): rule cases from this chat, five samples each, Directive:
  - a long Directive reply fails, through a new code check `max_sentences: 4` (1);
  - at B, no disputing the belief (3);
  - no pick-from-three question (5);
  - at the Start tap, the bridge, the line, and a question about one specific event (6, 7);
  - after "Stronger", the next-step question (8).
- Records:
  - the client's message in `docs/client/messages/`;
  - `requirements.md`: R83 kept overruled for Supportive and Reflective, upheld for Directive; R94 and R105 upheld
    after a set;
  - `PORT-STATUS.md`, edited in place: the Directive decision and the feelings check;
  - a journal note.

## Non-goals and anti-goals

- Supportive and Reflective keep their length, their possibilities questions and their activating event.
- No code length check now (option 2).
- The letter lines and the closing buttons stay.
- Anti-goal: a Directive that turns cold or empty. It still gives one real point before its question.
- Anti-goal: solutions in the chat before the set. The next step comes only after a finished set, as now.

## Constraint

OpenRouter credits are exhausted, so no eval can run. The prompt and code change and the tests pass now; the eval
cases and the gate run when the credits are back.

## Left to the builder

Every wording in `mani.md`, the Directive example, and the exact sentence counting (a sentence ends in `.`, `?` or
`!`; the stage line counts as one).
