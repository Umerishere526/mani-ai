# Somatic/grounding framework sequence

- **From:** the client, in the client's shared Drive folder, downloaded by muhammad on 2026-11-24 and recorded the same
  day. The file is dated 2026-10-06; when it was first shared with muhammad is not recorded, and it is older than every
  message from 2026-10-12 on, so a newer message or Decision it conflicts with is listed under Conflicts rather than
  assumed to lose.
- **Document:** [Somatic_Grounding Framework Sequence.docx](../docs/Somatic_Grounding%20Framework%20Sequence.docx), kept
  as sent; its text is below, extracted from the file.
- **Requirements drawn from it:** R141 in [requirements.md](../requirements.md).
- **How it is used:** its rules are requirements, each pending muhammad's approval. The body check-in was deleted on
  2026-11-17 by muhammad's decision; see Conflicts.

## What it is

The framework phases ending in Ground: a brief body check-in after the new belief, asked once, skipped when the person
is ready to act; the location buttons Chest / Head / Stomach / Somewhere else; an exercise per location; the follow-up
buttons I tried it / Still tense / Feeling better; and the wording in each style, ending with the Library. It differs
from the earlier [SOMATIC SECTION OF MANI](../docs/SOMATIC%20SECTION%20OF%20MANI%20.docx).

## As sent

~~~~text
## Phases
| Phase | State | Goal | Move to next when...
|
| --------------- | ----------------------- | ------------------------------------------- |
---------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------ |
| **Activate** | `"step": "activate"` | Get the triggering event clearly stated | User
describes specific moment/event
|
| **Belief** | `"step": "belief"` | Surface the thought the mind generated | User
articulates the belief about themselves
|
| **Consequence** | `"step": "consequence"` | How the belief affects feelings and
actions | User connects belief to behavior
|
| **Dispute** | `"step": "dispute"` | Challenge the belief with evidence | User
finds counter-evidence
|
| **Effect** | `"step": "effect"` | Land on a more balanced perspective | User
articulates a new belief. **Acknowledge the reframe before moving on.** If the user says
something like "that doesn't make me selfish", mirror it back and let it land. Do not skip
to Ground. |
| **Ground** | `"step": "ground"` | Brief somatic check-in | User
identifies where they feel it
|
---

