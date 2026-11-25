-- ABOUTME: Adds the reply check to the purposes a model call is recorded under: a second, short call that rewrites
-- ABOUTME: readings said as fact and figures of speech in Mani's reply before it is sent (muhammad, 2026-11-25).

alter type admin.llm_call_purpose add value if not exists 'reply_check';
