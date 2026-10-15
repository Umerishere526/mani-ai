# Two chat versions, testing confusion, and ABCDE still not explained

- **From:** Lolly
- **To:** muhammad
- **Received:** 2026-10-13
- **Requirements drawn from it:** [R6, R11, R12](../requirements.md#requirements), and the 2026-10-14 deadline row (chat testing only)

"Version A" is the chat built on `fi/run-cleanup`. "Version B" is the chat built on
`feat/abcde-framework-revamp`, merged into ours as PR #33 and changed since. The architecture review
of 2026-10-13 found that B stores nothing more than A. B felt like it remembered better because of a
second model call, effort `high` and questions built from the person's words, which we removed for
R2 and R3 (see [scope feature 18](../../scope/scope.md)).

muhammad's reading of "does not clearly explain what A, B, C, D, and E stand for": the offer shows
the five steps after the permission question, Tell me more keeps the longer explanation, and each
stage opens with its letter and name as the ABCDE document describes.

## As sent

Muhammad,
Thank you for the work you've put into improving the Chat.
Manasa is unavailable between 9 and 10 a.m. ET, but I would like to speak with you directly. I'm finding the testing process increasingly confusing, and with Wednesday approaching, I don't want us to lose another full day trying to understand what has changed, what we're testing, and what still needs to be corrected.

Are we scheduled to speak today, or were you expecting us to test independently? Either way, I would appreciate a call this morning so we can get aligned before proceeding.

Addressing what you sent over yesterday: I wish you had not separated the Chat into two different versions. It complicates a process that we have been working hard to simplify. After reviewing your screenshots and signing into both sites, I have some clear observations, but I also have questions about what has actually been implemented.

Here is my assessment of the two versions:

Version A is closer to the natural conversation we want. Version B appears to have better technology for remembering information the user has already shared.

What we need is to combine the strengths of both. MANI should have a natural conversation, understand why someone is struggling, and offer a framework when appropriate. Once the framework begins, it should remember what the person has already explained rather than asking them to repeat themselves.

The biggest issue I see is that while you are making progress with how the framework functions, neither example demonstrates that MANI truly understands the person's emotional concern. That is what still needs improvement.

I am also confused about what I am actually supposed to be testing. I reviewed your screenshots, signed into the sites, and went through the conversations myself. The ABCDE framework is still not working correctly. Even after MANI introduces the framework and the user agrees to try it, it does not clearly explain what A, B, C, D, and E stand for or guide the user through the framework as we have defined it.

Between the two versions, the screenshots, the conversations, and what I am seeing when I sign in, I am utterly confused about what has changed, what is working, and what I am supposed to evaluate. This process is becoming unnecessarily complicated, and it needs to stop.

I also want to reinforce that this week's priority is exclusively the Chat experience. We are introducing MANI to beta users in stages. Wednesday is for Chat testing only. We are not introducing the full app or new front-end designs until next week.

With Wednesday approaching, I am concerned about how little time remains for corrections, testing, and confirming that the complete conversational experience works properly.

I appreciate your efforts, Muhammad. I know you are working hard on this, but we need to simplify the process, consolidate what is working, and focus on getting one Chat experience right.

Lolly
