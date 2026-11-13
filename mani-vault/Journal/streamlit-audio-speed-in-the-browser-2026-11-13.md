---
type: journal
date: 2026-11-13
apps: [chat-tester]
tags: [journal, streamlit, audio, supabase-storage]
---

# Exercise audio speed lives in the browser

2026-11-13. Checked in the installed Streamlit 1.64.0 and in headless Chrome against local Supabase Storage.

- `st.audio` has no playback-speed parameter in 1.64 and renders a bare `<audio controls>`. Whether the browser's own ⋮ menu offers speed for audio was not confirmed on any browser, Safari included.
- `st.components.v1.html` and `.iframe` are deprecated in 1.64 in favour of `st.iframe`. `st.html(..., unsafe_allow_javascript=True)` runs in the page itself, not an iframe, and keeps `<audio controls preload>`, `<select>` and `<option selected>` through its sanitizer.
- Many players on one page: one delegated `change` listener behind a `window` flag, as `copy_button.py` does. A script per player that declares a top-level `const` fails on the second player ("Identifier has already been declared"). A test that dispatches `change` by hand must pass `{ bubbles: true }`, or the delegated listener never sees it.
- Every exercise gets this player, so the library looks the same throughout; only stories (`type` "Story") get its speed menu (`audio_player(url, speed_choice=...)`), which is where muhammad wants the speed feature.- The library's own player (seek bar, skips, play, mute, time, speed) is plain HTML in `st.html`. The sanitizer keeps `<input type=range>`, `<button data-*>` and `<style>`, but it strips inline SVG. So the icons are SVG data URIs painted through a CSS `mask` in `currentColor`, which follows the theme. Media events (`timeupdate`, `play`, `loadedmetadata`) do not bubble, so one document listener catches them in the capture phase. The CSS and JS live in `audio_player.css` and `audio_player.js`, and Python reads them once at import. A link that fails to load (bad token, past its hour) dims the controls and says "Audio unavailable right now. Reload the page." Otherwise it would look like a working player that ignores taps.
- Checked in headless Chrome: 12 signed links plus one bad one on one page, with real mouse clicks (`Input.dispatchMouseEvent`) on Play and the seek bar, in the light and dark themes. Every card showed its total time. The scripts are in the session scratchpad, not the repo.
- Signing the same Storage path twice gives two different links. `library.py` fetches and signs on every rerun, so any rerun of the library page swaps every player's `src` and stops playback. Only a button tap reruns that page today, and a speed change is not one. With an identical link, a rerun kept the audio playing at its speed.
- A signed link answers `Range: bytes=0-1` with `206 Partial Content`, which seeking and iPhone Safari need. Checked on local Storage only.
- Chat turns carry no exercise since the 2026-10-22 removal ([[somatic-check-in-is-the-clients-script-2026-10-22]]), so a player in the chat would need a turn field and a message column; not built.
- Tested only in headless Chrome on a scratch page with two players and real signed links. Measured inside the page over 4 s, the audio advanced 0.5, 1.5 and 2.0 seconds per second at those speeds, and the other player stayed at 1x. Not tested: Safari, Firefox, a phone, and the real library page with every card against the backend.

## Stale lines found in `backend/PORT-STATUS.md`, not fixed

- "What the service does", Exercises: says a completing framework picks an exercise with one tool call in `mani/llm/tools.py`. That file does not exist, and the lines just above it say the automatic pick was deleted.
- Open engineering, "Admin audio upload": "the exercise card is also not kept on the message". No exercise card exists any more. (Fixed 2026-11-13, with the count below.)
- Status: said `admin.exercises` holds 17 exercises (now 30, see the next section). `content/exercises/` has 12 mp3s and 12 manifest entries. The local database holds 35 exercises (30 active) and the local `exercises` bucket 12 files, so 18 active exercises have no audio locally: `sign` answers 400 for them and the library shows "Audio unavailable right now." under the card. Checked 2026-11-13 from the backend log and `admin.exercises.audio_path`. The same day the 18 were copied from the production bucket ("mani-app", read only) into the local one, with sizes matching; all 30 active exercises now sign locally. The 5 inactive ones (`home-break`, `home-ground`, `home-rest`, `burnout-monkey-anchor-breathing`, `burnout-sorting-table`) have no file in production either.

## The repo's library now mirrors production

- Production ("mani-app") re-recorded the 12 original exercises on 2026-11-09: same ids, new file names (`bee-breathing.mp3`, not `anxiety-bee-breathing.mp3`), new lengths, three new titles. The repo still held the old recordings, so running the old manifest anywhere would have put the old names and files back.
- `exercises.json` holds production's 30 rows. The audio is not in git (muhammad, 2026-11-13: it must not go to GitHub). Local copies of production's 30 files at 64 kbps mono (`ffmpeg -codec:a libmp3lame -b:a 64k -ac 1 -ar 44100`, about 113 MB) sit gitignored in `content/exercises/`, and the seed stops and names any that are missing. Every stated length matches the compressed file. The 12 old recordings are still in `main`'s history, and GitHub has them.
- Vercel builds the backend from the repo root (its log reads `backend/.python-version` and `backend/requirements.txt`), so `backend/.vercelignore` is not applied there, and any committed audio rode in the function bundle. Keeping the audio out of git keeps it out of the bundle too.
- `seed_exercises.py` used to check categories against `LibrarySection`, the chat button's destinations, which the model reads in its reply schema. It now checks against its own `ExerciseCategory`, which has the 8 library categories, so `LibrarySection` and the model's schema are unchanged.
- The seed uploads with `x-upsert: true`. Run against production, it would replace production's 192 kbps stereo files with the 64 kbps copies. Production was only read from.
- After seeding locally, all 30 production rows are identical in the local database, and all 30 sign. Local still holds 5 inactive rows production does not have (`home-*`, two `burnout-*`), and 12 old-named files in its bucket that no row uses.
