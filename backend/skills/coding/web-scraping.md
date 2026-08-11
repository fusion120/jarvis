---
lang: python
keywords: scrape, scraper, beautifulsoup, bs4, html, page, website, crawl
---
# Scrape a web page with requests + BeautifulSoup

```python
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
r = requests.get("https://example.com/articles", headers=headers, timeout=30)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")
titles = [a.get_text(strip=True) for a in soup.select("h2 a")]
for t in titles[:10]:
    print(t)
```

Gotchas:
- **Send a `User-Agent`** header — many sites 403 bare `python-requests`.
- Respect robots.txt and the site's ToS; keep it polite (low rate, small
  batches). This is for Mohamed's own use, not mass harvesting.
- If the content is loaded by JavaScript, `requests` won't see it — you need a
  headless browser (Selenium/Playwright) instead; that's a bigger setup.
- Pages change — write defensive selectors and skip missing items with
  `if a is None: continue`.
- Save what you scrape to JSON so you don't re-hit the site.
