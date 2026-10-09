---
id: 10000000-0000-0000-0000-000000000016
name: tuning
description: The numbers that shape a conversation, covering offer timing, windows and memory limits. Never sent to a model.
---

offers:
  # An offer may come from the person's second message, in any style: it was four rounds for
  # Supportive and Reflective until Mani's own judgement was made the signal (muhammad,
  # 2026-10-01). Counted in the person's own messages.
  clear_offer_after: 2
  # After "I want to keep talking" an offer may come back after two more exchanges (counted in messages).
  clear_cooldown_after_decline: 4
  cooldown_after_complete: 45
  # The style used when neither the conversation nor the profile has chosen one yet. The
  # conversation's own style, set per thread, wins over the profile's onboarding answer.
  default_style: supportive
windows:
  # Messages of history the model sees. It is also how many new messages accumulate before the
  # rolling summary refreshes: any larger number leaves messages that have scrolled out of the
  # history the model sees and are not yet in the summary either.
  context_window: 20
  # How many recent reply shapes the model is shown, to keep it from repeating itself.
  style_window: 7
  # How many of a reply's own leading words count as its opener for repetition purposes, and
  # how many of Mani's own past replies to surface. Small on purpose: a nudge against an
  # immediate repeat, not a transcript.
  recent_openers_words: 2
  recent_openers_window: 3
  # A title is asked for once the thread has this many messages and none yet. Tested as "at
  # least", because a single crisis turn writes one message, not two.
  title_after_messages: 3
  # The model ends a framework's ending by setting `ending`. If it never does, the framework is
  # retired once the person has sent this many messages since the ending began, so it cannot
  # hold the thread, and block every new offer, for good.
  ending_turn_cap: 12
memory:
  # The memory is pasted into the system prompt of every later chat, so it is bounded whatever
  # the model returns: a runaway list is a cost multiplier and an injection channel.
  max_entries: 6
  max_entry_chars: 160
  # How long a conversation has to be quiet before the idle job treats it as finished.
  idle_after_hours: 24
