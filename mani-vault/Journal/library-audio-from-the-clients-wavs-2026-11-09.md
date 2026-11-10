2026-11-09

# Library audio from the client's WAVs

Lolly said the Library still played AI voices and showed the old descriptions. What was actually true:

- GitHub `main` held 12 AI recordings. Correlated against her WAVs they scored 0.01, so they were different audio.
- The unpushed `feat/library-sections-safety-and-test-isolation` already had all 30 of her recordings, and the Pro project (`mani-app`) was seeded from it on 2026-11-08. They had been squashed to 64 kbps mono, which threw away the stereo music beds (the side channel sits about 15 dB under the mid, so it is real content).
- The local dev DB still had 5 active rows (the "Start here" pieces, Monkey Anchor, The Sorting Table) that `main` dropped from the manifest and never switched off. The seed now sets every unlisted row inactive.

Checking an MP3 against its source: LAME adds about 1,105 samples of delay at the start. A lag search that is too short, or a comparison resampled to a rate where the delay lands on a fraction of a sample (48 kHz down to 16 kHz), reads 0.95–0.97 for a good encode. Compare at the file's native rate with a lag search of about 2,048 samples; all 30 then scored 0.996 to 0.9997.

Supabase Storage's CDN can keep serving an overwritten path, so a replaced recording goes to a new filename and the seed deletes the old one.

- Rebasing `feat/capacity-resilience` onto `fix/library-client-audio`: drop `daec98a` and `c564235` (its 64k library). With those two left out, everything else replays cleanly (simulated 2026-11-09). Keeping them brings the MP3s back; see [[transaction-pooler-and-busy-pool-fixes-2026-11-09]] for the rebase that resurrected deleted content.
- Decision: `backend/PORT-STATUS.md`, "The exercise audio lives only in the `exercises` bucket".
