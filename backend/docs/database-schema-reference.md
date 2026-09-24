# Database schema reference

Complete, verified map of every schema, table, column, role, and grant in this project's
database — queried live from `information_schema`/`pg_catalog`, not reconstructed from the
migration files. Regenerate rather than hand-edit if the schema changes (§ at the bottom
has the exact queries) — every table below reflects the state after migrations 001–005.

Generated 2026-09-23 against local Supabase (`supabase_db_mani`). Nothing here was typed
from memory — every table, column, constraint, policy, and grant was queried directly from
`pg_catalog`/`information_schema` and is reproducible with the queries noted per section.

## 1. What's Supabase-default vs. what this project added

**Nothing in this project alters a Supabase-default table, role attribute, or system
role.** Every table, every grant beyond the platform's own, and every RLS policy below was
added by this project's five migrations (`001` through `005`). The only things touched
outside plain `CREATE`/`GRANT`/`CREATE POLICY` are the documented, intended configuration
surface Supabase itself exposes for exactly this purpose: `supabase/config.toml` (email
confirmation, password policy, exposed schemas — see `.claude/SUPABASE.md`).

**Platform-default and left alone:** the `auth` schema and its tables (`auth.users` etc.),
the `storage`/`realtime`/`supabase_functions` schemas, and the base attributes of every
role Supabase creates (`anon`, `authenticated`, `service_role`, `authenticator`,
`supabase_auth_admin`). This project only ever *adds* grants and policies on top of these —
never edits what Supabase itself defines. One attempt to alter a Supabase role
(`ALTER ROLE supabase_auth_admin BYPASSRLS`, considered during migration 005) was
**refused by Postgres itself** — `supabase_auth_admin` is a reserved role, lockable even
from the `postgres` role this project connects as. That refusal is the platform's own
boundary, not a choice this project made, and migration 005 works within it (see §5).

