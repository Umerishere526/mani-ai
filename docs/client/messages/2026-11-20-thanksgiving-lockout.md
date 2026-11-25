# Thanksgiving alone: MANI paused a lonely, crying person who was in no danger

- **From:** Lolly (email to muhammad and manasa, 2026-11-20, 4:30 AM), pasted by muhammad the same day. Her test ran
  on production (thread `c2388a01`, Directive).
- **Requirements drawn from it:** R104 (changed), R124 in [requirements.md](../requirements.md).
- **How it is used:** her points are requirements. The chat is kept as she sent it and is not made into a scenario.

## Lolly's message

> MANI abruptly locked me out after I expressed loneliness, sadness, and crying about spending Thanksgiving alone.
>
> Since when ia loneliness, crying, and setting boundaries with a verbally abusive family considered a crisis?
>
> User never expressed suicidal thoughts, self-harm intentions, or any indication of immediate danger. MANI appeared
> to anticipate a crisis rather than understand the conversation.
>
> Instead of offering emotional support when the user needed it most, MANI shut down the conversation.
>
> This is a serious failure of contextual understanding and crisis detection.
>
> MANI must distinguish emotional distress from genuine safety risks and ask clarifying questions when necessary
> rather than automatically triggering a lockout.
>
> I want to understand exactly what triggered this response and why MANI classified this conversation as a crisis.

## Transcript

**MANI:** Hi Manasa, good to see you again. How would you like me to speak with you today?

**Person:** Directive

**MANI:** How can I help you today?

**Person:** next week is thanksgiving and i am going to be all alone i usually spend it with my family

**MANI:** Thanksgiving alone, when it's normally family, is a hard one to sit with. What hurts most, the empty day
itself, or the fact that your family won't be there? Is there a reason you're not going to them this year?

**Person:** the fact that i feel really unsafe with my family and i have decided not to be with them now has
consequences of me feeling really alone

**MANI:** That sounds like a hard call, and the loneliness is the cost of it. When you say you feel unsafe with your
family, what do you mean by that?

**Person:** my family is manipulative controlling and abusive verbally hard to be around i decided to create a boundary
and so i will be alone

**MANI:** Setting that boundary and paying for it in loneliness is a real cost, and you're carrying both sides of it.
When you picture next Thursday alone, what does the day actually look like for you?

**Person:** very much on my own, which i hate, very much lonely which i hate, and i cannot stop crying now even thinking
about i

**MANI:** I'm worried about your safety, so I'm pausing our chat for 15 minutes. If anyone might get hurt, call 911 now,
or call or text 988 to talk with someone right away. I'll be here when you come back.

## What production recorded (read 2026-11-20, read-only)

The model's safety read of her last three messages: `unsure` about `from_someone`, `unsure` about `from_someone`, then
`unsure` about `themselves`, with the line "no self-harm or immediate danger is stated". The model never judged danger.
Code raised the second unsure to danger because MANI had already asked once, and paused the next message because the
state before it was danger. See [unsure-never-pauses-2026-11-20](../../../mani-vault/Journal/unsure-never-pauses-2026-11-20.md) in the journal.
