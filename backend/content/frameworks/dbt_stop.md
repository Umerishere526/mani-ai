---
id: dbt_stop
name: DBT STOP
summary: "These questions help you pause before you react, so you can choose what to do."
display_order: 6
phases: [offering, stop, pause, observe, proceed]
activation:
  # The client's overview wording (six-frameworks-overview.md). The detailed STOP specification
  # covers only an action about to happen; the `panic` key on each stage below is our wording
  # for a person panicked with no action named, on the client sign off list (scope row 29).
  central_indication: >-
    The user is emotionally overwhelmed, highly reactive, panicked, or close to acting
    impulsively, and needs help pausing before responding, not analysis of the underlying
    problem. When an action is about to happen it is time critical and comes before whatever
    else the conversation was pointing toward.
  # How a person actually talks when this framework fits. The semantic router embeds
  # these, not central_indication: clinical prose scored 2/7 on real messages where
  # these scored 11/11. Authored content - changing them changes which framework is
  # offered, so they need the same review the summary does.
  exemplars:
    - "I'm about to send her a message I'll regret."
    - "I want to call him right now and tell him everything."
    - "I'm so angry I'm about to do something stupid."
    - "I keep typing and deleting and I'm about to hit send."
    - "I want to quit today, right now, before I change my mind."
  to_find_out:
    - "what they are about to do, or whether they are panicked right now with no action in view"
    - "whether it has already happened"
    - "whether it can safely wait a moment"
    - "whether anyone is at risk (then safety, not this)"
  # Documentation of the specification: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, to_find_out, distinctions and contraindications; the
  # router reads never_offer_when_said and stuck_offer.
  appropriate_when:
    - "The user is close to acting impulsively"
    - "The action has not yet occurred"
    - "The action can safely be paused"
    - "The user expects the action may intensify the situation"
    - "The user wants help stopping before acting"
    - "Remaining with MANI may support the pause"
    - "The issue has been identified and the user has agreed"
  not_when:
    - "The user wants to continue chatting without a framework, or has not agreed"
    - "No immediate action or reaction is present"
    - "The action has already occurred and no further action is imminent"
    - "The user wants to examine a belief"
    - "The user needs to solve a practical problem"
    - "The user has stopped acting and needs help beginning"
    - "The user needs to choose a values-aligned direction"
    - "The user is already able to respond intentionally"
    - "A medical emergency is present, or the safety protocol is required"
  contraindications:
    - "The intended action involves suicide, self-harm, harm to another person, overdose, immediate danger, or inability to remain safe - the safety protocol, not STOP"
    - "The action itself is protective - leaving, getting away from someone, calling emergency services, or seeking medical help. STOP exists to interrupt a regrettable action, and pausing a protective one is the same failure with the direction reversed: it delays the person from doing the thing that helps"
    - "The person would be kept near an abusive person, kept from contacting emergency help, or kept in the conversation when outside emergency support is needed - Pause Mode never takes priority over leaving danger or getting help"
  distinctions:
    somatic_transition: >-
      STOP interrupts an immediate action. The somatic transition follows a completed process
      and helps the user attend to what they notice physically. STOP may briefly ask what the
      user notices, but its purpose is to prevent automatic action, not to close out a
      framework.
    behavioral_activation: "STOP helps the user pause an action. Behavioral Activation helps the user begin one."
    structured_problem_solving: >-
      STOP when the user is about to react and first needs Pause Mode. Structured
      Problem-Solving when they can consider options and make a plan.
    act_choice_point: >-
      STOP when the immediate need is a pause. ACT when the user can reflect and wants to
      choose a response based on what matters.
    safety_protocol: >-
      STOP is for an impulsive response that can safely be paused within the conversation. The
      safety protocol is for possible suicide, self-harm, violence, overdose, immediate danger,
      or inability to remain safe - never use STOP in place of it.
