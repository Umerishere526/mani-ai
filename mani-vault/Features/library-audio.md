---
type: feature
status: shipped
date: 2026-10-02
apps: [backend, chat-tester]
tags: [feature, library, exercises, audio, somatic]
---

# Library audio

**Status:** shipped (local)
**Affects:** backend, chat-tester

## Problem

The client checks Mani's work in the Streamlit chat-tester. Today a finished framework ends on
Chat More and Go to Library, and neither leads anywhere: tapping Go to Library just sends that label
as a chat message, and no exercise is ever offered. The backend side is already built
(`admin.exercises`, signed URLs for an `exercises` bucket, `/v1/exercises`, admin CRUD, and the
`StartExercise` tool call when a framework retires). It does nothing because no bucket exists, the
catalog has no rows, and the tester has no library page. See [[what-every-conversation-is-for]].

The goal is the mani-app flow, testable in Streamlit: framework, then somatic, then one exercise
fitted to the conversation, then Go to Library, where the person can see every exercise and play
any of them.

## Scope

In scope:
- The 18 audio exercises from mani-app's `library_audio/` (3 home, plus 3 each for Anxiety,
  Boundaries, BuildingHabits, Burnout and EmotionalIntelligence), compressed and committed.
- A seed script that creates the private `exercises` bucket, uploads the audio and upserts the
  catalog rows.
- `GET /v1/exercises` returns the full catalog, and `audio_path` no longer appears in responses.
- After somatic, one exercise chosen from the whole catalog using the conversation as context.
- A flat library page in the chat-tester, opened from Go to Library or from the sidebar.

Out of scope (explicitly):
- Somatic stages, `content/prompts/somatic.md`, and the Chat More / Go to Library button logic in
  the orchestrator. A colleague owns this work; we only consume the retiring turn.
- Completions tracking. The `/v1/exercises/completions` routes stay but nothing calls them.
- Keeping the exercise card after a reload (`MessageOut` carries no exercise).
- Admin audio upload, mobile and web screens, and NarcissisticDynamics (no audio exists for it).

## Approach

### Content and compression (one-off)
- Copy mani-app's `library_audio/exercises.json` into `backend/content/exercises/exercises.json`,
  keeping its fixed UUIDs, titles, subtitles, descriptions, types, categories and display order.
- Re-encode each MP3 with ffmpeg (`brew install ffmpeg`) to **64 kbps mono MP3**. Save it at
  `backend/content/exercises/<filename>`, where `<filename>` is the manifest's flat storage name
  (e.g. `anxiety-bee-breathing.mp3`).
- **Listen test first.** Convert one file and leave it beside its original. muhammad listens and
  approves before the other 17 are converted. The originals are never committed.
- The same pass writes `durationMinutes` (decimal minutes, 2 places, from ffprobe) into the
  manifest, so the seed script needs neither ffmpeg nor a new Python dependency.
- Home items get `category: "home"`, which is already a `LibrarySection` value. That satisfies the
  NOT NULL column without a migration.

Measured sizes: 131 MB across 18 files, the largest 21 MB. Supabase Free allows 50 MB per file and
1 GB in total, so compression is for streaming speed and repo size, not to fit a limit.

### Seed script: `backend/scripts/seed_exercises.py`
- Reads the manifest and validates it with a Pydantic model. It is never read at runtime, like
  `content/frameworks`.
- Ensures the bucket `storage.BUCKET` (`"exercises"`, private) exists through the Storage REST API
  with the service-role key from settings. It creates the bucket if missing and leaves it alone if
  present.
- Uploads each file to `exercises/<filename>` with upsert, so re-runs are idempotent.
- Upserts `admin.exercises` by id on an admin connection. `audio_path` is set to the filename.
- It is not a migration, because `scripts/test_db.sh` applies migrations to plain Postgres, which
  has no `storage` schema. It runs the same way against local and hosted projects.
- It is run after `scripts/seed.py`. Add it to the BACKEND.md command list.

