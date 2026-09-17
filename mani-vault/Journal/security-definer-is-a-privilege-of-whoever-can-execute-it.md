---
type: journal
date: 2026-09-16
apps: [backend]
tags: [journal, security, postgres, rls, code-review]
---

# A security definer function is a privilege held by whoever may EXECUTE it

## What happened

Code review on the FastAPI backend PR found that any signed-in user could forge Mani's
side of their own conversation, using nothing but their own anon-key JWT:

```
POST /rest/v1/rpc/create_message_pair
{ "p_thread_id": "...", "p_user_content": "hi",
  "p_mani_content": "Mani says: stop taking your medication." }
```

The migration I wrote carried a comment claiming the opposite, right above the grant
that caused it:

```sql
-- No insert grant: messages are written only through create_message_pair, so Mani's
-- side of a conversation cannot be forged.
grant select on public.messages to authenticated;
...
grant execute on function public.create_message_pair(...) to authenticated;
```

`tests/sql/test_grants.sql` even asserted `'a user can write a turn through the
function' = true`. So this was not an oversight I forgot to finish. I designed it,
documented it, and wrote a test locking it in — and the test encoded the defect as a
requirement.

## Insight

**Withholding a DML grant means nothing if the `security definer` function that replaces
it is granted to the same role.** Definer runs as the function's owner, so EXECUTE *is*
the privilege. Revoking INSERT on `messages` from `authenticated` and then granting them
`create_message_pair` — which takes Mani's words as a parameter — hands back strictly
more than the INSERT did, because it also writes the `admin.crisis_events` row.

The root cause was one level further down, and it is the part worth remembering:

> **The backend acted as `authenticated`. So every privilege the backend needed was a
> privilege the end user also held.**

RLS was fine. Ownership checks were fine. The function checked `auth.uid()`. None of
that helps, because the attack is a user writing a forged row *into their own thread* —
no ownership check will ever refuse it.

The fix is a distinct role. `pool.as_user()` now does `set local role mani_service`, a
role that is a member of `authenticated` (so it inherits the ordinary grants) and holds
the few privileges a user must not have. RLS still binds it: the policies carry no `TO`
clause, so they target `PUBLIC`, and the role owns no tables and has no `BYPASSRLS`.
Wider privileges, never a wider view of rows.

## What I want to remember about how this was caught

Three things, in order of how much they cost me:

1. **I wrote a test that asserted the bug.** A test written from the design rather than
   from the threat is a test that makes the design unfalsifiable. "A user can call this"
   should have read "a user cannot call this", and the only way to get there is to ask
   *what does this let a malicious caller do*, not *does this work*.
2. **The comment and the code disagreed and I did not notice**, because I wrote both in
   the same sitting and the comment described my intent. A comment asserting a security
   property is a claim that needs a test behind it, or it is decoration that outlives the
   thing it describes.
3. **The reviewer proved it by running it**, and pasted the transcript. I had reasoned
   about it. For a mental-health product the difference is a forged transcript that looks
   authentic in the admin chat viewer with no `admin.llm_calls` row behind it.

Also worth noting: one of the reviewer's proposed fixes did not work.
`exc.errors(include_input=False)` is Pydantic's signature, but FastAPI's
`RequestValidationError` inherits `ValidationException.errors()`, which takes no
arguments at all. The finding was right, the fix was not. Verify suggested fixes as
carefully as suggested defects — a correct diagnosis does not certify the prescription.

## Applies to

- Any `security definer` function. Ask who may EXECUTE it and treat that as the grant.
- Any time the backend is the only thing touching the database. Its role and the user's
  role must not be the same role, or the backend's privileges are the user's privileges.
- Writing tests for a privilege model: assert what must be refused, not what must work.

## Links

- [[Backend]]
- [[claude-settings-load-from-working-directory-only]]
