import requests, re, sys
sys.stdout.reconfigure(encoding='utf-8')

r = requests.get("https://megaplay.buzz/lib/app.main.js?v=21784260800", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
text = r.text

# Find API endpoints
for match in re.finditer(r'["\']([^"\']*(?:api|source|stream|video|m3u8|file|get)[^"\']*)["\']', text):
    print(match.group(1)[:150])

print("\n--- ajax/fetch calls ---")
for match in re.finditer(r'(ajax|fetch|getJSON)\s*\(', text):
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 200)
    print(text[start:end][:250])
    print("---")
