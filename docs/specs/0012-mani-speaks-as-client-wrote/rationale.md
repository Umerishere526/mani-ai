# 0012. Rationale: Mani speaks and asks as the client wrote

## Context

> ⚠️ Premise note: this spec reverses one of muhammad's own fixes. `question_focus` was added on 2026-09-24 because "the style rule in the long prompt alone did not hold" (the comment in `context.py`). It goes because it now contradicts the client: it tells Supportive and Reflective to ask about feelings and never the facts, while every one of the client's Supportive and Reflective examples asks about what happened. The style lines carry the whole weight after this, and three real conversations are the only check. muhammad chose that cap.

> ⚠️ Premise note: some of our rules forbid what the client's own lines do. "Never name a feeling… not as a fact, a guess or a question" forbids the client's "Does it feel like your body is activated and your thoughts are moving too quickly?". "Never ask them to sort, label or pick what is worst" forbids "What feels strongest right now?", "What feels most pressing right now?" and "Which one keeps pulling at you the most?". The client's documents win over our conversation rules (muhammad, 2026-10-06), so these are cut. The client's own limits stay: Reflective "does not introduce meanings, emotions, motives, or conclusions the user has not expressed", which `rules` line 1 and line 3 still say.

In muhammad's chat tester run on 2026-10-08, Direct style, the person gave the event and the feeling in their first message ("my manager pointed me out in front of the CEO", embarrassed), and the offer still came at turn 8. Mani even asked whether a brief look would help, got a yes, and kept asking. The journal note `offer-late-root-cause-prompt-not-code-2026-10-08.md` traced it to the prompt, not the timing code: `clear_offer_after` was already 2. Thought Reframe's Starts when line wanted the thought, the moment, why it matters and that they want a brief look. `mani_base.md` added that every question "reaches, unseen" for what the likeliest set needs, and that two fitting sets need a question that tells them apart. Each rule costs a question. The Direct line, "Start with what they feel", made Direct restate the feeling every turn, which is Reflective's behavior.

The client's style document of 2026-10-08 sets the target. Offer "once it has enough understanding to identify the issue and determine the appropriate framework", in about 2 to 4 exchanges, "a range, not a required count". The three styles differ by behavior, not by phrases, and each has a list of what Mani does inside a framework. The cadence is: the issue is stated, 2 to 4 exchanges, "ask, check, and confirm rather than label or assume", then the offer. The document calls the first style Directive; the button says Direct.

muhammad's rule from the same day bounds the fix: reach the client's outcome by cutting and clarifying prompt rules, never by adding them, because rule bloat makes the model drift, and keep the guardrail code. `mani_base.md` and `response_format.md` hold 150 lines and 3616 words between them today. Feature 15 (the offer's wording and buttons) edits the same `offers` block, so the boundary between the two has to be drawn line by line.

## Options considered

### Option 1: Cut and replace with the client's phrases (chosen)

Rewrite the three style lines from the client's behavior lists, in the client's phrases. Cut the rules that each ask for one more question, cut the clauses that forbid the client's own lines, shorten the Starts when lines to what identifies the issue, and delete the two `[ctx]` lines that contradict the client (`question_focus`) or duplicate the check rule (`clarification_lines`).

**Pros**:
- Every edit removes or replaces words, so the prompt gets shorter and has fewer rules to trip over.
- The style lines can be read side by side with the client's lists.
- No new code; two `[ctx]` lines and a model field leave it.

**Cons**:
- It undoes the `question_focus` fix, and the style lines must now hold on their own.
- The Starts when lines lose their brief or deep distinction between ABCDE and Thought Reframe.

### Option 2: Paste the client's lists word for word

Replace the style lines with the client's 9 or 10 bullets per style, as the document writes them.

**Pros**:
- The most literal reading of "as the client wrote".
- No judgment about which phrases to keep.

**Cons**:
- About 30 more lines, the opposite of the cut rule.
- Each list repeats the three universal rules (do not label, check understanding, let them confirm), already in `rules`, so the model reads them four times.
- It does nothing about the offer timing rules that caused the 8 turn offer.

### Option 3: A code cap that forces the offer

Leave the prompts and make the code mark an offer as due after the fourth exchange, through `[ctx]`.

**Pros**:
- Deterministic; the offer would come by exchange 4 every time.
- Easy to test with a scripted model.

**Cons**:
- The client says 2 to 4 is "a range, not a required count" and Mani should not keep asking "simply to reach a certain number of exchanges". A cap turns it into a count.
- It adds code and a `[ctx]` line, and leaves the rules that cause the extra questions in place, so the model fights the cap.
- It does nothing for the style behavior.

### Option 4: Show the client's dialogues as examples

Add one or two of the client's scenarios to the prompt as worked examples of each style and the cadence.

**Pros**:
- Models copy examples well; the cadence would be shown, not described.

**Cons**:
- Hundreds of words added to every call, against the cut rule and the cost baseline.
- Models copy examples too well: the client's exact lines would turn into stock phrases, which the document forbids by name.
- The contradicting rules would still be there.

## Rationale

The 8 turn offer had a known cause: rules that each asked for one more question. Option 1 is the only one that removes that cause, and it does so by deleting, which is the direction muhammad set. Options 2 and 4 add words without removing a contradicting rule. Option 3 adds code to override rules that would still be there, and turns the client's range into the count the client warned against.

Within Option 1, the boundary with feature 15 is drawn by what each line does. Lines that decide when to offer belong here; lines that decide what the offer says and which buttons it carries belong to feature 15. So `offers` line 1's first sentence and line 3 change, and the rest of the block stays byte for byte, so feature 15 starts from a known text.

The Starts when lines shrink to what identifies the issue, because the stage ledger (spec 0010) already asks any stage still missing after the yes. A Starts when line that also names the later stages makes the model ask them before it may offer, which is the cost the client wants removed; once the person says yes, the ledger asks them anyway, or skips them when the chat already told them. The two preference clauses ("a brief look", "in depth") are cut because they can only be learned by asking. The difference they carried is still on the Skip when lines.

`clarification_lines` goes for a related reason. The two lines come from an earlier client document, the October 8 document never uses them, and `rules` line 2 already says how to check understanding. Two ways of saying the same thing invite an extra check question.

Renaming only the label keeps the change to one string. The key `direct` lives in the `SupportStyle` value, every stored thread and the prompts, and no person ever sees it.

The real run cap is muhammad's choice: three conversations, one per style, so each style line is exercised once on a different issue. It shows a direction, not a rate, and the spec says so.
