---
type: feature
status: in progress
date: 2026-09-16
apps: [mobile]
tags: [feature, mobile, chat]
---

# Conversation style selection (Directive / Supportive / Reflective)

**Status:** in progress — greeting/style-pick/opening-question stage shipped; the framework, somatic check-in, and chat-more/library handoff stages are not built yet.
**Affects:** mobile

## Problem

MANI's chat previously opened straight into an empty message list with no way to set the conversational tone. muhammad specified a fixed conversational cadence (see below) where the first thing that has to happen, before any framework or exchange logic, is the user choosing how MANI should relate to them for that thread.

## Scope

In scope (this pass):
- A style picker screen shown when a chat thread has no style chosen yet.
- Three styles: Directive, Supportive, Reflective — each with a label, one-line description, and a style-specific opening question MANI asks once picked.
- Style resets to unset whenever a new thread starts.

Out of scope (explicitly, and not yet built):
- The rest of the conversation cadence: the 2-4 exchange clarification phase, "ask/check/confirm" framing, offering a structured framework + permission-to-begin, the framework conversation itself, the somatic check-in, and the Chat More / Go to Library branch at the end.
- Persisting the chosen style anywhere (backend, AsyncStorage, per-thread history). It is in-memory only for the current hook instance — see [[conversation-style-picker-implementation]] for why.
- Any backend involvement — `useChatSimulation` is still a fully local stand-in, no network calls.

## Approach

- `backend/` — untouched. No API for this yet.
- `web/` — untouched. This is a mobile-only screen today.
- `mobile/` —
  - `types/chat.ts` gained `ConversationStyle = 'directive' | 'supportive' | 'reflective'`.
  - `dictionaries/en.json` gained `chat.styleGreeting`, `chat.stylePrompt`, `chat.styleOptionsLabel`, and `chat.styles.{directive,supportive,reflective}.{label,description,opening}` — the three opening lines are exactly what muhammad specified:
    - Directive → "How can I help you today?"
    - Supportive → "How can I support you today?"
    - Reflective → "What's on your mind today?"
  - `hooks/useChatSimulation.ts` gained `conversationStyle` state (`ConversationStyle | null`) and `selectConversationStyle(style)`, which sets the style and pushes the style's opening question as the first `mani` message. `startNewThread` resets it back to `null`.
  - New components in `components/chat/`: `ConversationStylePicker` (the greeting + three option cards) and `ConversationStyleOption` (one card, styled like the existing `SmartPromptChip` pill pattern rather than the wireframe's rectangular outlined cards — muhammad's call, for visual consistency with the rest of chat). muhammad later swapped the option card's flat background for the existing `CardGradient` shared component plus `overflow-hidden` on the `Pressable`, matching how gradient cards look elsewhere (home/category cards).
  - `app/chat.tsx` was starting to bump the 100-line extraction threshold, so the message-list-plus-input area was pulled out into `components/chat/chat-conversation.tsx` (`ChatConversation`) at the same time. `chat.tsx` is now a thin switch: render `ConversationStylePicker` when `conversationStyle === null`, else `ChatConversation`.

Full implementation narrative and the reasoning behind each decision: [[conversation-style-picker-implementation]].

## Data

No database or endpoint involved — this is UI-only local state, matching how the rest of `useChatSimulation` has no backend yet.

## Open questions

- [ ] When the real conversational-framework logic gets built, does `conversationStyle` need to move out of `useChatSimulation` and into something that survives across the 2-4 exchange / framework / check-in stages, or does one hook instance already span all of that for a given thread? Not decided — no framework logic exists yet to answer it against.
- [ ] Does style ever need to persist per-thread (e.g. shown in the header, restored when reopening an old thread from history)? Explicitly deferred — see [[conversation-style-picker-implementation]] for why in-memory-only was chosen for now.

## Done means

- [x] Opening a fresh chat thread (no style chosen) shows the three-option picker, not an empty message list.
- [x] Picking a style sets that style and immediately shows MANI's style-specific opening question as the first message.
- [x] Starting a new thread (`startNewThread`) resets the picker to be shown again.
- [x] `tsc --noEmit` and `npm run lint` both clean in `mobile/`.
- [ ] Visually verified in a real simulator — **not done**, no iOS/Android simulator is available in the dev environment this was built in. muhammad needs to eyeball it in Expo before trusting the visual result.
