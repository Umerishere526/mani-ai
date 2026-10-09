# 0013. Rationale: the offer in the client's words

## Context

> ⚠️ Premise note: the shared lead promises the wrong thing for five of the six sets. "By the end, you will have turned a problem that feels unclear or overwhelming into a practical next step" is Structured Problem Solving's own description. On its offer the sentence appears twice, once in the lead and once in the description. On a Thought Reframe offer the person is promised a practical next step and, two lines later, a different way of seeing the situation. On ABCDE, ACT Choice Point and STOP the promise does not match what the questions do. The cleaner text is the lead without that sentence, since each description already says what it leads to. muhammad saw both drafts on 2026-10-08 and kept the sentence. The spec builds it as he wrote it, and because the text is seeded, removing the sentence later is a one line reseed.

> ⚠️ Premise note: this spec reverses part of two decisions in force. Spec 0007 removed the code's offer composition ("offer in the model's words"), and the decisions in force say the reply goes out as the model wrote it. Both stand everywhere else. The reason for the exception is that the client and muhammad now want exact text, and no prompt can guarantee a model copies text exactly.

> ⚠️ Premise note: the client's intro document marks every description "do not give them the name of the framework". muhammad decided on 2026-10-08 to show the name, and the client is to be told; that line is already on the client list in `PORT-STATUS.md`.

Today an offer is the model's own: one sentence showing it understood, then what the questions help with in fresh words from the framework's Description line, then a question in the chosen style, with two buttons the model writes, Try it (carrying the framework id) and Keep chatting (a decline). `offers` line 1 forbids the name, the id and the word framework.

The client's documents of 2026-10-08 ask for more and for less. The style document gives three buttons, Yes, let's try it · Tell me more · I want to keep talking, and after Tell me more, the first and last again. Its example offers are worded per style ("I have a structured approach that can help you work through this. Would you like to try it with me?"), and its Tell me more replies are per style and often name the person's issue. The intro document gives each framework's description, word for word, and asks that the name not be shown. Scope feature 15, written by muhammad, asks for a fixed frame with the name and the client's description exactly, changeable by reseed.

Two things in the code shape what is possible. A turn is one model call, and the code after it only guards what is stored or sent. A tap is matched by its label against the buttons stored on Mani's newest message, and a button may carry a key the model never writes: the greeting's style buttons carry `style`, and a style tap gets its opener from the `replies` row with no model call. muhammad's rule from 2026-10-08 also applies: reach the client's outcome by cutting prompt rules, never by adding them.

## Options considered

### Option 1: The code writes the offer from seeded rows (chosen)

The model marks an offer with one button carrying the framework id, as today. After every guard, the code replaces the turn's text with a seeded template filled with the framework's name and description, and writes the three buttons. A Tell me more tap is answered from the same rows with no model call.

**Pros**:
- The only option that shows exactly the same text every time.
- All wording lives in seeded content: a reseed changes it.
- The prompt gets shorter: the offer wording rule and six `Offer:` lines go.
- It reuses two existing patterns: buttons with code only keys, and a tap answered without the model.

**Cons**:
- An exception to "the reply goes out as the model wrote it".
- The offer loses the per style voice the client's examples show.
- The model's text on an offer turn is generated and thrown away.

### Option 2: The model copies the text word for word

The prompt tells the model to write the lead, the name and the Description line exactly, with the three buttons.

**Pros**:
- No code change; the reply still goes out as written.
- The model could still add a sentence in the person's words.

**Cons**:
- Models paraphrase; "exactly" cannot be promised, and checking it after the call would mean reading words to decide what to send, which the decisions in force forbid.
- It adds a rule rather than cutting one, against muhammad's rule.
- Tell me more would still cost a model call and give a different answer each time.

### Option 3: The client's style document as written

No name and no description. The model writes the styled offer the way the client's examples do, and the code only adds the three buttons.

**Pros**:
- Closest to the client's newest document, including "do not give them the name".
- Keeps the per style voice.

**Cons**:
- Drops the description, which muhammad and the scope ask for.
- The offer text still varies run to run.

### Option 4: The model's line, then the name and description from the code

The model writes its styled offer, and the code adds the name and the description under it.

**Pros**:
- Keeps the per style voice and adds the exact description.

**Cons**:
- Two voices in one message, and a code addition to model text.
- Not what muhammad drew: his offer is fixed text only.

## Rationale

The requirement that decides it is "exactly". The scope's done line asks that every offer show the frame, the name and the description exactly, and that changing it need only a reseed. Only Option 1 meets that, because only the code can copy text exactly. Options 2 and 3 leave the words to the model; Option 4 meets the requirement for the description but not for the frame muhammad wrote, and he chose fixed text only when shown both.

Option 1 also keeps the model's real job. Deciding when the issue is clear and which set fits stays with the model, and every guard that can stop an offer (unknown ids, a running framework, a decline, a safety concern, the ending) runs before the code writes anything. So the exception to "the reply goes out as the model wrote it" covers one turn, the offer, and only its words.

Tell me more marks its button with a stored only key, `more`, matched from the stored options the way `style` is. The runner up, matching the seeded label, breaks when the label is reseeded between an offer and the tap. Typed text past an offer is not removed, though clients hide the field: the backend is the only authority, and any client that still sends text keeps getting today's yes and no handling. What is sent follows one rule: any offer button that survives the checks gets the full offer. The cross check found that keeping the model's answer to a typed question (with two buttons) would need a same offer comparison in code and a prompt line telling the model to carry the button again, both for a path no current client reaches. muhammad chose the one rule on 2026-10-08.

The `Offer:` lines are cut because the model no longer words the offer, and a rule the model reads every turn for a job it does not do is the kind of bloat muhammad asked to remove. The format goes from eight lines to seven, and the seed check moves with it.

No real model run is planned. The offer is deterministic once the model's button survives the guards, so scripted turns prove it, and whether the model offers at the right moment is unchanged by this spec (it was measured under spec 0012 and is measured further under feature 11).
