# 0006. Rationale: the main model is chosen on real conversations

The decision record behind [index.md](index.md).

## Context

Mani's chat turn is one structured model call (ADR 002), and since spec 0005 the model must also fill a checklist of facts quoted in the person's words; the code chooses the framework from it. The current model marked general stress as panic and as "cannot control", marked "do not know where to begin" as "cannot begin", and changed the checklist every turn, so the stress chat got ACT in 3 of 3 runs, the grief chat got no offer, and the deadlines chat got the wrong framework. The code did what spec 0005 says; its input was too noisy. Whether that is the model or the design needs a stronger model on the same chats.

How a call is configured today. `content/prompts/mani_base.md` names `model_id` and `model_parameters` (only `temperature: 1`), seeded into `admin.prompts`; `composer.model_settings(config)` returns them, and the orchestrator uses them for the first draft, the redraft and the exercise pick (`client.choose_exercise`, temperature 0.7, 200 tokens). Titles are not a row of their own: `title_generation` is a layer added to the chat prompt, so titles come from the chat model. Summaries (`summarization.md`) and memory folding (`memory_fold.md`) have their own rows, today the same lite model. `client.complete` passes only temperature and max tokens (default 2048) to `chain.build`, which sends the provider routing and `usage` in the request body; reasoning effort is never sent. Every call is pinned to `google-ai-studio` with no fallbacks and `data_collection: deny`; `admin.prompts.routing` can override that, but `scripts/seed.py` does not write it, and the admin portal can. In development the prompt cache lasts one second, so the config is reread from the database almost every turn.

Live data from OpenRouter on 5 October. Gemini 3.8 Flash has a zero data retention route only on Google Vertex; Google AI Studio has none, and keeps prompts for abuse monitoring. The current lite model is pinned to AI Studio, so production chat is probably not zero retention today. Vertex standard (`google-vertex/global`) costs 0.75 / 3.75 dollars per million input / output tokens, cached input 0.075, reasoning billed as output, median first response about 2.9 s, degraded at 91 percent uptime in the half hour checked; Vertex flex had a 37 s median and is not usable for chat. The lite model on AI Studio costs 0.25 / 1.50. 3.8 Flash scores 40.9 on Artificial Analysis' intelligence index, the lite family's scored sibling about 22; those scores measure reasoning and coding, not our checklist. About 3.73 dollars of credit remain, and real runs need muhammad's yes each time. Conversation content is special category health data.

## Options considered

### Option 1: The in family upgrade only (chosen)
Gemini 3.8 Flash against the lite model's results on the same chats.

**Pros**:
- About 0.70 dollars, inside the remaining credit.
- The smallest switch: same family, same structured output path, implicit caching.
- Answers, for this model, effort and route, whether spec 0005's chats can be passed.

**Cons**:
- Does not meet row 35's four candidates, two open models; that comparison stays open.
- Changes model, effort and route together, so a miss does not say which.

### Option 2: Five candidates across families
Gemini 3.8 Flash, Claude Sonnet 5.5, GPT-6 Luna, Qwen 3.8 27B and MiniMax M3 on the same chats.

**Pros**:
- Meets row 35; shows whether quality differs by family.

**Cons**:
- Several times the cost; each non Gemini candidate needs its own route and zero retention check; OpenAI routes are moderated, a risk for messages about self harm.

### Option 3: Keep the model, redesign the facts
Spend nothing on models; change spec 0005 instead.

**Pros**:
- No model spend or cost change.

**Cons**:
- Builds on an unproven diagnosis; if the model is the cause, the redesign is wasted.

## Rationale

The open question after spec 0005 is whether its failures come from the model, and the cheapest experiment is one clearly stronger model on the same chats. Staying in the Gemini family keeps the structured output path and caching equal, though the route changes from AI Studio to Vertex because only Vertex keeps no data for this model. muhammad chose this over the five candidate comparison to fit the budget, accepting that row 35 stays open. Low reasoning effort keeps delay and hidden output cost down; reading the checklist is not a hard puzzle, and max tokens is raised to 4096 so thinking cannot cut a reply off and fail it for a setting rather than the model. muhammad first chose the cheaper flex tier, but flex has no zero retention route on AI Studio and a 37 second median on Vertex, so Vertex standard was chosen instead. Three runs on the chats that tell the models apart, because the lite model went 1 of 3 and then 0 of 3 on the stress chat; one run on the two it already passed. The journey run is there because the switch also moves titles and the exercise pick, which none of the five chats reaches. A miss goes back to muhammad as it is, because changing model, effort and route together means a miss cannot alone indict the design.