### API: `mani/db/exercises.py`, `mani/routers/exercises.py`, `mani/models/api.py`
- `list_active`: the home-screen filter becomes optional (`home_screen: bool | None = None`, where
  None means all). `GET /v1/exercises` returns every active exercise ordered by category, then
  `display_order`, then title. `GET /home` keeps passing `True`. `?category=` is unchanged.
- `ExerciseOut` drops `audio_path`, so clients get only the signed `audio_url`, as the router's
  header already promises.

### Choosing the exercise: `mani/chat/orchestrator.py` `_offer_exercise`, `mani/llm/client.py` `choose_exercise`
- Candidates are all active exercises, with exercises linked to the finished framework
  (`list_for_framework`) listed first. Each candidate line carries id, title, type, category and
  subtitle.
- The pick is given the framework name, the thread's `current_issue` from its summary when there is
  one, and the person's last 3 messages from the turn's already-loaded history. No new query is
  needed for those.
- Unchanged: the call runs only on the turn a framework retires, it stays one small tool call
  (`StartExercise`, `max_tokens=200`), an unknown id falls back to the first candidate, and an
  empty catalog means no call.
- The `choose_exercise` docstring ("never the whole catalog") is updated to describe the new
  behaviour.

### Chat-tester: `chat-tester/library.py` (new), `chat-tester/app.py`, `chat-tester/client.py`
- `client.list_exercises()` calls `GET /v1/exercises` with the bearer token, using the same
  request helper as the other calls.
- `library.py` has `render_library()`, a single flat page:
  - "Start here" (the home items), then one heading per category;
  - each item shows title, `type · m:ss`, subtitle or description, and `st.audio(audio_url)`;
  - a "← Back to chat" button at the top.
- `app.py` stores the view in `st.session_state` (`chat` or `library`).
  - A tapped button that has a `library` value switches to the library view instead of sending a
    message.
  - A sidebar "Library" button switches to it at any time.
  - The existing "Exercise offered" card is unchanged.
- URLs are fetched each time the library renders, so the one-hour signature expiry never matters
  during testing.

## Data

- No migration, and no schema or RLS change. Rows go into the existing `admin.exercises`
  (grant-based access, `select` for `authenticated`). Audio goes into a new private bucket. Only
  the backend's service role signs URLs, so no `storage.objects` policy is needed for users.
- Endpoint behaviour changes:
  - `GET /v1/exercises` now includes home items;
  - `ExerciseOut` loses `audio_path`.
  - No frontend uses these yet; the chat-tester is the first consumer.
- Each retiring turn makes one extra `exercise_select` call with a larger prompt (18 candidates
  plus 3 messages, an estimated few hundred tokens). This is the same exception
  [[ADR-002-one-model-call-per-chat-turn]] already allows.

## Open questions

- [x] The listen test: muhammad approved 64 kbps mono (2026-10-02). 131 MB → 59 MB.
- [ ] Hosted project: the seed script works against it, but no hosted project exists yet
  (PORT-STATUS).

## Done means

- [ ] `backend/content/exercises/` holds `exercises.json` and 18 compressed MP3s, each well under
  50 MB. muhammad approved the listen test.
- [ ] After `python scripts/seed_exercises.py`, Studio (http://127.0.0.1:54343) shows 18 objects in
  the `exercises` bucket and 18 rows in `admin.exercises`. Re-running changes nothing.
- [ ] `GET /v1/exercises` returns all 18 with a working `audio_url` and no `audio_path`.
- [ ] A finished framework in the chat-tester ends with an exercise card that plays and fits the
  conversation, plus one `exercise_select` row in `admin.llm_calls`.
- [ ] Go to Library and the sidebar Library button both open the flat page. All 18 play, and Back
  returns to the same thread.
- [ ] `pytest`: new tests pass, the output is pristine, and the integration tests ran rather than
  skipped. Tests use fakes built from the real interfaces:
  - the full-catalog listing;
  - that `audio_path` is absent from `ExerciseOut`;
  - candidate ordering and the conversation context passed to `choose_exercise`;
  - the retiring turn offering a catalog exercise with a scripted model;
  - manifest validation in the seed script.
- [ ] `PORT-STATUS.md` updated: the catalog is no longer empty, the bucket exists, and the
  "Audio upload" open item is closed.