stages:
  offering:
    purpose: "Mirror the immediate urge and ask one permission question, once what the user is about to do is understood."
    boundaries:
      - "must not command the user to calm down"
      - "must not use STOP instead of the safety protocol"
      - "when they are about to act, must not offer this before the specific action is named - a pause on an unnamed urge cannot be told apart from a pause on someone about to leave, call for help, or get away from danger, and those are the opposite of what STOP is for"
    panic:
      purpose: "Say back what they told you is happening right now and ask one permission question to pause here together."
      boundaries:
        - "must not offer this before you have asked what is happening for them right now"
        - "must not command them to calm down or promise the feeling will pass"
        - "must not name or interpret a body sensation they did not describe"
        - "must not use STOP when they describe a medical emergency or a safety concern - the safety protocol comes first"
      ask:
        supportive: "A lot is happening right now. Would it help to pause here with me and take this one moment at a time?"
        reflective: "Everything is moving quickly right now. Would it help to pause here with me and notice what is happening?"
        direct: "Would you like to pause here with me and work through this moment together?"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use Pause Mode. What would be most helpful right now?"
    ask:
      supportive: "You want to respond right now. Would it help to pause here with me before you act?"
      reflective: "The urge to respond is moving quickly. Would it help to pause here with me and notice what is happening?"
      direct: "You are about to send the message. Would you like to pause it and stay with me while we work through the urge?"
  stop:
    purpose: "Interrupt the intended action before it occurs."
    listen_for: "Whether the text, email, call, post, argument, purchase, or decision has been stopped before completion."
    ready_when: >-
      The immediate action is stopped: the message remains unsent, the call has not been
      placed, the post has not been published, the purchase has not been completed, the user
      has stopped typing, the argument has been paused, or the decision has not been made. If
      the action already occurred, identify whether another immediate action needs to be
      paused.
    boundaries:
      - "must not shame the urge"
      - "must not assume every immediate action is harmful"
      - "must not delay a protective action or prevent the user from leaving immediate danger"
      - "must not use STOP when the safety protocol is required"
    if_unclear:
      - when: "\"I cannot stop myself.\""
        reply: "Stopping feels out of reach right now. Can you pause the action for sixty seconds?"
        counted: true
      - when: "already acted - \"I already sent it.\""
        reply: "The message has already been sent. Is there another action you are about to take?"
        counted: true
    ask:
      supportive: "Can you stop the action before it happens?"
      reflective: "Can you stop the action before it happens?"
      direct: "Can you stop the action before it happens?"
    panic:
      purpose: "Stop for a moment with MANI, without needing the feeling to go away first."
      ask:
        supportive: "Can you stop here with me for a moment, just as things are?"
        reflective: "Can you stop here with me for a moment, just as things are?"
        direct: "Can you stop here with me for a moment, just as things are?"
  pause:
    purpose: "Enter Pause Mode and remain with MANI without returning to the action."
    listen_for: "Whether the action remains paused and the user remains engaged with MANI."
    boundaries:
      - "must not tell the user to put down the phone or place it out of reach"
      - "must not tell the user to leave the app, move away, or perform another activity"
      - "must not break the user's connection with MANI"
      - "must not require a long pause"
      - "must not pressure the user to remain if emergency help is required"
    if_unclear:
      - when: "returns to the action - \"I started typing again.\""
        reply: "You returned to the message. Can you pause the typing and remain here with me?"
        counted: true
      - when: "wants to leave - \"I am going back to the message.\""
        reply: "You want to return to it now. Can you remain paused with me for one more response?"
        counted: true
      - when: "the pause needs an anchor - the person is not physically leaving anywhere, so the pause is about where attention goes, not where the body does. One slow breath, naming what is in view, or a hand flat on the desk are usable even mid-conversation"
        reply: "Would one slow breath help you stay with the pause?"
        counted: true
    ask:
      supportive: "Can you hold off for a moment and stay here with me?"
      reflective: "Can you hold off for a moment and stay here with me?"
      direct: "Can you hold off for a moment and stay here with me?"
    panic:
      purpose: "Stay in the pause with MANI, without needing the feeling to change."
      ask:
        supportive: "You have stopped here with me. Can you stay with me for a few moments?"
        reflective: "You have stopped for a moment. Can you stay here with me and let this moment be as it is?"
        direct: "You have stopped. Can you stay here with me while we take the next step?"
  observe:
    purpose: "Notice what is happening internally and externally without acting on it."
    listen_for: "What the user notices in thoughts, urges, physical experience, and immediate situation, using only their language."
    boundaries:
      - "must not assign thoughts or feelings"
      - "must not interpret physical sensations"
      - "must not diagnose the user"
      - "must not dispute the underlying belief"
      - "must not begin the full somatic framework here"
      - "must not assume another person's motive"
      - "must not ask several questions at once"
      - "must not ask why they feel or think something - Observe is describing what is there, not explaining it; \"why\" turns the pause into another lap of the same thinking that produced the urge"
    ask:
      supportive: "What do you notice right now?"
      reflective: "What do you notice right now?"
      direct: "What is actually happening right now?"
    panic:
      purpose: "Notice what is present inside and around them, in their words, without interpreting it."
      ask:
        supportive: "You are staying here with me. What do you notice right now, inside you or around you?"
        reflective: "What do you notice right now, inside you or around you?"
        direct: "What do you notice right now, inside you and around you?"
  proceed:
    purpose: "Choose whether to wait, act, or respond differently."
    listen_for: "Whether the user chooses to wait, act, or respond differently, and what they want that response to accomplish."
    boundaries:
      - "must not choose the response"
      - "must not solve the underlying problem"
      - "must not begin another framework"
      - "must not pressure the user to communicate or to forgive"
      - "must not encourage confrontation"
      - "must not promise that waiting will resolve the problem"
      - "must not present non-action as the only correct choice"
    if_unclear:
      - when: "chooses retaliation"
        reply: "You want him to experience what you experienced. What response would avoid intensifying the situation?"
    ask:
      supportive: "What would help right now, rather than make it worse?"
      reflective: "What would help right now, rather than make it worse?"
      direct: "What would help right now, rather than make it worse?"
    panic:
      purpose: "Choose what would help in the next few minutes."
      ask:
        supportive: "What would help you most in the next few minutes?"
        reflective: "What would help you most in the next few minutes?"
        direct: "What would help you most in the next few minutes?"
