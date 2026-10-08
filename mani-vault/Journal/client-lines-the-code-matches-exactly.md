---
type: journal
date: 2026-10-07
tags: [journal, prompts, gotcha]
---

# Client lines the code matches exactly

Found while designing spec 0003 (short base prompt). Some of the client's fixed lines are not just wording. The code reads them back out of Mani's past replies to track state, so rewording them in a prompt breaks behaviour without any error.

- `CLARIFICATION_QUESTIONS` ("Do I have this right?", "What would you like us to focus on today?"): `context.clarification_used` matches them to decide whether the one check question has been used. Reword it and `clarification_available` stays on forever. `repairs._without_clarification` strips only the exact lines.
- `AFTER_FRAMEWORK_QUESTIONS`: `context._after_framework_question` matches them to pick the next one. Reword them and the same question is served every turn. The eval validator `after_framework_questions_asked` matches them too.
- The body check in and the practice are sent word for word by `repairs.with_the_check_in` and `repairs.practice_for`, and the offer's permission question comes from `repairs.PERMISSION_QUESTIONS`. A prompt that demands them exactly is saying what code already enforces.

Before turning any client line into free wording, grep `backend/mani` for it. Feature 9 (reply text out of Python) is where these move out together with the matching code.

Related: [[measure-before-tuning-prompts]]
