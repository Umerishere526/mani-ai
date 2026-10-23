# ABOUTME: Decodes one string field out of a JSON object as it streams, chunk by chunk.
# ABOUTME: The reply schema puts text last; only that field's decoded value reaches a client.

from __future__ import annotations

import re

_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}

# A lone surrogate is malformed Unicode, not malformed JSON: emit the replacement
# character for it, the way a browser would, rather than fail a whole turn over it.
_REPLACEMENT = "\ufffd"


class TextFieldExtractor:
    """Pulls the decoded value of one string field out of a streaming JSON object.

    feed() returns the text decoded since the last call, handling chunk splits
    anywhere - mid-key, mid-escape, mid-surrogate-pair. Everything outside the
    field (reasoning, planning, the closing braces) is dropped.
    """

    def __init__(self, field: str) -> None:
        self._key = re.compile(r'"' + re.escape(field) + r'"\s*:\s*"')
        self._seek = ""
        self._tail = ""
        self._high_code = 0
        self._decoded: list[str] = []
        self._found = False
        self.closed = False

    def feed(self, chunk: str) -> str:
        if self.closed:
            return ""
        data = chunk
        if not self._found:
            self._seek += chunk
            match = self._key.search(self._seek)
            if match is None:
                # The key can straddle a chunk boundary; keep a tail long enough to
                # hold a partial match instead of rescanning the whole preamble.
                self._seek = self._seek[-64:]
                return ""
            data = self._seek[match.end() :]
            self._seek = ""
            self._found = True

        out: list[str] = []
        data = self._tail + data
        self._tail = ""
        i, n = 0, len(data)
        while i < n:
            ch = data[i]
            if ch == "\\":
                if i + 1 >= n:
                    self._tail = data[i:]
                    break
                esc = data[i + 1]
                if esc == "u":
                    if i + 6 > n:
                        self._tail = data[i:]
                        break
                    # Not hex: the JSON is malformed. ValueError is the caller's
                    # signal to treat this attempt as a schema failure.
                    code = int(data[i + 2 : i + 6], 16)
                    i += 6
                    if 0xD800 <= code <= 0xDBFF:
                        self._flush_high(out)
                        self._high_code = code
                    elif 0xDC00 <= code <= 0xDFFF and self._high_code:
                        out.append(
                            chr(0x10000 + ((self._high_code - 0xD800) << 10) + code - 0xDC00)
                        )
                        self._high_code = 0
                    else:
                        self._flush_high(out)
                        out.append(chr(code))
                    continue
                if esc not in _ESCAPES:
                    raise ValueError(f"invalid escape \\{esc} in streamed JSON string")
                self._flush_high(out)
                out.append(_ESCAPES[esc])
                i += 2
                continue
            if ch == '"':
                self._flush_high(out)
                self.closed = True
                break
            self._flush_high(out)
            out.append(ch)
            i += 1

        piece = "".join(out)
        if piece:
            self._decoded.append(piece)
        return piece

    @property
    def text(self) -> str:
        return "".join(self._decoded)

    def _flush_high(self, out: list[str]) -> None:
        if self._high_code:
            out.append(_REPLACEMENT)
            self._high_code = 0
