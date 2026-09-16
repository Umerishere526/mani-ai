# ABOUTME: Mani's opening line on a new thread.
# ABOUTME: Written here rather than generated, so the first screen costs nothing.

DEFAULT_NAME = "there"


def greeting(nickname: str | None, returning: bool) -> str:
    opener = "Nice to see you again." if returning else "It's Mani."
    return f"Hi {nickname or DEFAULT_NAME}. {opener} How can I support you today?"
