"""Windows 95 look: one CSS block and small HTML builders. No external fonts, images or scripts.

Builders return compact one-line HTML (blank lines or 4-space indents would be treated as Markdown code).
`window(title, body_html)` expects `body_html` to be already safe: build it with the escaping helpers in render.py.
"""

import html
from datetime import datetime

CSS = """
:root { --gray:#c0c0c0; --dark:#808080; --light:#ffffff; --black:#000000; --navy:#000080; --teal:#008080; }
html, body, .stApp, [data-testid="stAppViewContainer"] { background: var(--teal) !important; }
.stApp, .stApp p, .stApp label, .stApp span, .stApp li {
  font-family: "MS Sans Serif", "Microsoft Sans Serif", Tahoma, Verdana, Geneva, sans-serif;
  color: var(--black);
}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer { display: none !important; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 780px; padding: 1.2rem 1rem 4.5rem !important; }

/* Windows ----------------------------------------------------------------------------------------------------- */
.w95-window { background: var(--gray); border: 2px solid; border-color: var(--light) var(--black) var(--black) var(--light);
  box-shadow: inset -1px -1px 0 var(--dark), inset 1px 1px 0 #dfdfdf; padding: 2px; margin: 0 0 14px; }
.w95-title { background: linear-gradient(90deg, var(--navy), #1084d0); color: var(--light) !important; font-weight: bold;
  display: flex; justify-content: space-between; align-items: center; padding: 2px 3px 2px 6px; font-size: 13px; }
.w95-title * { color: var(--light) !important; }
.w95-controls { display: flex; gap: 2px; }
.w95-ctl { width: 16px; height: 14px; background: var(--gray); border: 1px solid; border-color: var(--light) var(--black) var(--black) var(--light);
  display: inline-flex; align-items: center; justify-content: center; font-size: 10px; line-height: 1; color: var(--black) !important; }
.w95-body { padding: 10px 12px; font-size: 14px; line-height: 1.4; }
.w95-body h4 { margin: 10px 0 4px; font-size: 14px; }
.w95-body p { margin: 4px 0; }

.w95-scroll { overflow-x: auto; }
.w95-table { width: 100%; border-collapse: collapse; background: var(--light); border: 2px solid;
  border-color: var(--dark) var(--light) var(--light) var(--dark); font-family: "Courier New", Courier, monospace; font-size: 13px; margin: 2px 0 8px; }
.w95-table th { background: var(--gray); text-align: left; padding: 2px 6px; border: 1px solid; border-color: var(--light) var(--dark) var(--dark) var(--light); font-family: inherit; }
.w95-table td { padding: 2px 6px; border-bottom: 1px dotted var(--dark); word-break: break-word; }
.w95-kv td:first-child { white-space: nowrap; font-weight: bold; }
.w95-status { font-weight: bold; }
.w95-pre { background: var(--light); border: 2px solid; border-color: var(--dark) var(--light) var(--light) var(--dark);
  padding: 6px; font-family: "Courier New", Courier, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word; margin: 6px 0 0; }
.w95-body details summary { cursor: pointer; font-weight: bold; }

/* Dialogs (info / error) ---------------------------------------------------------------------------------------- */
.w95-dialog { display: flex; gap: 14px; align-items: flex-start; }
.w95-icon { flex: 0 0 32px; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font: bold 22px "Times New Roman", serif; color: var(--light) !important; border: 2px solid var(--black); }
.w95-icon-error { background: #c00000; }
.w95-icon-info { background: #0000c0; }
.w95-icon-warn { background: #ffd700; color: var(--black) !important; }
.w95-dialog-text { flex: 1; }
.w95-btn { display: inline-block; min-width: 74px; text-align: center; padding: 3px 12px; margin-top: 8px; background: var(--gray); border: 2px solid;
  border-color: var(--light) var(--black) var(--black) var(--light); box-shadow: inset -1px -1px 0 var(--dark); }

/* Trojan Tim ---------------------------------------------------------------------------------------------------- */
.w95-tim-row { display: flex; gap: 16px; align-items: flex-start; }
.w95-tim { width: 96px; height: auto; image-rendering: pixelated; flex: 0 0 96px; }
.w95-bubble { position: relative; background: #ffffe1; border: 1px solid var(--black); padding: 8px 12px; flex: 1; box-shadow: 2px 2px 0 var(--dark); }
.w95-bubble::before { content: ""; position: absolute; left: -9px; top: 22px; border: 8px solid transparent; border-right-color: var(--black); border-left: 0; }
.w95-bubble::after { content: ""; position: absolute; left: -7px; top: 23px; border: 7px solid transparent; border-right-color: #ffffe1; border-left: 0; }
.w95-bubble p { margin: 0 0 6px; }
.w95-bubble p:last-child { margin-bottom: 0; }
@media (prefers-reduced-motion: no-preference) {
  .w95-tim { animation: w95-bob 1.4s steps(2, jump-none) infinite; }
  @keyframes w95-bob { from { transform: translateY(0); } to { transform: translateY(-3px); } }
}
@media (max-width: 600px) {
  .w95-tim-row { flex-direction: column; }
  .w95-bubble::before, .w95-bubble::after { display: none; }
}

/* The real Streamlit form, dressed as a "Run" window ------------------------------------------------------------ */
[data-testid="stForm"] { background: var(--gray); border: 2px solid !important; border-radius: 0 !important;
  border-color: var(--light) var(--black) var(--black) var(--light) !important; box-shadow: inset -1px -1px 0 var(--dark), inset 1px 1px 0 #dfdfdf;
  padding: 36px 14px 14px !important; position: relative; margin-bottom: 14px; }
[data-testid="stForm"]::before { content: "Run"; position: absolute; top: 2px; left: 2px; right: 2px; height: 20px; padding-left: 6px;
  background: linear-gradient(90deg, var(--navy), #1084d0); color: var(--light); font: bold 13px/20px Tahoma, Verdana, sans-serif; }
[data-testid="stForm"] label p { color: var(--black) !important; font-weight: bold; }
[data-testid="stTextInput"] input { border-radius: 0 !important; background: var(--light) !important; color: var(--black) !important;
  border: 2px solid !important; border-color: var(--dark) var(--light) var(--light) var(--dark) !important;
  font-family: "Courier New", Courier, monospace !important; box-shadow: inset 1px 1px 0 var(--black); }
[data-testid="stTextInput"] > div, [data-testid="stTextInput"] > div > div { border-radius: 0 !important; background: transparent !important; border: 0 !important; box-shadow: none !important; }
[data-testid="stFormSubmitButton"] button { border-radius: 0 !important; background: var(--gray) !important; color: var(--black) !important; font-weight: bold;
  border: 2px solid !important; border-color: var(--light) var(--black) var(--black) var(--light) !important; box-shadow: inset -1px -1px 0 var(--dark); }
[data-testid="stFormSubmitButton"] button:active { border-color: var(--black) var(--light) var(--light) var(--black) !important; box-shadow: inset 1px 1px 0 var(--dark); }
[data-testid="stTextInput"] input:focus-visible, [data-testid="stFormSubmitButton"] button:focus-visible { outline: 1px dotted var(--black) !important; outline-offset: 2px !important; }

/* Taskbar ------------------------------------------------------------------------------------------------------- */
.w95-taskbar { position: fixed; left: 0; right: 0; bottom: 0; height: 34px; background: var(--gray); border-top: 2px solid var(--light);
  display: flex; align-items: center; gap: 6px; padding: 2px 4px; z-index: 1000; font-size: 13px; }
.w95-start, .w95-task { display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 10px; border: 2px solid;
  border-color: var(--light) var(--black) var(--black) var(--light); box-shadow: inset -1px -1px 0 var(--dark); font-weight: bold; }
.w95-start img { width: 18px; height: auto; image-rendering: pixelated; }
.w95-task { font-weight: normal; border-color: var(--black) var(--light) var(--light) var(--black); box-shadow: inset 1px 1px 0 var(--dark); }
.w95-clock { margin-left: auto; padding: 3px 10px; border: 1px solid; border-color: var(--dark) var(--light) var(--light) var(--dark); }
"""


