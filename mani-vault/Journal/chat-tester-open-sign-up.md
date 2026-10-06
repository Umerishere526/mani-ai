---
type: journal
date: 2026-10-05
apps: [chat-tester]
tags: [journal, chat-tester, auth]
---

# chat-tester: open sign-up, chosen with the risk known

## What happened

`09f9bd6` (2026-09-25) removed chat-tester's sign-in screen and signed everyone in as one fixed
account, so a public link could not create accounts on the hosted project. On 2026-10-05
muhammad asked for login and sign-up back, so that each person has their own chats and threads.
Asked how sign-up should be gated (invite code, open, or sign-in only), muhammad chose **open**
and removed the fixed user.

## What to remember

- Per-user isolation needed no work: the backend takes the user from the verified JWT and RLS
  scopes threads to it. A different Supabase account is all "own chats" means.
- Sign-up uses the Admin API (`client.sign_up`) with the service role key, so anyone who can reach
  the page can create confirmed accounts and spend OpenRouter credit. That is the accepted risk.
- The name-based quick user (`sign_in(name)`, one shared password) was deleted, not restored:
  anyone typing a name got that account.
- If abuse shows up, the smallest fix is an invite code: sign-up requires a value matching
  `CHAT_TESTER_SIGNUP_CODE`, and the tab is hidden when the variable is unset.
- Streamlit session state is per tab, so a refresh signs out. A cookie-held refresh token would fix
  that if it becomes annoying.

## Noticed, not fixed

- `app.py`'s composer uses `st.components.v1.html`. Streamlit 1.64 warns on every run that it was
  due for removal after 2026-06-01 and should become `st.iframe`.
- The README and root `CLAUDE.md` say `source venv/bin/activate`, but the env on disk is
  `chat-tester/.venv`.
