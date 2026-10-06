# Scope epic: Production readiness

Keeping Mani up, affordable and observable once real people use it. The evidence is in the backend audit from October 2026. Back to [the index](index.md).

## Slice 7: Ready for a limited beta

### 12. Mani stays up when many people chat · needs a decision

A chat turn holds a database connection open through every model call, up to several minutes. With about ten turns at once the connections run out and Mani freezes for everyone, and the health check cannot see it. The reply is also sent before it is saved, and two messages in the same chat at once can overwrite each other.
**Done when:** a load test of at least 20 chats at once completes without a freeze, a reply is only shown once it is saved, two messages in one chat at once both land correctly, and the health check fails when the database cannot be reached.

- [ ] Design it (spec): `/architect Mani stays up when many people chat`

### 15. Usage and request limits · needs a decision

The daily message limit is off by default and can be raced past, one message can cost up to seven model calls, voice messages and summaries have no limit, and request size is unlimited even before sign in. Production settings that should be required are not checked at startup.
**Done when:** each person has a usage budget that holds under parallel requests and covers voice, oversized requests are refused before they are read, and the app refuses to start in production without its required settings.

- [ ] Design it (spec): `/architect usage and request limits`

### 16. Monitoring and alerts · needs a decision

Logs are plain text with no request id, there are no metrics, and nothing alerts anyone on a crisis, an error spike or a freeze.
**Done when:** every request can be traced by an id, turn time and error rates are measured, and a named person is alerted on a crisis record, a rise in errors, or the app not answering.

- [ ] Design it (spec): `/architect monitoring and alerts`

## Slice 9: Robust for open launch

### 23. Backup AI provider and no lost messages · needs a decision

One AI provider with no fallback, so its outage is Mani's outage, and the person's typed message is lost when the model fails. A failed second attempt also throws away a usable first reply.
**Done when:** an outage of the main provider still produces a reply (from a second provider or a fixed safe reply), the person's message is always saved, and a usable first reply is kept when a retry fails.

- [ ] Design it (spec): `/architect backup AI provider and no lost messages`

### 26. Automatic checks on every change · needs a decision

About 800 tests exist but nothing runs them automatically, and the tests that would have caught the freeze, the admin permission checks over the network, and real AI failures are missing or skipped.
**Done when:** every change runs the full test suite and the database tests, a load test and AI failure tests run on a schedule, and the admin permission tests run instead of skipping.

- [ ] Design it (spec): `/architect automatic checks on every change`

## Deferred

Out of scope for this build pass, kept so the plan stays honest.

- **Reliable background jobs**: summaries and memory folds survive a restart and run on a schedule · needs a decision
- **Data retention**: a written policy for how long conversations and records are kept, and a scheduled clean up · needs a decision (legal input)
- **Real model checks on a schedule**: run the scripted conversations against the real model regularly and score the client's rules · needs a decision
- **Prompt changes reach every server**: a change in the admin portal takes effect everywhere at once
- **One error shape everywhere**: every failure returns the same error format, and a sign in key outage is not reported as an expired session
- **Docs match the app**: correct the twelve places where the backend docs disagree with the code
- **Remove unused code and settings**
- **Smaller security fixes**: check the token issuer, compare the cron secret safely, hide the API docs in production, validate admin audio paths, ask for sign in again before account deletion
- **Repeatable builds**: pin the base image and every dependency, run migrations in the deploy
- **Split the chat turn code** into smaller parts once rows 12 and 22 land
