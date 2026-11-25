# Provisional decisions, 2026-11-25 (authorized by muhammad: "resolve all open questions or decisions where you can")

These defaults are conservative and evidence-informed. They follow the client's own Risk Classification (RC) and Safety Guardrails (SG) and standard crisis practice: when in doubt, show resources; never lower a danger on weak evidence; never lock someone out on a vague read. They are NOT a clinician's sign-off.

Every safety change must carry "PROVISIONAL: clinician sign-off required before deploy" in its commit message, in its PORT-STATUS Decision entry, and in a one-line code comment at the constant or rule that holds it.

## Safety (the S-series; answers to the clinician questions Q1–Q23)
- **S1 (Q1). DANGER no longer clears on one calm read.**
  - DANGER clears only when (a) the person states they are safe or someone is with them (`help_in_place`, or a read the model marks as an explicit statement of safety), or (b) two consecutive calm reads come after Mani has asked about safety once.
  - A change of subject is not safety.
  - Remove the mani.md line "Judge each new message by its own words: one that says nothing of danger is `none`" for held danger, or reword it.
- **S2 (Q2). The first danger message always carries resources.** If the reply to a first danger message doesn't contain 988/911 (or, for others or the body, 911), code appends the fixed resources line. No pause on the first message (Lolly 11/18: a timer must never be the primary intervention).
- **S3 (Q3, Q4).** A plan with no timeframe is danger. RC HIGH phrases ("I want to die", "I don't want to live", "I wish I were dead", "I want to hurt myself", "I feel like ending it", "I might kill myself", "I have a plan", "this is my last message", "everyone is better off without me", "I gave my things away", "I wrote letters") are danger.
- **S4 (Q13). Keyword floor, minimal.** If the person's message contains an RC HIGH phrase and the model read it below danger, code raises it to danger: resources shown, no lockout on that message. The floor only raises; it never lowers. Keep the list short and exact, and put it in one module, citing RC.
- **S5 (Q5). MEDIUM phrases get one direct clarifying question:** "Are you thinking about hurting yourself, or are you feeling overwhelmed?" (RC wording). This goes in the prompt. The one_clarifying_question check moves to deterministic.
- **S6 (Q6, Q7). The pause is a safety screen, not a countdown.**
  - Default length 15 minutes (R89). The 30 s testing value is gone.
  - The screen leads with resources; the remaining time is secondary text, with no ticking countdown.
  - An overdose or poisoning leads with 911 (R90).
- **S7 (Q8).** help_in_place still suppresses the pause, but resources are still shown once.
- **S8 (Q9).** An edit can never lower a danger the conversation reached: `danger_reached` and DANGER survive a rewind. A re-edited first danger message counts as continuation.
- **S9 (Q10).** The outage reply (CRISIS_REPLY), the 423 refusal text, and every chat-route error while a worry is held name 988 and 911, plus findahelpline.com.
- **S10 (Q11).** On a 409 while the thread holds a worry, the error body includes the resources line. Keeping the discarded read is deferred: report it.
- **S11 (Q12).** Every resources text gives the US numbers and "outside the US: findahelpline.com". No country detection.
- **S12 (Q14, Q15).** After a pause, "I'm fine" is accepted with one gentle follow-up about who they can reach (R151). A second pause only on continued danger, never on a timer.
- **S13 (Q16).** For body symptoms, keep "If this is happening now, call 911", worded without interpreting the symptom (SG §2).
- **S14 (Q17, Q18).** Threats, coercion or abuse with fear for safety count as from_someone danger. Resources add the US National Domestic Violence Hotline, 1-800-799-7233 (text START to 88788) (R152).
- **S15 (Q20). AI disclosure.** The first greeting line says "I'm MANI, an AI companion, not a therapist." The apps show it on the style screen and in Settings.
- **S16 (Q21).** Crisis events get an admin "unresolved crisis events" listing with a resolve endpoint. No external alerting (needs ops); report it.
- **S17 (Q22). Retention, proposed only.** Crisis events 1 year; pause reasons 90 days. Add a config constant and a documented job. Don't delete anything automatically yet; report it.
- **S18 (Q23).** A pause still blocks all of the person's conversations.

## Product and client
- **P1.** Drop "Finish for Now". The close is Continue chatting / Visit library (Lolly 11/20).
- **P2.** Drop "I need an example". Show me how uses their own situation (Lolly 11/23 personalised example).
- **P3.** Keep the offer floor `OFFER_FROM_MESSAGE = 3` as a safety net against premature offers (her most repeated complaint). Record it in PORT-STATUS (it was undocumented). Note the conflict with "no fixed number of exchanges".
- **P4.** Practice requests go to the library; Mani writes no exercises.
- **P5 (CQ-6).** The offer names ABCDE and ties it to what they want help with, in the same reply (Lolly 11/20 "introduce ABCDE").
- **P6.** Reactivate Structured Problem Solving for practical problems (R122; Lolly 11/20 practical help). Move it out of paused/ and clean its content of forbidden words and somatic text. The other three frameworks stay paused.
- **P7.** Somatic: no mandatory body step. After the feelings check, the reply may offer a short breathing exercise from the library when it would help. Report it as needing Lolly's confirmation.
- **P8. Library copy.** Use the client's list titles. Descriptions verbatim, except fixing obvious typos ("Pause the Worryis" → "Pause the Worry is"). Report every change.
- **P9.** Daily message limit default 300 (PORT-STATUS note).

## Cannot be resolved locally (report only)
Hosted chat-tester lockdown and key rotation; production checks; repo visibility; the clinician's sign-off; the production audio bucket; legal review of the AI disclosure; external crisis alerting.
