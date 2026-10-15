# Job decision: testing feedback in all three styles

- **From:** Lolly
- **To:** muhammad
- **Received:** 2026-10-12
- **Scenario:** `job_decision` in [scenarios.json](../../../backend/scripts/scenarios.json)
- **Requirements drawn from it:** [R3, R4](../requirements.md#requirements)

The style is written "Direct", the name before migration 019, so it was most likely tested on the
build deployed before the changes of 2026-10-12.

## As sent

MANI Direct Test: Job Decision:
1. Repetitive and Unnatural Mirroring
USER SAID: I'm facing an important decision, and I keep going back and forth. Every time I think I've made up my mind, I start questioning myself again. I'm frustrated because I don't understand why I can't just decide.

MANI: "The frustration of questioning yourself again just when you thought you’d decided is clear."

Better response: "You've been going back and forth, and neither choice feels quite right yet. What's the decision you're trying to make?"

2. Repetition and Premature Narrowing
MANI: "You’re afraid of choosing wrong when there are good reasons for both options. What feels most uncertain about what might happen if you accept the new job?"

Better response:"What's making the new opportunity appealing, and what's making you consider staying?"

This explores both sides without repeating the user's fear or prematurely focusing on one option.

MANI Supportive Style: Testing Feedback and Red Flags:
1. Unnatural and Repetitive Mirroring
User said: "I'm facing an important decision, and I keep going back and forth. Every time I think I've made up my mind, I start questioning myself again. I'm frustrated because I don't understand why I can't just decide."
MANI responded: "That repeated second-guessing sounds frustrating, especially when you feel close to deciding. What part of this choice leaves you feeling most unsure?"
What is not working: MANI repeats the user's frustration and second-guessing rather than responding naturally. It also asks what part of the choice feels uncertain before understanding what decision the user is facing.
Better Supportive response: "Making a decision can be difficult when you keep questioning yourself. What's the decision you're facing?"

IMPORTANT: Mirroring should confirm understanding when needed, not simply restate the user's words or emotions.

 MANI REFLECTIVE Style: Testing Feedback and Red Flags:
1. Unnatural and Repetitive Mirroring
User said: "I'm facing an important decision, and I keep going back and forth. Every time I think I've made up my mind, I start questioning myself again. I'm frustrated because I don't understand why I can't just decide."
MANI responded: "You get close to deciding, then doubt draws you back in, and not understanding that pattern is frustrating. What thought tends to come back when you start questioning your choice?"
What is not working: MANI repeats the user's experience of second-guessing and frustration instead of responding naturally. The language feels constructed rather than conversational.
Better Reflective response: "Sometimes the hardest part of a decision is understanding what's keeping you from making it. What decision are you facing?"
IMPORTANT: Mirroring should demonstrate understanding, not simply rephrase what the user has already expressed.

2. Unnecessary Mirroring Before a Good Reflective Question
MANI responded: "There are good reasons on both sides, but the possibility of choosing wrong keeps bringing you back to doubt. What would making the wrong choice mean to you?"
What is working: The question is appropriate for Reflective style. It encourages the user to examine what making the wrong choice represents to them rather than simply listing the advantages of each option.
What could improve: The opening sentence repeats what the user has already expressed. The reflective question itself is strong and should remain.
Better response: "What would making the wrong choice mean to you?”
This encourages reflection while allowing MANI to understand both sides of the decision.
