# Risk classification

- **From:** the client, in the client's shared Drive folder, downloaded by muhammad on 2026-11-24 and recorded the same
  day. The file is dated 2026-09-01; when it was first shared with muhammad is not recorded, and it is older than every
  message from 2026-10-12 on, so a newer message or Decision it conflicts with is listed under Conflicts rather than
  assumed to lose.
- **Document:** [Risk Classification.pdf](../docs/Risk%20Classification.pdf), kept as sent; its text is below, extracted
  from the file.
- **Requirements drawn from it:** R131 in [requirements.md](../requirements.md).
- **How it is used:** its rules are requirements, each pending muhammad's approval. Several of its rules conflict with
  the safety Decisions in force; see Conflicts.

## What it is

Every message classified HIGH_RISK, MEDIUM_RISK or LOW_RISK, with trigger phrases for each. HIGH shows crisis resources
at once, offers a hotline and de-prioritises the conversation; MEDIUM responds with empathy and one direct clarifying
question, upgrading or downgrading on the answer; LOW continues the conversation with no hotline. A message with any
high-risk signal is HIGH. "Intent = escalate, Emotion = support, Ambiguity = clarify."

## As sent

~~~~text
1. CLASSIFICATION OUTPUT
Every user input must be classified into ONE of these:

   ●​ HIGH_RISK
   ●​ MEDIUM_RISK
   ●​ LOW_RISK

2. HIGH_RISK → TRIGGER CRISIS
HOTLINE
Definition

User expresses intent, plan, or near-term risk of self-harm

Trigger Conditions (ANY = HIGH_RISK)

A. Direct intent

   ●​ I want to die
   ●​ I don’t want to live
   ●​ I wish I were dead

B. Self-harm desire

   ●​ I want to hurt myself
   ●​ I feel like ending it
   ●​ I might kill myself

C. Plan or method

   ●​ I have a plan
   ●​ I know how I would do it
   ●​ I’ve been researching ways

D. Time-based urgency

   ●​ I might do it tonight
   ●​ I don’t think I’ll make it
   ●​ I feel close to doing something

E. Finality / goodbye language

   ●​ This is my last message
   ●​ I said goodbye to people
   ●​ Everyone is better off without me

F. Preparation behavior

   ●​ I gave my things away
   ●​ I wrote letters
   ●​ I’m putting things in order

System Action

   ●​ Immediately show crisis resources
   ●​ Offer hotline connection
   ●​ De-prioritize normal conversation flow

3. MEDIUM_RISK → CLARIFY, DO NOT
TRIGGER
Definition

User shows distress that could escalate, but no clear intent

Trigger Conditions (ANY = MEDIUM_RISK)

   ●​ I feel like giving up
   ●​ I don’t know how much longer I can do this
   ●​ I wish I could disappear
   ●​ I feel numb
   ●​ I don’t care about anything anymore
   ●​ I’m exhausted with life
System Action

   ●​ Respond with empathy
   ●​ Ask ONE direct clarification question:

Example logic:​
Are you thinking about hurting yourself, or are you feeling emotionally
overwhelmed?

   ●​ If user confirms self-harm → upgrade to HIGH_RISK
   ●​ If not → downgrade to LOW_RISK

4. LOW_RISK → NORMAL SUPPORT (NO
HOTLINE)
Definition

User expresses pain, grief, or stress without self-harm intent

Trigger Conditions

A. Grief

   ●​ My grandfather died
   ●​ I lost someone
   ●​ I miss them

B. Depression / sadness

   ●​ I feel depressed
   ●​ I feel down
   ●​ I feel empty

C. Stress / overwhelm

   ●​ I feel overwhelmed
   ●​ I’m struggling
   ●​ I’m exhausted

D. Existential thoughts

   ●​ I think about death
   ●​ What’s the point of life

E. Help-seeking

   ●​ I need help
   ●​ I want to talk to someone
   ●​ I think I need therapy

System Action

   ●​ Continue normal conversation
   ●​ Offer support tools
   ●​ DO NOT show crisis hotline

5. DECISION LOGIC (IMPLEMENTATION)
Step 1: Scan input

Check for HIGH_RISK patterns

IF match → HIGH_RISK

Step 2: If not HIGH_RISK

Check for MEDIUM_RISK patterns

IF match → MEDIUM_RISK

Step 3: If neither
→ LOW_RISK

6. PRIORITY RULE (IMPORTANT)
If a message contains BOTH:

   ●​ Low-risk language​
      AND
   ●​ Any high-risk signal

→ classify as HIGH_RISK

Example:​
My grandfather died and I don’t want to live anymore​
→ HIGH_RISK

7. DO NOT DO THIS
Do NOT trigger hotline for:

   ●​ grief alone
   ●​ depression alone
   ●​ stress or overwhelm
   ●​ philosophical discussion of death

8. MINIMUM KEYWORD GROUPS (FOR
MODEL OR RULES)
HIGH_RISK keywords

   ●​ die
   ●​ kill myself
  ●​ end it
  ●​ don’t want to live
  ●​ hurt myself
  ●​ suicide
  ●​ plan
  ●​ tonight
  ●​ goodbye

MEDIUM_RISK keywords

  ●​ give up
  ●​ disappear
  ●​ numb
  ●​ can’t do this
  ●​ don’t care anymore

LOW_RISK keywords

  ●​ sad
  ●​ depressed
  ●​ overwhelmed
  ●​ stressed
  ●​ lost someone

9. WHAT MATTERS MOST
  ●​ Intent = escalate
  ●​ Emotion = support
  ●​ Ambiguity = clarify
~~~~
