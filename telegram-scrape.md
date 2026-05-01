# Scrape a public Telegram channel — no auth

```bash
curl -sL "https://t.me/s/<channel>"           # ~16 latest posts
curl -sL "https://t.me/s/<channel>?before=<id>"  # older
```

Works only for public channels with web preview enabled. If `/s/` redirects to `/`, it's private / a user / disabled.

## Selectors

Each post: `<div class="tgme_widget_message" data-post="<channel>/<id>">`

| Field | Where |
|---|---|
| id | attr `data-post` |
| date | `time[datetime]` (ISO 8601) |
| text | `.tgme_widget_message_text.js-message_text` |
| views | `.tgme_widget_message_views` |
| photo | `.tgme_widget_message_photo_wrap` style `background-image:url(...)` |
| video | `video[src]` |
| author | `.tgme_widget_message_from_author` |

Image/video URLs (`cdn*.telesco.pe`) are direct — `curl -O` works.

## Python

```python
import re, requests
from bs4 import BeautifulSoup

def fetch(channel, before=None):
    url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
    return requests.get(url, timeout=20).text

def parse(html):
    out = []
    for box in BeautifulSoup(html, "html.parser").select("div.tgme_widget_message"):
        pid = box.get("data-post", "").split("/")[-1]
        text = box.select_one(".tgme_widget_message_text.js-message_text")
        time = box.select_one("time[datetime]")
        views = box.select_one(".tgme_widget_message_views")
        photos = [re.search(r"url\('([^']+)'\)", p.get("style", "")).group(1)
                  for p in box.select(".tgme_widget_message_photo_wrap")
                  if "background-image" in p.get("style", "")]
        videos = [v["src"] for v in box.select("video[src]")]
        out.append({
            "id": int(pid) if pid.isdigit() else pid,
            "date": time["datetime"] if time else None,
            "text": text.get_text("\n", strip=True) if text else "",
            "views": views.get_text(strip=True) if views else None,
            "photos": photos,
            "videos": videos,
        })
    return out

posts, before = [], None
for _ in range(5):
    page = parse(fetch("data_secrets", before))
    if not page: break
    posts += page
    before = page[0]["id"]
```

## Notes

- Throttle: `sleep 1–2s` between pages; back off on 429.
- Edits reflect current state; no edit history.
- For private channels you need MTProto (Telethon/Pyrogram) + a user session.