def css_block() -> str:
    return f"<style>{CSS}</style>"


def window(title: str, body_html: str) -> str:
    """A beveled window with a blue title bar. `title` is escaped; `body_html` must already be safe."""
    return (
        f'<div class="w95-window"><div class="w95-title"><span>{html.escape(title)}</span>'
        '<span class="w95-controls" aria-hidden="true"><span class="w95-ctl">_</span><span class="w95-ctl">&#9633;</span>'
        '<span class="w95-ctl">&#215;</span></span></div>'
        f'<div class="w95-body">{body_html}</div></div>'
    )


_ICONS = {"error": ("w95-icon-error", "X"), "info": ("w95-icon-info", "i"), "warn": ("w95-icon-warn", "!")}


def dialog(kind: str, title: str, message: str) -> str:
    """A classic message box. Title and message are escaped. The OK button is decoration only."""
    css_class, glyph = _ICONS[kind]
    return window(
        title,
        f'<div class="w95-dialog"><span class="w95-icon {css_class}" aria-hidden="true">{glyph}</span>'
        f'<div class="w95-dialog-text"><p>{html.escape(message)}</p><span class="w95-btn" aria-hidden="true">OK</span></div></div>',
    )


def taskbar(tim_img_html: str, now: datetime | None = None) -> str:
    """Decorative taskbar. The clock shows the time the page was rendered (no JavaScript)."""
    now = now or datetime.now()
    clock = now.strftime("%I:%M %p").lstrip("0")
    return (
        f'<div class="w95-taskbar" aria-hidden="true"><span class="w95-start">{tim_img_html}Start</span>'
        f'<span class="w95-task">Trojan Tim.exe</span><span class="w95-clock">{html.escape(clock)}</span></div>'
    )
