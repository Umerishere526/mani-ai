---
type: journal
date: 2026-10-12
tags: [journal, schema, offers, body-route, tests, lessons]
---

# Structured reply fields (2026-10-12)

Spec 0003 built: the model reports its judgments in typed fields, and code sends the client's fixed
text. The reply's shape is picked from the database each turn, so a field that does not apply is not
there to fill. Follows [[general-judgment-over-case-patches-2026-10-12]] and
[[offer-window-owned-by-code-2026-10-12]].

## Lessons

- **A scripted model must parse through the schema the turn sent.** The integration fake used to hand
  back the scripted `Reply` as it was, so a test could fill a field the real call would never accept.
  It now validates each script against the schema it was given, the way the provider's reply is. That
  is what makes "a field outside the moment cannot affect the turn" testable at all.
- **`create_model(__base__=X)` keeps every field of X.** A per style `Offer` built on the base `Offer`
  still carried `lead_line`, so the directive style was asked for a line its template does not have.
  The unit test on the schema's properties caught it; build the variant from a plain config instead.
- **pydantic `extra="ignore"` hides stale test scripts.** After `prompts` and `state.accepted` left
  `Reply`, tests passing them still constructed fine and silently tested nothing. Grep the tests for
  removed field names; a green run is not proof.
- **A typed yes used to depend on the model also reporting `state`.** With no state the row was never
  written and the framework never began. The framework starting this turn now comes from the row (or
  the tapped button), and its phase falls back to `offering` until a reply names a stage.
- **A validator for model mistakes dies with the model's field.** `Button.decline` accepted a word for
  a boolean because the model wrote buttons. Once code writes every button it was dead, so it went.
- **Prompt size:** the supportive ABCDE open offer turn went from 35,752 to 30,718 characters (system
  prompt, `[ctx]` and schema together), mostly the button guidance and the Framework Index's offer
  patterns, which the slot descriptions replace.

## Open

- The live `scenario_check` run (AC-11) is owed and needs muhammad's yes. The scenario file now has an
  `answering_the_offer` group for a no, a moved on, and a yes through the body route.
- The slot descriptions come from the first active framework's template. Only ABCDE is active; a second
  framework with differently worded slots would need them per framework.
