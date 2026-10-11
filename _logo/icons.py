"""Renders PNG icons from assets/logo/sas-emblem.svg (needs: pip install playwright; playwright install webkit).
    python icons.py
"""
import os, pathlib
from playwright.sync_api import sync_playwright

LOGO = pathlib.Path(__file__).resolve().parent.parent / "assets" / "logo"
svg = (LOGO / "sas-emblem.svg").read_text()
# (file, size, background): touch icons get the cream paper so iOS doesn't fill the corners black
JOBS = [("favicon-32.png", 32, None), ("apple-touch-icon.png", 180, "#F6F3E6"), ("icon-192.png", 192, "#F6F3E6"), ("icon-512.png", 512, "#F6F3E6")]
with sync_playwright() as p:
    b = p.webkit.launch()
    for name, size, bg in JOBS:
        pg = b.new_page(viewport={"width": size, "height": size}, device_scale_factor=1)
        pad = 0 if size <= 32 else size // 12
        pg.set_content(f'<html><body style="margin:0;background:{bg or "transparent"}"><div style="padding:{pad}px;width:{size-2*pad}px;height:{size-2*pad}px">'
                       + svg.replace("<svg ", '<svg width="100%" height="100%" ', 1) + "</div></body></html>")
        pg.screenshot(path=str(LOGO / name), omit_background=bg is None)
    b.close()
print("ok")
