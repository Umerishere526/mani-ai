# ABOUTME: A small copy icon under each message, as the ChatGPT and Claude apps have.
# ABOUTME: Streamlit has no copy control besides st.code's, so one shared click handler writes the text to the clipboard.

from __future__ import annotations

import html

import streamlit as st

# One listener for every icon on the page, registered once however many times the page reruns. The text rides on
# the button as an escaped attribute, never inside the script, so a message can never run as code. Streamlit strips
# SVG markup from st.html, so the script draws each icon (two overlapping squares, then a tick once copied) with the
# DOM as the button appears.
_SCRIPT = """
<script>
if (!window.__maniCopy) {
  window.__maniCopy = true;
  const NS = "http://www.w3.org/2000/svg";
  const icon = (shapes) => {
    const svg = document.createElementNS(NS, "svg");
    for (const [name, value] of Object.entries({
      width: "15", height: "15", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
      "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true",
    })) svg.setAttribute(name, value);
    for (const [tag, attrs] of shapes) {
      const shape = document.createElementNS(NS, tag);
      for (const [name, value] of Object.entries(attrs)) shape.setAttribute(name, value);
      svg.appendChild(shape);
    }
    return svg;
  };
  const copyIcon = () => icon([
    ["rect", { x: "9", y: "9", width: "13", height: "13", rx: "2" }],
    ["path", { d: "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" }],
  ]);
  const doneIcon = () => icon([["path", { d: "M20 6 9 17l-5-5" }]]);
  const draw = () => document.querySelectorAll(".mani-copy:empty").forEach((b) => b.replaceChildren(copyIcon()));
  draw();
  new MutationObserver(draw).observe(document.body, { childList: true, subtree: true });
  const fallback = (text) => {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  };
  document.addEventListener("click", async (event) => {
    const button = event.target.closest(".mani-copy");
    if (!button) return;
    const text = button.dataset.copy;
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      fallback(text);
    }
    button.replaceChildren(doneIcon());
    button.title = "Copied";
    setTimeout(() => { button.replaceChildren(copyIcon()); button.title = "Copy"; }, 1500);
  });
}
</script>
"""

# The same 2rem square as the edit icon beside it (app.py), so the two sit level on one row.
_STYLE = (
    "background:none;border:none;padding:0;color:#8e8ea0;cursor:pointer;line-height:0;border-radius:8px;"
    "width:2rem;height:2rem;display:inline-flex;align-items:center;justify-content:center;"
)
_HOVER = "<style>.mani-copy:hover { background: rgba(142, 142, 160, .2) !important; color: inherit !important; }</style>"


def copy_button(text: str) -> None:
    """A copy icon that copies `text` exactly as shown, line breaks included."""
    st.html(
        f'<button class="mani-copy" style="{_STYLE}" title="Copy" aria-label="Copy" '
        f'data-copy="{html.escape(text, quote=True)}"></button>' + _HOVER + _SCRIPT,
        width="content",
        unsafe_allow_javascript=True,
    )
