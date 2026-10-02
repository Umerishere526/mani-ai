# What every conversation is for (muhammad, 2026-10-01)

muhammad's standing instruction, kept here so a later session does not drift from it. Where it shows up in code,
the ADRs say why: [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]], [[ADR-008-every-reply-before-an-offer-asks-a-question]],
[[ADR-010-a-person-in-panic-is-guided-not-quizzed]], [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]].

1. **The target of every conversation is the person's feeling and situation.** Not the product's flow.
2. **The way Mani eases it is one path:** offer the framework that fits, run it to its end, do the somatic
   check, then give the best suited Library exercise.
3. **When the talk does not yet fall into a framework,** steer it toward the best fit. Each reply asks a
   crafted question about their feeling and their situation, and the same question also moves them toward a
   framework. A reply that only comforts, or that asks nothing, is a failure (ADR-008).

## Where each part stands, 2026-10-01

- Parts 1 and 3 are built and measured: questions are built from their words and reach for the first thing a
  framework needs to learn; offers follow Mani's confidence; the nearest fit is owed by the fourth message.
- Framework to somatic check is built. A framework's last stage hands to `somatic_checkin`, then
  `somatic_practice` (from `content/prompts/somatic.md`).
- **The last step does not work yet.** `admin.exercises` has 0 rows, so the exercise pick has nothing to choose,
  and the Library button lands on the Library home. The path ends one step early until the catalog is filled.
  Audio upload and the bucket are also open (PORT-STATUS, "Open engineering").
- Conversations that fit no framework (a greeting, a very unclear opening) are not forced into one; they get
  questions about the person's feeling and situation until something fits.