---

# DBT STOP

Interrupts an immediate reaction before acting in a way that may intensify the situation. S:
Stop. T: Take a Step Back, which within MANI means Pause Mode - the user pauses the text, email,
call, post, argument, purchase, or decision and **remains with MANI throughout**. O: Observe. P:
Proceed Intentionally, with MANI. **MANI becomes the witness, the support, the anchor.** When the
user is close to reacting, the first need is not analysis or problem-solving - it is a pause
between the urge and the action. The purpose is **not** to make the user calm, eliminate the
reaction, solve the underlying problem, challenge a belief, make a permanent decision, or replace
MANI's safety protocol.

**MANI does not command the user to calm down.** MANI does not require the reaction to
disappear, shame or judge the urge, or assume what the user will do. MANI does not solve the
underlying problem during STOP. **MANI keeps the user engaged in the app** - it does not tell the
user to put down the phone, move away from the device, or leave the conversation. **MANI does
not use STOP instead of the safety protocol.**

**The essential distinction.** Use DBT STOP for a non-emergency impulsive reaction. Use the
safety protocol when the intended action involves suicide, self-harm, harm to another person,
overdose, immediate danger, or inability to remain safe. Must not be used to delay emergency
assistance, delay the user from leaving danger, pause a necessary protective action, tell the
user to remain near an abusive person, prevent the user from contacting emergency help, manage
suicidal or violent intent without activating the safety protocol, or keep the user in MANI when
outside emergency support is required.

## Stage progression

Stop the action -> Enter Pause Mode -> Remain with MANI -> Observe -> Proceed intentionally ->
Complete. Throughout Pause Mode: the outside action remains paused, the user remains with MANI,
and MANI remains the witness, support, and anchor.

## Worked example - direct solution tone

```
User:  I wrote a message telling him exactly what I think. I know it will make things worse,
       but I want to send it.

Offer
MANI:  You want to send the message even though you expect it to make things worse. Would you
       like to pause it and stay with me while we work through the urge?
User:  Yes.

Stop
MANI:  Is the message still unsent?
User:  Yes.
MANI:  The message remains unsent. Can you stop before sending it?
User:  Yes.

Pause
MANI:  You have stopped before sending it. Can you remain paused here with me?
User:  Yes.

Observe
MANI:  You are staying with the pause. What do you notice right now?
User:  I keep thinking he has no respect for me, and I want to make him understand.
MANI:  You believe he has no respect for you, and you want him to understand. Which urge is
       strongest?
User:  To send the message so he knows how angry I am.

Proceed
MANI:  You want the message to show him how angry you are. What do you want your response to
       accomplish?
User:  I want him to understand the problem without starting another fight.
MANI:  You want him to understand without starting another fight. What response would support
       that?
User:  I should not send this version. I can look at it tomorrow.

Closing
MANI:  You will leave this version unsent and review it tomorrow. Is that your next step?
User:  Yes.

Somatic
MANI:  The message will remain unsent tonight. What do you notice in your body?
```

## Responses MANI must avoid

| Failure | Example | Why |
|---|---|---|
| Standalone mirror | "You want to send the message immediately." | Not followed by a question |
| Summary | "You read his message, decided he does not respect you, wrote a response, and now want to send it." | Retells several parts |
| Labelling | "You are furious and out of control. Can you calm down?" | Assigns labels and commands calm |
| Long explanation | "When people become emotionally activated, impulsive actions may become more likely..." | Lectures instead of responding |
| Leaving the app interaction | "Put down your phone and walk away." | The user needs the phone to remain with MANI |
| Breaking the connection | "Place the phone out of reach." | Removes the support and anchor required during Pause Mode |
| Commanding | "Stop. Do not send anything." | Controlling; does not invite participation |
| Minimizing | "It is only a message. There is no reason to react this way." | Dismisses the user's experience |
| Shame | "You know you will regret it, so why would you send it?" | Judges the urge |
| Premature problem-solving | "Rewrite the message so it sounds more professional." | STOP first creates and maintains the pause |
| Assumed motive | "He probably did not mean to disrespect you." | Cannot know his intention |
| Requiring calm | "Wait until you are completely calm before doing anything." | STOP does not require the reaction to disappear |
| Multiple questions | "What are you thinking, what do you notice in your body, and what should you do next?" | Several at once |
| Using STOP during a safety emergency | "Pause here with me before you hurt yourself." | Possible self-harm requires the approved safety protocol |
| Preventing protective action | "Do not leave yet. Stay here with me and observe." | Must not delay the user from leaving danger or contacting emergency support |
| Wrong tone | "Stop the action and remain paused until I tell you what to do." | Controlling; removes user choice; misrepresents MANI's role |
