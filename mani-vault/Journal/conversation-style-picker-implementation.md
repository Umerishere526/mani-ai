---
type: journal
date: 2026-09-16
apps: [mobile]
tags: [journal, mobile, chat, chat-cadence]
---

# Building the Directive/Supportive/Reflective style picker

See [[conversation-style-selection]] for the feature spec (scope, done-means). This note is the narrative: what was asked, what was decided, and why.

## What was asked

muhammad described MANI's full conversational cadence:

```
Greeting
→ User selects Directive, Supportive, or Reflective
→ Style-specific opening question
→ User states the issue
→ Approximately 2–4 exchanges to understand the issue
→ Ask, check, and confirm rather than label or assume
→ Offer the appropriate structured framework
→ Ask permission to begin
→ Framework becomes the deeper conversation
→ Framework completes
→ Somatic check-in
→ Chat More OR Go to Library
```

And the conversational-behavior distinction behind the three styles (not just tone, but what MANI is *doing*):

- **Directive** — leads the user toward clarity, action, problem-solving, a next step.
- **Reflective** — reflects meaning/emotions/details back so the user feels understood and can examine their experience more deeply.
- **Supportive** — acknowledges and validates while offering warmth, encouragement, gentle forward momentum.

Only the first three steps of the cadence (greeting → style pick → opening question) were in scope for this pass — everything from "user states the issue" onward is unbuilt. A wireframe was supplied showing a dark card with "Hi (NickName) It's Mani" / "How would you like me to speak with you today?" and three bordered option boxes (Directive, Supportive, Reflective), each with a description line, plus a screenshot of the current empty `chat.tsx` (hamburger + Get Help Now header, empty body, message input bar).

## Decisions made before writing code

Three things weren't determined by the existing code, so I asked rather than guessed:

1. **Where does the selected style live?** Chose to put it inside `useChatSimulation` (not local `chat.tsx` state), because the hook is what builds messages (`createMessage`/`buildReply` already live there), and the style-specific opening question is itself a message MANI sends. Keeping message-construction logic in one place means `chat.tsx` never has to know how a greeting is built — same shape as how it already doesn't know how replies are built.

2. **Visual style of the option cards.** The wireframe showed plain white-outlined rectangular cards on a dark background. The app already has `SmartPromptChip` — a pill-shaped, spring-press card with a bold title + description — used for the smart-prompt suggestions under MANI's replies. muhammad chose to reuse the pill pattern for visual consistency with the rest of chat rather than match the wireframe literally. (muhammad later refined this further — see below.)

3. **Does the style need to persist?** Chose in-memory only, reset on `startNewThread`, matching how `messages`/`crisisDetected` already reset there. No AsyncStorage, no provider, no backend field. Reasoning: nothing else in this app persists across app restarts yet (`useChatSimulation` is a fully local stand-in, no `@mani/api`), so adding persistence for just this one field would be scope creep ahead of the actual backend integration. If a real thread history / backend arrives later, this is the natural point to revisit — noted as an open question in the feature spec rather than solved speculatively (YAGNI).

## Implementation

- `types/chat.ts` — added `ConversationStyle = 'directive' | 'supportive' | 'reflective'`. No existing type for this.
- `dictionaries/en.json` — added a `chat.styles.<style>.{label,description,opening}` block, following the existing nested-group pattern already used for `chat.dateGroups`. All three opening lines are muhammad's exact wording. This is the only dictionary file in the app (no i18n framework, no other language files) — so "every language file gets updated together" per the golden rules is trivially satisfied here.
- `hooks/useChatSimulation.ts` — added `conversationStyle` state and `selectConversationStyle(style)`. This hook is already right at the 80-line hook cap (77 lines before this change), so I didn't want to inline a lookup switch/if-chain for the three opening lines directly in the hook. Extracted `lib/utils/get-conversation-style-opening.ts` (9 lines) that just reads `en.chat.styles[style].opening` — keeps the hook's own function body at 51 lines, well inside budget, and follows Golden Rule 4 (reusable lookup logic goes in `lib/utils/`, not inlined in a hook).
- `components/chat/conversation-style-option.tsx` + `conversation-style-picker.tsx` — new files, following the barrel/kebab-case-file/PascalCase-export convention already established in `components/chat/`. `ConversationStyleOption` was modeled directly on `smart-prompt-chip.tsx`'s structure (same `useSharedValue`/`withSpring` press-scale pattern, same `SPRING_CONFIG` shape) rather than invented fresh, per Golden Rule 4 ("search for an existing implementation first").
- `components/chat/chat-conversation.tsx` — `app/chat.tsx` was at 107 lines before this feature, already at the "start extracting past 100 lines" threshold from the golden rules, and adding a picker/conversation branch would have pushed it well past 100. Extracted the FlatList + input/crisis-banner area (everything shown once a style is picked) into `ChatConversation`, leaving `chat.tsx` as a thin switch between `ConversationStylePicker` and `ChatConversation`. This wasn't asked for directly — it fell out of the 150-line component rule — but is the same kind of decomposition call as the `AuthScreenShell` extraction and the `ChangeEmailScreen` split noted in [[mani-mobile-ui-port]].

## Correction: option card styling, post-implementation

After the first pass shipped (flat `bg-primary-400` pill, matching `SmartPromptChip` exactly), muhammad edited `conversation-style-option.tsx` directly: swapped the flat background for the existing `CardGradient` shared component (an absolute-fill `LinearGradient` from `colors.primary[600]` to `colors.primary[800]`, already used behind home/category cards) and added `overflow-hidden` to the `Pressable` so the gradient clips to the `rounded-3xl` corners. Reviewed the diff — `CardGradient` self-positions via `StyleSheet.absoluteFill`, so it correctly layers behind the `View` holding the label/description text with no z-index issues; the edit is consistent with how `CardGradient` is used elsewhere and needed `overflow-hidden` specifically because `LinearGradient`'s `absoluteFill` would otherwise bleed past the parent's rounded corners. No changes needed on my end — this was muhammad tightening the visual language to match other cards in the app, not a functional change.

## Not verified

**No simulator is available in this dev environment** (`xcrun simctl list devices` returns nothing booted or installed, `expo` isn't globally installed either — only reachable via `npx`/local devDependency). `tsc --noEmit` and `npm run lint` both pass clean, but the actual rendered picker — spacing, gradient card legibility against `bg-primary-900`, whether the spring-press animation feels right — has not been visually confirmed. Same standing limitation already noted repeatedly in [[mani-mobile-ui-port]] for this environment. muhammad needs to run `npx expo start` and check a real simulator before treating the visual result as settled, especially since the wireframe's dark-card-on-dark-background contrast was explicitly part of the ask.

## Applies to

Any future work continuing the conversation cadence (the 2-4 exchange phase, framework offer/permission, somatic check-in, chat-more/library branch) will need to decide how those phases key off `conversationStyle` — right now nothing downstream of the opening question reads it at all; `buildReply` in `useChatSimulation` is still one canned response regardless of style. That's the next real decision point, not yet made.

## Links

- [[conversation-style-selection]] — feature spec
- [[mani-mobile-ui-port]] — the broader mobile UI port this chat screen originally came from; same environment limitations (no simulator) and same decomposition instincts (extract before hitting the line cap) apply here
- [[nativewind-v5-active-state-on-nested-view]] — a real bug found while extending the same `CardGradient`-on-Pressable pattern to `ChatDrawerNavSection`'s active-state highlight; `active:` on a nested child breaks the parent Pressable's `onPress` entirely, fixed with `group`/`group-active`
