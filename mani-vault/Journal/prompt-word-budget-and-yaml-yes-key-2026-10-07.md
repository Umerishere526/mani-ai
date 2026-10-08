---
type: journal
date: 2026-10-07
tags: [journal, prompts, yaml, gotcha]
---

# A word budget needs a real rewrite behind it, and a bare `yes` key is a boolean

Found while building spec 0003 (short base prompt).

## Write the files before you set the budget

Spec 0003 first said 1,500 words, then 2,000, each from an estimate that "removing only what is redundant lands near 2,200". The first honest rewrite, with every repeat, list, `any_stage` and `consent_lines` gone, was 3,220 words, 6% under the 3,436 it started from. Real behaviour (the `ctx` glossary for about 28 keys, the stuck cases in `in_a_framework`, the offer subcases) is most of the size. The budget that held every behaviour was 2,800. Count a real draft before putting a number in a spec. The budget now ratchets down as features 4 and 5 delete the `[ctx]` entries they own.

## A bare `yes:` key loads as `True`

YAML 1.1 reads `yes`, `no`, `on`, `off` as booleans, also as mapping keys. A rule named `yes` under `offers` loaded as the key `True`, so a test that looked it up by name would never find it. Name such rules `on_yes`. A value that contains a colon and a space (`on: its purpose`) also breaks a plain scalar. The guard test, `backend/tests/unit/test_prompt_budget.py`, catches both because it loads the files and refuses duplicate keys and lists.

## A rule that opens with a bracket is a list

`- [ctx] names the stage you are on` loads as a flow sequence and the whole file fails to parse. Open the sentence with a word ("The stage you are on is named in [ctx]"). Found building spec 0005; `test_every_style_value_the_schema_allows_is_taught` caught it because it loads `mani_base.md` as YAML.

## A banned phrase list is substring sensitive

"carrying" appeared inside "carrying on talking". The guard matches whole words, and the fix was a rewording ("talking on").

Related: [[client-lines-the-code-matches-exactly]], [[measure-before-tuning-prompts]]
