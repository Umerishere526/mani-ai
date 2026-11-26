# ABOUTME: The client's rules that code can read from a reply's words beyond what the turn enforces: gendered pronouns
# ABOUTME: and questions. Shared by the rule cases (run_eval) and the regression suite's checks.

from __future__ import annotations

import re

PRONOUNS = {"he": re.compile(r"\b(he|him|his|himself)\b", re.IGNORECASE),
            "she": re.compile(r"\b(she|her|hers|herself)\b", re.IGNORECASE)}
# Words for people that already say whether they are a he or a she, so Mani may use the pronoun once the person has
# named someone with one ("my sister" lets Mani say "she").
GENDERED_WORDS = {"he": re.compile(r"\b(brother|father|dad|husband|boyfriend|son|uncle|grand(?:father|pa)|nephew|"
                                   r"stepdad|stepfather|man|guy)s?\b", re.IGNORECASE),
                  "she": re.compile(r"\b(sister|mother|mom|mum|wife|girlfriend|daughter|aunt|grand(?:mother|ma)|niece|"
                                    r"stepmom|stepmother|woman|girl)s?\b", re.IGNORECASE)}
QUESTION = re.compile(r"[^.?!\n]*\?")


def questions(text: str) -> list[str]:
    return [q.strip() for q in QUESTION.findall(text) if q.strip(" ?")]


def pronouns(text: str) -> set[str]:
    """Which of he and she the text uses, in any form."""
    return {g for g, pattern in PRONOUNS.items() if pattern.search(text)}


def genders_named(text: str) -> set[str]:
    """Which of he and she the person's words establish: a pronoun, or a word for someone that carries it."""
    return pronouns(text) | {g for g, pattern in GENDERED_WORDS.items() if pattern.search(text)}
