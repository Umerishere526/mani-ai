-- ABOUTME: Adds the purpose of the call that reads what a chat message adds to Mani's picture of the person,
-- ABOUTME: made after the reply is sent (orchestrator.read_understanding), so its cost and time are kept apart.

alter type admin.llm_call_purpose add value if not exists 'understanding';
