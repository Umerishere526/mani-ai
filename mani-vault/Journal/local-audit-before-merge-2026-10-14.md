# Local audit before merge (2026-10-14)

The uncommitted ABCDE / working-read work was audited file by file, against the local Supabase,
before it goes to main. Nothing committed; prod read only. Related: [[abcde-names-and-confirms-its-stages-2026-10-14]],
[[mani-forms-a-read-instead-of-mirroring-2026-10-13]], [[latency-azure-stall-and-redraft-amplification-2026-10-14]].

## Fixed, each with a test

- **Stage rules contradicted each other.** `[ctx]` meanings, `response_format.md` ("skip the ones they have
  already answered"), the `TechniqueState.step` and `stages_known` schema descriptions and two `mani_base.md`
  lines still said skip or jump stages; the decided rule is say it back as a possibility, check it, one
  stage a reply. All now say the same thing.
- **A partial read wiped the stored one.** `repairs.carried_read` keeps their slots when a reply leaves them empty.
- **Their words in `read_*` lines could close `[ctx]`.** Disarmed like the message.
- **A framework reply with no `state` escaped "never a third ask".** It wrote no row, so `stage_asks` never
  counted it and the move-on never fired. `repairs.apply` now takes it as asking the stage in force.
- **`stage_already_in_the_read` sent a partial stage back** when one of its slots was filled, against
  "partial asks only for the gap". Now partial only when every slot is filled.
- **`asks_what_is_known` sent back new questions against the read** ("Is the client still changing
  requirements?" scored 0.75 against a slot). Against the read only a question made wholly of its words (a
  final s aside) counts now. In two scenario runs the read check never fired; all its redrafts are the
  earlier-question check.
- **Redraft budget.** A turn's model calls share 25 s; a redraft gets what is left, not under 5 s.
- **Sentry would have received the person's message.** `send_default_pii=False` does not cover request
  bodies or frame locals; sentry-sdk 2.x attaches both by default. `max_request_body_size="never"` and
  `include_local_variables=False`; `test_error_reports.py` sends a real error through the app.
- **Completing an unknown exercise was a 500** (FK violation unhandled). Now 404, in a savepoint.
- **`scenario_check` "asks what they already said" only looked at the last message** (`said` shadowed).
- Cron secret compared in constant time. The YAML-mapping test now walks nested lists, which found one
  in `response_format.md` reasoning steps (and caught one I introduced while fixing the wording).

## Verified clean

- No route takes identity from body, query or header; every thread-id query checks the owner. Forged
  admin claim, anon key, cross-user GET/PATCH/POST/DELETE all refused live with real local tokens.
- Migrations 001-012 apply from scratch on a throwaway Postgres; grants and RLS suites pass there and on
  local. Local history had 011/012 hand-applied; recorded with `supabase migration repair --local`.
- `working_read` stays `text`: only the backend reads it, whole. All 7 local values parse.
- Local data had no test leftovers or orphans; nothing deleted.
- A full ABCDE walk per style through the HTTP API: label and consent line on the first stage, one stage a
  reply, confirm then move, the body route word for word, Chat More / Go to Library, no HTTP errors. The
  supportive walk asked E three times; that is the decided exemption (`Framework.closing` is the last stage
  before the body route, and `may_skip` is false for it), not a leak in the ceiling. "In my chest" at the
  check-in skips the place buttons by design; "Kind of tight" brings them.
- Hosted, read only: back at `010` (see [[duplicate-migration-versions-after-merge-2026-10-06]]), prompts from
  the 2026-10-09 seed, RLS on everywhere. The order and rollback are in
  `docs/superpowers/plans/2026-10-14-prod-runbook-stage-asks-and-working-read.md`.

## Deferred, needs muhammad

- `abcde.md` `activate` purpose/ready_when say a clear event needs no check, and the supportive and
  reflective `confirm` lines state the event as settled. Client copy, so not edited.
- `question_focus` for Direct ("what they would want to be different") against `mani_base`'s "never ask
  what they would change before they bring it up".
- `mani_base` says ABCDE fits a situation **and** a belief or feeling; `abcde.md` `central_indication` says
  **or**, with the event optional.
- Voice upload read whole into memory before the 25 MB check; `daily_message_limit` defaults to off.
- Production's Vercel environment sets no `SENTRY_DSN` (no error reports at all) and no `DAILY_MESSAGE_LIMIT`.
  7 `@example.com` accounts are in prod.
- `scenario_check.py`'s "asks a question it already asked" counts the question frame, as the redraft check did:
  of 11 flagged pairs one was a real repeat. Left alone so the measure did not move with the code it measures.
- The prompts say one stage per reply, never skipped, but `techniques.validate_transition` still accepts a
  jump of several stages, and only `redraft.ledger_stage` (trusting the model's own ledger) stands in the way.
  The comments in `techniques.py` and `repairs.py` still give the old reason ("a stage their words already
  answer is left unasked"). muhammad chose to leave code and comments as they are for now (2026-10-14).
  Options were: redraft a reply that jumps more than one stage, clamp the recorded stage to one forward
  (risks the stage on record disagreeing with what the reply asked), or correct the comments only.

## Done after the audit, at muhammad's go-ahead (each flagged as a behaviour change)

- Production refuses to start with `AI_DEBUG_MODE=true`.
- A deleted account's token: writes now 401 (the `*_user_id_fkey` failure), not 500. No per-request user lookup.
- A typed yes is held to the first-stage checks a tap gets: `_why` judges the draft from the stage it starts.
- Redrafts went from 23-27% of replies to 9.5-11% (main about 3% of calls; this tree 60% earlier the same day,
  see [[latency-azure-stall-and-redraft-amplification-2026-10-14]]). Two causes, found by capturing what made each
  check fire across a scenario run and labelling it by hand:
  - The earlier-question check counted the words every question is put in. "What did your manager do?" has three
    words of four letters or more, two of them "what" and "your", so it matched almost anything. Leaving the frame
    out took different-question firings from 17 of 26 to 4 of 12 and kept 8 of 9 real repeats.
  - `same_unknown` assumed they had answered in between. Mostly they had not ("idk", "No, I'm not angry"), so
    the model was right to want the same thing and the redraft changed nothing 11 times in 17. muhammad chose to
    note it rather than redraft it.

## Low, recorded only

Tell me more: the model's two sentences are discarded when the framework has `explain`. `_MEANING["offer"]`
describes the paused `dbt_stop`. `support_check` needs situation and impact while `mani_base` says impact
or response. `dispute`/`effective` have no `confirm`. `stage_check` is sent on offering and somatic turns.
The third-ask repair inserts the next stage's `ask` word for word. Framework `body`, `appropriate_when`,
`not_when`, `somatic.md` `prompts` are seeded but never read. Users B listing A's messages get 200 with an
empty list rather than 404 (nothing leaks). A finished technique row can reach `stage_asks = 2` (harmless).

## Method that paid off

Reading the write path, not just the read path: the no-`state` gap only shows when asking "which turns
write the row that counts". And a live run with real tokens found two 500s no unit test could.

`scripts/scenario_check.py` configures no logging, so run bare it reports flags and no redrafts; a run showing
zero redrafts is that, not a clean model. Wrap it in `logging.basicConfig(level=logging.INFO)`.

A redraft count says how often a check fires, not whether it is right. Patching the checks in-process to record
what they fired on (the person's message, both questions or both unknowns) and labelling 40-odd samples by hand
settled in minutes what thresholds had been argued over. Word-overlap checks over short questions are dominated
by their frame words; any new one should leave them out.