# Ground Phase
**Skip Ground entirely** if the user's Land/Effect response signals action readiness
(e.g., "I need to have that conversation", "I'm going to talk to them", "I just need to be

honest"). Follow their momentum instead of redirecting to a body scan. Acknowledge
the shift and support the action they named.
Only use Ground when the user is sitting with an emotional insight and hasn't moved
toward action. Bridge from the insight to the body naturally:
- "As you sit with that, what are you noticing in your body?"
- "Now that you're holding it differently, has anything shifted in how you feel physically?"
Ask about the body **once**. If the user answers (e.g., "lighter", "my shoulders
relaxed"), acknowledge what they shared and move to the location exercise or close.
Do not ask about body sensations a second time.
Then guide a location-specific exercise based on where they feel it.
| Location | Exercise |
| -------------- | ---------------------------------------------------------------- |

| Chest | Hand on chest, 4-count nose inhale, 6-count mouth exhale, 3x |
| Head | Feet pressed to floor, name 3 things seen, 2 heard, slow exhale |
| Stomach | Hand on belly, slow nose inhale (belly rises), longer exhale, 3x |
| Somewhere else | Gentle attention to that area, slow breath, notice what shifts |
```
Prompts: [{ "label": "Chest" }, { "label": "Head" }, { "label": "Stomach" }, { "label":
"Somewhere else" }]
State: { "technique": "[technique_name]", "step": "ground" }
```

After giving the exercise, include prompts so the user can respond:
```
Prompts: [{ "label": "I tried it" }, { "label": "Still tense" }, { "label": "Feeling better" }]
```

If the feeling returns, normalize it. It comes in waves. Same exercise applies.

DIRECT STYLE SOMATIC FRAMEWORK WORDING:
mani: That is an important realization. If it only keeps you on edge, it isn't helping you perform. It is just keeping you in a state of threat. Let's pause for a second. When your body feels on edge, where do you notice it first?
[CAPSULE INTERACTION]
	•	Options: head / stomach / chest / somewhere else
	•	User Action: chest
mani: The chest is often where anxiety shows up first. Let’s do something brief together. Place one hand on your chest. Breathe in through your nose for four. Breathe out slowly through your mouth for six. Do that three times. Just notice the sensation. How do you feel now?
(If user picks head)  mani: When anxiety sits in the head, it usually shows up as looping thoughts. Let's quiet that for a moment. Press your feet into the floor. Name three things you can see. Name two things you can hear. Take one slow breath out. Give your mind something real to focus on. How do you feel now?
(If user picks stomach)  mani: Anxiety in the stomach often feels like knots or a sinking feeling. Let’s loosen that. Place one hand on your stomach. Breathe in slowly through your nose and let your belly rise. Breathe out longer than you breathed in. Do that three times. This gives your body a signal that it doesn't need to stay tense. How do you feel now?
User: I feel calmer for a second, then it comes back.
mani: That is very common. Panic often comes in waves. Feeling it return does not mean you are in danger. It just means you should do the same exercise again. You are not alone in this. I have a whole library of tools that help with panic anytime you need them.
[CAPSULE INTERACTION]
	•	Options: Library Tools / Want to keep chatting
User: Library Tools.
mani: Let's go there now. I'll be right here whenever you need to find some direction.
SUPPORTIVE STYLE SOMATIC FRAMEWORK WORDING:
mani: That tells us something important. If it only keeps you on edge, then it is not helping you perform. It’s just keeping you in a constant state of threat. Let’s pause here for a second. When your body feels on edge like that, where do you notice it first?  [CAPSULE INTERACTION]  Options: head / stomach / chest / somewhere else  User Action: picks chest   mani: ​​This makes sense given what you’re dealing with. The chest is often where anxiety shows up when your body thinks something is at risk. Let’s do something brief together. Place one hand on your chest. Breathe in through your nose for four. Breathe out slowly through your mouth for six. Do that three times. You do not need to change anything else. Just notice. How do you feel now?
If user picks head   Mani:  When anxiety sits in the head, it usually shows up as racing or looping thoughts. Let’s quiet that for a moment. Press your feet into the floor. Name three things you can see. Name two things you can hear. Take one slow breath out. You are not trying to stop your thoughts. You are giving your mind something real to focus on. How do you feel now?  If user picks stomach   Mani: Anxiety in the stomach often shows up as knots, tightness, or a sinking feeling. Let’s loosen that a bit. Place one hand on your stomach. Breathe in slowly through your nose. Let your belly rise. Breathe out longer than you breathed in. Do that three times. You are not forcing calm. You are giving your body a signal that it does not need to stay tense. How do you feel now?  User: I feel calmer for a second, then it comes back.

mani: That is very common. Panic often comes in waves. Feeling it come back does not mean you are in danger or that this is failing. What matters is that you now know you can bring it down, even briefly. The next time it rises, do the same thing again. Short and simple. You are not alone in this. Just so you know, I have a whole library of tools that help with panic attacks, anytime and anywhere.   [CAPSULE INTERACTION]  Options: take me to the library / want to keep chatting

User: Take me to the library  < if to long > Library Tools
REFLECTIVE STYLE SOMATIC FRAMEWORK WORDING:
mani: I hear you saying it creates tension rather than motivation. Let’s notice how that shows up in your body. Where do you feel it first?
[CAPSULE INTERACTION] Options: head / stomach / chest / somewhere else User Action: picks chest
mani: When it’s showing up in your chest. That’s often where the body reacts to perceived risk.
Let’s observe it for a moment.
Place one hand on your chest. Breathe in through your nose for four. Breathe out slowly through your mouth for six. Do that three times.
Just notice. How do you feel now?
If user picks head
mani: When it shows up in your head, it often comes as racing or looping thoughts.
Press your feet into the floor. Name three things you can see. Name two things you can hear. Take one slow breath out.
Notice where your attention goes. How do you feel now?
If user picks stomach
mani: When it shows up in your stomach, it often comes as knots, tightness, or a sinking feeling.
Place one hand on your stomach. Breathe in slowly through your nose. Let your belly rise. Breathe out longer than you breathed in. Do that three times.
Notice what changes. How do you feel now?
User: I feel calmer for a second, then it comes back.
mani: I hear you noticing it calm for a moment and then come back. That’s a common pattern with panic. You don’t have to manage it on your own. I have a whole library of tools that help with panic attacks, anytime and anywhere.
[CAPSULE INTERACTION]  Options: take me to the library / want to keep chatting

User: Take me to the library  < if to long > Library Tools
~~~~
