# 0007. Rationale: a framework ends with a conclusion and the body check

## Context

Every framework file ends with a `closing` stage whose `ask` is a completion question: "How does that sit with you?", "Does that feel accurate to you?", "Is that something you could realistically do?" It came from section 21 of each client specification. The body check follows it as a separate turn, and the shared `somatic_checkin` stage has a rule that skips the body check when the person's closing answer already names an action.

Two chats on 2026-10-05 show the cost. In the ACT chat the person had just said they would write to their manager and go to their mother, and Mani answered with "Is that something you could realistically do today?" In the ABCDE chat the person said "i don't know myself. i've lost my confidence", and Mani answered "It is completely understandable to feel like your confidence has taken a hit. Is there anything you would add before we finish looking at this?" That second question is not the normal closing question. It is the `if_earlier_missing` fallback, used because the balanced thought was never given. In both chats muhammad wanted an ending that concludes, validates and moves to the body check, not another question.

Three things limit the answer. The frameworks' own boundaries forbid choosing the person's response or values, summarizing the framework, or claiming it worked. Spec 0002 bans "It sounds like", invented feelings and restating. And removing the closing question without care would make the body check skip rule fire on almost every ACT, Behavioral Activation, Problem Solving and DBT STOP ending, which is the problem scope row 19 describes. Not deciding leaves every framework ending on a form question.

## Options considered

### Option 1: Remove `closing`, and let the body check stage write the conclusion

The last real stage is followed straight by `somatic_checkin`. Its purpose and boundaries carry the conclusion rules once for all frameworks, the model writes one or two sentences, and `with_the_check_in` appends the client's fixed question.

**Pros**:
- The code already does the hard part: the `closing` to `somatic_checkin` move, the fixed check in text and the dropping of the model's own last question all exist.
- One place for the rules, so six frameworks cannot drift.
- Removes a stage that existed only to ask one question.

**Cons**:
- Per framework closing boundaries merge into one shared list.
- Many tests and scripts name `closing`, so the change is wide even though each edit is small.

### Option 2: Keep `closing` as a stage that writes the conclusion, and have code skip to the body check

Each framework keeps its own closing purpose and boundaries, the model writes the conclusion at `closing`, and code records `somatic_checkin` for that reply and appends the check in.

**Pros**:
- Framework specific closing rules stay where they are.
- Fewer content and test edits.

**Cons**:
- A stage that is never recorded, which is a fiction the phase list has to explain, and new code to jump over it.
- Six copies of nearly the same rules.

### Option 3: One fixed concluding line per style

Authored once, sent word for word, then the check in.

**Pros**:
- Fully testable and safe against every boundary.
- No model call risk at the end.

**Cons**:
- It cannot mention the person's own plan, so it reads generic, which is what muhammad objected to.

### Option 4: Keep a question and reword it

Replace "Is that something you could realistically do?" with a warmer question.

**Pros**:
- Smallest change.

**Cons**:
- It does not meet what muhammad asked for. It is still a question, and the "anything to add" fallback stays.

## Rationale

Option 1 is the smallest change that gives muhammad what he asked for. The context shows the machinery for "a model written reflection, then the client's fixed check in" is already in the code and already used for the closing to body check move. Option 2 keeps a stage that nothing would ever stay on, and Option 3 and Option 4 fail the point of the change: a conclusion that is about this person. Option 1 puts the rules in the one stage every framework already shares.

muhammad confirmed three choices on 2026-10-05: the conclusion and the body question go in one message, it applies to all six frameworks, and the body check is always asked. He also confirmed that the conclusion is written by the model under tight rules, and that the "I don't know" fix covers the balanced stages only. I recommended each of these and he took them as recommended. Two things in his earlier messages were not taken. A suggested ending that told the person to explain their situation to their manager and be with their mother would have chosen the action and value for them, which the ACT boundaries forbid ("must not choose the response", "must not select the user's values"). A second suggested ending asked another question, wrote the balanced thought the person had said they could not find, and began "It sounds like". Both were set aside for the same reason: the conclusion confirms what the person decided or said, and adds nothing of Mani's.

Always asking the body check, not keeping the action skip, is what keeps scope row 19's promise. Once the closing question is gone, the skip would apply to the answer at the last real stage, and four of six frameworks end on an action. The skip was written for a different shape, a closing answer that happened to mention an action, and it would silently turn the body check off for most endings.

The "I don't know" branch uses the counted hold that spec 0003 built, so it needs no new mechanism and is bounded by the same limit of one extra turn. It is limited to the balanced stages because that is where muhammad found the failure, and because those are the stages that ask the person for a conclusion; widening it to all 27 stages would reopen spec 0003's decision that "I don't know" moves on.
