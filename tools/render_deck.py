#!/usr/bin/env python3
"""Render deck/RG_Early_Warning_Deck.md to a landscape slide PDF (one '# ' section per slide) via headless Chrome."""
import re, subprocess, sys
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "deck" / "RG_Early_Warning_Deck.md").read_text()
front = re.match(r"---\n(.*?)\n---\n", src, re.S)
meta = dict(re.findall(r'^(\w+): "(.*)"$', front.group(1), re.M))
body = src[front.end():]
slides = [s.strip().strip("-").strip() for s in re.split(r"\n(?=# )", body) if s.strip().strip("-").strip()]
css = """
@page { size: 13.333in 7.5in; margin: 0; }
body { margin:0; font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color:#1b1f24; }
.slide { width:13.333in; height:7.5in; box-sizing:border-box; padding:0.45in 0.6in; page-break-after:always; overflow:hidden; position:relative; }
.slide h1 { font-size:26pt; color:#0f2537; margin:0 0 10px; border-bottom:4px solid #ff3621; padding-bottom:6px; }
.slide p, .slide li { font-size:12.5pt; line-height:1.35; margin:4px 0; }
.slide table { border-collapse:collapse; width:100%; font-size:11pt; margin:6px 0; }
.slide th { background:#0f2537; color:#fff; text-align:left; padding:5px 7px; }
.slide td { border-bottom:1px solid #dde3ea; padding:4px 7px; vertical-align:top; }
.slide pre { background:#f3f6f9; padding:10px; font-size:10.5pt; border-radius:6px; }
.slide code { font-size:10.5pt; background:#f3f6f9; padding:0 3px; }
.slide strong { color:#b8291a; }
.foot { position:absolute; bottom:0.2in; right:0.6in; font-size:9pt; color:#8592a0; }
.title { background:#0f2537; color:#fff; display:flex; flex-direction:column; justify-content:center; }
.title h1 { color:#fff; border:none; font-size:34pt; } .title p { font-size:16pt; color:#cfe0f0; }
"""
html = [f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>",
        f"<div class='slide title'><h1>{meta['title']}</h1><p>{meta['subtitle']}</p><p style='font-size:11pt'>All data synthetic · built and run on Databricks</p></div>"]
for i, s in enumerate(slides, 1):
    html.append(f"<div class='slide'>{markdown.markdown(s, extensions=['tables', 'fenced_code'])}<div class='foot'>{i + 1}</div></div>")
html.append("</body></html>")
out_html = ROOT / "deck" / "RG_Early_Warning_Deck.html"
out_html.write_text("\n".join(html))
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={ROOT / 'deck' / 'RG_Early_Warning_Deck.pdf'}", out_html.as_uri()], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("wrote deck/RG_Early_Warning_Deck.pdf with", len(slides) + 1, "slides")