**This project's own additions, in full:**
- Schema: `admin` (config/analytics data, invisible to PostgREST by design)
- Role: `mani_service` (the backend's own DB identity — see §4)
- 14 tables (8 in `public`, 6 in `admin` — §3)
- Every RLS policy and every grant on those 14 tables (§4, §5)

## 2. Tables, by schema

Query: `select n.nspname, c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname in ('public','admin') and c.relkind='r' order by n.nspname, c.oid;`

| Schema | Table | What it holds |
|---|---|---|
| `admin` | `frameworks` | The six conversational frameworks (ABCDE, DBT STOP, etc.) — content, stage data, router phrase lists. |
| `admin` | `prompts` | The live system prompt layers (`mani_base`, `response_format`, etc.), one row per named prompt. |
| `admin` | `prompt_versions` | Snapshot of a prompt's content every time it's edited, for audit/rollback. |
| `admin` | `exercises` | The exercise catalog (currently empty — see `PORT-STATUS.md`). |
| `admin` | `crisis_events` | One row per crisis-flagged turn, for care-team review. |
| `admin` | `llm_calls` | One row per model call — tokens, latency, cost tracking. |
| `admin` | `user_memory` | What Mani has learned about one person across conversations - backend and admins only (ADR-005). |
| `public` | `profiles` | Onboarding data — nickname, topics, support style. Auto-created on signup (migration 004). |
| `public` | `threads` | One conversation. |
| `public` | `messages` | Every message in every thread, both sides. |
| `public` | `thread_technique_state` | Which framework is active in a thread, and its current phase. |
| `public` | `thread_techniques_offered` | Frequency-limiting: which frameworks have already been offered in a thread. |
| `public` | `thread_response_styles` | The model's self-reported response shape/voice per reply — anti-repetition signal. |
| `public` | `thread_summaries` | The rolling summary of a long thread, refreshed every 20 messages (the history window). Written by the backend only (migration 007). |
| `public` | `exercise_completions` | Whether a user found a completed exercise helpful. |

`admin.*` is **invisible to PostgREST** — `supabase/config.toml`'s `[api] schemas` lists
only `public`/`graphql_public`. A request for an `admin` table returns 404, not 403, even
with the service-role key. This is deliberate (`.claude/SUPABASE.md`) — treat any change to
that `schemas` list as a security-relevant decision, not a convenience tweak.

## 3. Every column, in defined order

Query for columns: `select a.attnum, a.attname, format_type(a.atttypid,a.atttypmod), a.attnotnull, pg_get_expr(ad.adbin,ad.adrelid) from pg_attribute a join pg_attrdef ad on ...` (full query in git history of this file). Query for constraints: `select conname, pg_get_constraintdef(oid) from pg_constraint where conrelid = '<table>'::regclass;`

Legend: **PK** primary key · **FK** foreign key · 🔒 CHECK-constrained closed set (must match the code-side enum noted) · *default* shown only when non-obvious.

### `public.profiles`
One row per user, created automatically by the migration-004 trigger on signup.

| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `user_id` | uuid | **PK**, FK→`auth.users(id)` cascade | Same id as the Auth user. Deleting the auth user deletes this row. |
| 2 | `nickname` | text | optional | 1–40 chars if set (CHECK `profiles_nickname_sane`). |
| 3 | `topics` | text[] | default `'{}'` | Free-text topics from onboarding. At most 10, 600 chars in total (CHECK `profiles_topics_bounded`, migration 008) - pasted into every system prompt. |
| 4 | `support_style` | text | optional 🔒 | `supportive` / `reflective` / `direct` (CHECK `profiles_support_style_known`). Matches `mani.models.rows.SupportStyle`. The onboarding default; a thread's own `conversation_style` overrides it. |
| 5 | `age_bracket` | text | optional | **Not constrained** — see §6. |
| 6 | `created_at` | timestamptz | default `now()` | |
| 7 | `updated_at` | timestamptz | default `now()`, touched by trigger | |

### `public.threads`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `user_id` | uuid | FK→`auth.users` cascade | Owner. |
| 3 | `title` | text | optional | Auto-generated after enough messages. |
| 4 | `message_count` | integer | default `0` | Maintained by the `messages_sync_count` trigger — never written directly by a user (not in their UPDATE grant). |
| 5 | `crisis_detected` | boolean | default `false` | One-way flag — no UPDATE policy lets a user clear it (`.claude/SUPABASE.md`'s own headline example of why RLS matters here). |
| 6 | `created_at` | timestamptz | default `now()` | |
| 7 | `last_message_at` | timestamptz | default `now()` | Maintained by the same trigger as `message_count`. |
| 8 | `deleted_at` | timestamptz | optional | Soft-delete marker. |
| 9 | `conversation_style` | text | optional 🔒 | `supportive` / `reflective` / `direct` (CHECK `threads_conversation_style_known`). Wins over `profiles.support_style` when set — see `mani/chat/context.py:resolve_style`. |
| 10 | `vague_streak` | smallint | default `0`, 0–10 (CHECK) | Currently written by nothing (`PORT-STATUS.md` "Open" — the vague-reply pivot isn't built). |
| 11 | `memory_folded_at` | timestamptz | optional | The last message folded into `admin.user_memory`; null means never. Only `mani_service` may write it (migration 009). |

### `public.messages`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `thread_id` | uuid | FK→`threads` cascade | |
| 3 | `user_id` | uuid | FK→`auth.users` cascade | Denormalized from the thread, for RLS. |
| 4 | `role` | `message_role` (enum) | required | `user` or `mani`. |
| 5 | `content` | text | required, non-blank (CHECK `messages_content_not_empty`) | |
| 6 | `prompt_options` | jsonb | optional | The capsule buttons under a Mani reply — see `SmartPrompt` in `mani/llm/schema.py`. |
| 7 | `selected_prompt` | text | optional | Which capsule label the user tapped, if any. |
| 8 | `client_message_id` | uuid | optional, UNIQUE with `user_id` | Idempotency key for retried sends. |
| 9 | `created_at` | timestamptz | default `clock_timestamp()` | `clock_timestamp()`, not `now()` — advances within one transaction, so paired user/Mani rows get distinct timestamps. |

### `public.thread_technique_state`
One row per thread — the currently (or most recently) active framework.

| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `thread_id` | uuid | **PK**, FK→`threads` cascade | One active technique per thread, enforced by the PK itself. |
| 2 | `user_id` | uuid | FK→`auth.users` cascade | |
| 3 | `framework_id` | text | FK→`admin.frameworks(id)` **RESTRICT** | Can't delete a framework a thread is using. |
| 4 | `outcome` | `technique_outcome` (enum) | required | `offered` / `accepted` / `declined`. |
| 5 | `phase` | text | optional | Current stage id within the framework. `null` when finished. |
| 6 | `at_message_count` | integer | required | Thread's `message_count` when this state was last written — the cooldown clock. |
| 7 | `library_offered_since` | boolean | default `false` | Whether the library follow-up has been offered since acceptance. |
| 8 | `updated_at` | timestamptz | default `now()`, touched by trigger | |

### `public.thread_techniques_offered`
Frequency-limiting log — every framework ever offered in a thread.

| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `thread_id` | uuid | **PK** (composite with #2), FK→`threads` cascade | |
| 2 | `framework_id` | text | **PK** (composite), FK→`admin.frameworks` RESTRICT | |
| 3 | `user_id` | uuid | FK→`auth.users` cascade | |
| 4 | `offered_at` | timestamptz | default `clock_timestamp()` | |

### `public.thread_response_styles`
Append-only log of the model's self-reported style per reply.

| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `thread_id` | uuid | FK→`threads` cascade | |
| 3 | `user_id` | uuid | FK→`auth.users` cascade | |
| 4 | `shape` | text | required 🔒 | One of 6 values (CHECK `response_styles_shape_known`, added migration 003). Matches `SHAPES` in `mani/llm/schema.py`. |
| 5 | `voice` | text | optional 🔒 | One of 5 values or null (CHECK `response_styles_voice_known`). Matches `VOICES` in `mani/llm/schema.py`. |
| 6 | `created_at` | timestamptz | default `clock_timestamp()` | |

### `public.thread_summaries`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `thread_id` | uuid | **PK**, FK→`threads` cascade | |
| 2 | `user_id` | uuid | FK→`auth.users` cascade | |
| 3 | `summary` | text | optional | 2–4 sentence prose summary. |
| 4 | `techniques_tried` | jsonb | default `'[]'` | List of `{name, helpful, context}` — see `TechniqueTried` in `mani/models/rows.py`. |
| 5 | `summarized_through_message_id` | uuid | FK→`messages` SET NULL | Watermark — where the next summarization run picks up. |
| 6 | `summarized_message_count` | integer | default `0`, `>= 0` (CHECK) | |
| 7 | `created_at` | timestamptz | default `now()` | |
| 8 | `updated_at` | timestamptz | default `now()`, touched by trigger | |

### `public.exercise_completions`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `user_id` | uuid | FK→`auth.users` cascade | |
| 3 | `exercise_id` | uuid | FK→`admin.exercises` cascade | |
| 4 | `helpful` | boolean | optional | User's own feedback. |
| 5 | `completed_at` | timestamptz | default `now()` | |

### `admin.frameworks`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | text | **PK** | e.g. `dbt_stop`, `abcde`. |
| 2 | `name` | text | required | Display name. |
| 3 | `summary` | text | required | One-line description. |
| 4 | `body` | text | required | **Written, never read** — see §6. |
| 5 | `activation_conditions` | text | default `''` | **Written, never read for routing** — superseded by column 12. |
| 6 | `phases` | text[] | required, non-empty, `phases[1]='offering'` (CHECK) | Ordered stage ids. |
| 7 | `display_order` | integer | default `0` | |
| 8 | `is_active` | boolean | default `true` | |
| 9 | `created_at` | timestamptz | default `now()` | |
| 10 | `updated_at` | timestamptz | default `now()`, touched by trigger | |
| 11 | `stages` | jsonb | default `'{}'`, must be a JSON object (CHECK) | Per-phase content: purpose, listen_for, ready_when, boundaries, `ask.{style}`. |
| 12 | `activation` | jsonb | default `'{}'`, must be a JSON object (CHECK) | `strong_signals`/`signals`/`distinctions` — what `mani/chat/router.py` actually reads. |

### `admin.prompts`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `name` | text | required, **UNIQUE** | e.g. `mani_base`, `response_format`. |
| 3 | `description` | text | default `''` | |
| 4 | `content` | text | required | The live prompt text (seeded from `content/prompts/*.md`). |
| 5 | `version` | integer | default `1`, `> 0` (CHECK) | |
| 6 | `model_id` | text | optional | Overrides the default model for this prompt. |
| 7 | `model_parameters` | jsonb | default `'{}'` | e.g. `temperature`, `maxTokens`. |
| 8 | `routing` | jsonb | default `'{}'` | OpenRouter provider routing overrides. |
| 9 | `is_active` | boolean | default `true` | |
| 10 | `created_by` | uuid | FK→`auth.users` SET NULL | |
| 11 | `updated_by` | uuid | FK→`auth.users` SET NULL | |
| 12 | `created_at` | timestamptz | default `now()` | |
| 13 | `updated_at` | timestamptz | default `now()` | |

### `admin.prompt_versions`
Snapshot taken automatically whenever `admin.prompts` is edited via the admin API.

| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `prompt_id` | uuid | FK→`admin.prompts` **RESTRICT**, UNIQUE with #3 | |
| 3 | `version` | integer | required | |
| 4 | `content` | text | required | |
| 5 | `model_id` | text | optional | |
| 6 | `model_parameters` | jsonb | default `'{}'` | |
| 7 | `routing` | jsonb | default `'{}'` | |
| 8 | `change_summary` | text | optional | |
| 9 | `created_by` | uuid | FK→`auth.users` SET NULL | |
| 10 | `created_at` | timestamptz | default `now()` | |

### `admin.exercises`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `title` | text | required | |
| 3 | `subtitle` | text | optional | |
| 4 | `description` | text | default `''` | |
| 5 | `type` | text | optional | **Not constrained, and not read anywhere in the backend** — see §6. |
| 6 | `category` | text | required | **Not constrained** — see §6. |
| 7 | `audio_path` | text | required | Storage path, signed on demand by `mani/storage.py`. |
| 8 | `duration_minutes` | numeric(5,2) | optional | |
| 9 | `display_order` | integer | default `0` | |
| 10 | `show_on_home_screen` | boolean | default `false` | |
| 11 | `is_active` | boolean | default `true` | |
| 12 | `created_at` | timestamptz | default `now()` | |
| 13 | `updated_at` | timestamptz | default `now()` | |
| 14 | `framework_id` | text | optional, FK→`admin.frameworks` SET NULL | Which framework's completion offers this exercise. |

### `admin.crisis_events`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `thread_id` | uuid | FK→`threads` cascade | |
| 3 | `user_id` | uuid | FK→`auth.users` cascade | |
| 4 | `message_id` | uuid | optional, FK→`messages` SET NULL | |
| 5 | `reason` | text | required | e.g. `"safety screen: suicide"`. |
| 6 | `detected_at` | timestamptz | default `now()` | |
| 7 | `resolution` | text | optional | **Read by the admin API, written by nothing** — the triage workflow is unfinished (`PORT-STATUS.md`). |
| 8 | `resolved_at` | timestamptz | optional | Same gap — `unresolved=true` currently matches every row ever written. |

### `admin.llm_calls`
| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `id` | uuid | **PK**, default `gen_random_uuid()` | |
| 2 | `thread_id` | uuid | optional, FK→`threads` SET NULL | |
| 3 | `user_id` | uuid | optional, FK→`auth.users` SET NULL | |
| 4 | `message_id` | uuid | optional, FK→`messages` SET NULL | |
| 5 | `prompt_version_id` | uuid | optional, FK→`admin.prompt_versions` SET NULL | **Always null in practice** — no call site passes it (`PORT-STATUS.md`). |
| 6 | `purpose` | `admin.llm_call_purpose` (enum) | required | `chat` / `summarize` / `exercise_select` / `memory_fold`. Made a real enum in migration 006 — was free text; see §6's now-resolved note. `memory_fold` added in 009. |
| 7 | `model` | text | required | |
| 8 | `input_tokens` | integer | default `0` | |
| 9 | `output_tokens` | integer | default `0` | |
| 10 | `cached_input_tokens` | integer | default `0` | |
| 11 | `latency_ms` | integer | default `0` | |
| 12 | `outcome` | `admin.llm_call_outcome` (enum) | required | Correctly enum-typed, unlike `purpose`. |
| 13 | `error_message` | text | optional | |
| 14 | `created_at` | timestamptz | default `now()` | |

### `admin.user_memory`
Patterns about one person across their conversations, folded in as each finishes (migration 009, ADR-005). Health data: `authenticated` holds nothing on it; only `mani_service` reads and writes it, and RLS scopes that to the caller's own row - the one `admin` table with RLS.

| # | Column | Type | Required | Purpose |
|---|---|---|---|---|
| 1 | `user_id` | uuid | **PK**, FK→`auth.users` cascade | Deleted with the account (also as `supabase_auth_admin`, which has its own DELETE policy). |
| 2 | `memory` | jsonb | default `'{}'` | `{themes, low_times, better_times, what_helps, what_doesnt, how_they_talk}` - `Memory` in `mani/llm/schema.py`. At most 6 entries of 160 chars per list, enforced in `mani/memory.py`. |
| 3 | `updated_at` | timestamptz | default `now()` | |

## 4. Roles — what each one is and what it can actually do

Query: `select rolname, rolsuper, rolinherit, rolcreaterole, rolcanlogin, rolbypassrls from pg_roles where rolname in (...);` and `select r.rolname, m.roleid::regrole from pg_auth_members m join pg_roles r on r.oid=m.member;`

| Role | Login? | Bypasses RLS? | Who/what actually connects as this | Purpose |
|---|---|---|---|---|
| `anon` | no (assumed via `authenticator`) | no | PostgREST, for an unauthenticated request | Holds **zero** privilege on any table in this project (confirmed: `tests/sql/test_grants.sql` asserts it). The anon key is public by design; safety depends entirely on this role having nothing to abuse. |
| `authenticated` | no (assumed via `authenticator`) | no | PostgREST, for a request carrying a valid user JWT | What a signed-in user's own request acts as when going through PostgREST directly (not through this backend). Holds the column-scoped, RLS-gated grants in §5 — never full-table access. |
| `service_role` | no (assumed via `authenticator`) | **yes** | Anything presenting the service-role key | Full, RLS-bypassing access. Never reaches a client — `backend/mani/config.py`'s `supabase_service_role_key` is the only place this key lives, and it's used only for Storage signing (`mani/storage.py`) and, since this session, the Auth Admin API (`mani/auth_admin.py`). |
| `authenticator` | **yes** | no | PostgREST's own connection | The role PostgREST logs in as. Not used to do anything itself — it's a member of `anon`, `authenticated`, **and** `service_role`, and `SET ROLE`s to whichever one a request's JWT specifies. This is stock Supabase/PostgREST architecture, not a project decision — confirmed live (`pg_auth_members`). |
| `supabase_auth_admin` | **yes** | no | GoTrue (Supabase Auth), confirmed via `GOTRUE_DB_DATABASE_URL` | Owns `auth.users` and everything under `auth.*`. Since migration 005, also holds the narrow, table-specific grants and RLS policies needed to complete the cascades this project's own `on delete cascade`/`set null` foreign keys promise when it deletes a user (§3, §5). **Cannot be granted `BYPASSRLS`** — confirmed live, Postgres refuses even from `postgres` here, because it's a reserved role. |
| `mani_service` | no (assumed by the backend via `SET LOCAL ROLE`) | no | This backend, for every ordinary request | A member of `authenticated`, so it inherits everything that role can do, **plus** a handful of privileges an ordinary user must not have: EXECUTE on the three `security definer` functions (`create_message_pair`, `mark_thread_crisis`, `create_greeting`) DELETE on `thread_technique_state`, INSERT/UPDATE on `thread_summaries` and `thread_technique_state` (moved off `authenticated` in migration 007, since both feed the model), SELECT/INSERT/UPDATE on `admin.user_memory`, and UPDATE on `threads.memory_folded_at` (migration 009). RLS still applies — the extra privileges are never a wider view of rows, only a wider set of actions (`.claude/SUPABASE.md`). **Never grant this to `authenticator`** — that would let PostgREST assume it directly and undo the separation (asserted by `tests/sql/test_grants.sql`, confirmed still true here — `mani_service` is absent from `authenticator`'s memberships). |
| `postgres` | yes | yes | Migrations, and anyone connecting directly (e.g. `supabase status`'s credentials) | **Not a true superuser on this platform** (`rolsuper = false`, confirmed live) — Supabase deliberately keeps its own internal roles (like `supabase_auth_admin`) out of reach even from this role, which is why migration 005 could not simply `ALTER ROLE ... BYPASSRLS`. |

## 5. RLS policies — one row per operation, per table, per role

Query: `select schemaname, tablename, policyname, cmd, roles, qual, with_check from pg_policies where schemaname='public';`

Every `public` table has RLS enabled and a **policy per operation** (`select`/`insert`/`update`/`delete`), never one broad `for all` policy — a broad policy hides mistakes (`.claude/SUPABASE.md`). The pattern, present on every row-owning table:

```sql
using ( (select auth.uid()) = user_id )
```

— wrapped in a `select` so Postgres caches it once per statement rather than evaluating it per row. Four tables (`thread_technique_state`, `thread_techniques_offered`, `thread_response_styles`, `thread_summaries`) additionally check **thread ownership**, not just `user_id`, on INSERT/UPDATE (migration 003 — this was a real, fixed gap, see that migration's comments):

```sql
with check (
  (select auth.uid()) = user_id
  and exists (select 1 from threads t where t.id = thread_id and t.user_id = (select auth.uid()))
)
```

**Since migration 005**, every table above also carries one additional policy, `auth_admin_cascade_delete` (`for delete to supabase_auth_admin using (true)`), and `threads` carries `auth_admin_cascade_message_count` (`for update ... using (true) with check (true)`) for the one side-effect trigger (`sync_thread_message_count`) that fires during that cascade. These are scoped to exactly one role and one operation each — they do not weaken what `authenticated` can do, since permissive RLS policies are OR'd together, never AND'd.

`admin.*` has **no RLS at all** — by design, since it's unreachable via PostgREST regardless (§2). Access there is controlled entirely by grants (§4/§6), not policies.

## 6. Hardcoded values — deliberate vs. not

Two different things get called "hardcoded" here, and they need different verdicts.

### Deliberate — a closed set of values, enforced in two places on purpose

These are real business rules, not values that should be dynamic. Each is enforced **both** as a CHECK constraint (so the database can never hold something the app doesn't understand) **and** as a matching enum/tuple in code (so the app never even attempts to write something the database would reject). Confirmed identical on both sides, live:

| Value | DB constraint | Code | Values |
|---|---|---|---|
| Conversation style | `profiles_support_style_known`, `threads_conversation_style_known` | `mani.models.rows.SupportStyle` | `supportive`, `reflective`, `direct` |
| Response shape | `response_styles_shape_known` | `SHAPES` in `mani/llm/schema.py` | 6 values (warmth lead, honor and follow, mirror and ask, mirror and hold, gentle follow, presence only) |
| Mirroring voice | `response_styles_voice_known` | `VOICES` in `mani/llm/schema.py` | naming, receiving, quoting, transitional, observing |

If either side of one of these pairs is ever changed, the other must change with it, or the database will reject values the app tries to write, or the app will silently drop values it should have accepted. There is no single source of truth to point at automatically — this is worth a comment at each site cross-referencing the other, if it doesn't already have one.

### Not hardcoded, and arguably should be — genuine gaps

- **`admin.exercises.category` and `.type`** — free text, no CHECK constraint, and currently zero rows exist to even reveal what values are actually in use. If a fixed set of categories is intended (matching the pattern above), it isn't enforced anywhere yet.
- ~~`admin.llm_calls.purpose`~~ — **resolved, migration 006.** Was free text; is now `admin.llm_call_purpose`, matching `outcome`'s discipline exactly. No Python change was needed — `mani/db/llm_calls.py::record()` already passed `purpose.value` the same way it already passed `outcome.value` into the pre-existing enum column.
- **`profiles.age_bracket`** — free text, sitting directly next to `support_style`, which is properly constrained. If this is meant to gate anything (content, framing), it currently can't be relied on to hold only expected values.

### Written but never read — not a hardcoding problem, but adjacent

`admin.frameworks.body` and `.activation_conditions` are written by `scripts/seed.py` on every seed run and read by nothing (`mani/chat/router.py` reads the `activation` jsonb column instead, per migration 002's own comment). Not incorrect, just a standing cost — every seed writes text nothing will ever load.

## How to regenerate this document

Every table above came from a live query, not the migration source. To re-verify or
refresh after a schema change:

```sql
-- Tables
select n.nspname, c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in ('public','admin') and c.relkind='r' order by n.nspname, c.oid;

-- Columns, in order, with type/nullability/default
select n.nspname, c.relname, a.attnum, a.attname,
       pg_catalog.format_type(a.atttypid, a.atttypmod),
       a.attnotnull, pg_get_expr(ad.adbin, ad.adrelid)
  from pg_attribute a
  join pg_class c on c.oid = a.attrelid
  join pg_namespace n on n.oid = c.relnamespace
  left join pg_attrdef ad on ad.adrelid = a.attrelid and ad.adnum = a.attnum
 where n.nspname in ('public','admin') and c.relkind='r' and a.attnum > 0 and not a.attisdropped
 order by n.nspname, c.oid, a.attnum;

-- Constraints (CHECK, FK, PK, UNIQUE)
select n.nspname, c.relname, con.conname, pg_get_constraintdef(con.oid)
  from pg_constraint con
  join pg_class c on c.oid = con.conrelid
  join pg_namespace n on n.oid = c.relnamespace
 where n.nspname in ('public','admin');

-- RLS policies
select schemaname, tablename, policyname, cmd, roles, qual, with_check from pg_policies;

-- Table + column grants
select table_schema, table_name, grantee, privilege_type
  from information_schema.role_table_grants where table_schema in ('public','admin');
select table_schema, table_name, grantee, privilege_type, column_name
  from information_schema.column_privileges where table_schema in ('public','admin');

-- Roles and membership
select rolname, rolsuper, rolinherit, rolcreaterole, rolcanlogin, rolbypassrls from pg_roles;
select r.rolname, m.roleid::regrole from pg_auth_members m join pg_roles r on r.oid=m.member;
```
