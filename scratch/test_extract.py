import urllib.request
import re

url = "https://steamrip.com/detroit-become-human-free-download-f1/"
req = urllib.request.Request(
    url,
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
)
html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")

# Find all anchor tags
links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
found = []
for href, text in links:
    clean_t = re.sub(r'<[^>]+>', '', text).strip()
    if any(k in href.lower() or k in clean_t.lower() for k in ["download", "torrent", "megadb", "buzz", "gofile", "1fichier", "magnet", "bzzhr"]):
        found.append((clean_t, href))
        print(f"[{clean_t}] -> {href}")

print(f"\nTotal extracted: {len(found)}")
