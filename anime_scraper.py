# anime_scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, base64, re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnimeRequest(BaseModel):
    title: str
    episode: int = 1
    source: str = "auto"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
TIMEOUT = 15

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

@app.get("/proxy")
def proxy_embed(url: str):
    try:
        from urllib.parse import urljoin, urlparse
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"{parsed.scheme}://{parsed.netloc}/",
        }, timeout=TIMEOUT)
        content = resp.text
        if "4animo" in parsed.netloc:
            def fix_rel(m):
                prefix = m.group(1)
                path = m.group(2)
                if path.startswith(("http://", "https://", "//")):
                    return m.group(0)
                return f'{prefix}{base}/{path.lstrip("/")}'
            content = re.sub(r'((?:src|href|action)=["\'])((?!https?://|//)[^"\']+)', fix_rel, content)
            content = re.sub(r'fetch\(["\']((?!https?://|//)[^"\']+)', lambda m: f'fetch("{base}/{m.group(1).lstrip("/")}"', content)
            content = re.sub(r'url:\s*["\']((?!https?://|//)[^"\']+)', lambda m: f'url: "{base}/{m.group(1).lstrip("/")}"', content)
            content = re.sub(r'(["\'])(/stream/[^"\']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)
            content = re.sub(r'(["\'])(/p/[^"\']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)
            content = re.sub(r'(["\'])(/jwplayer/[^"\']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)
        return Response(content=content, media_type="text/html")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

def extract_m3u8(url):
    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://gogoanimez.to/",
        }, timeout=TIMEOUT)
        m3u8_urls = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', resp.text)
        return m3u8_urls
    except:
        return []

def get_qualities(master_url):
    try:
        r = requests.get(master_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
        lines = r.text.strip().split("\n")
        qualities = []
        for i, line in enumerate(lines):
            if "RESOLUTION=" in line:
                res_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
                if res_match and i + 1 < len(lines):
                    qualities.append({
                        "resolution": res_match.group(1),
                        "url": lines[i + 1].strip()
                    })
        return qualities
    except:
        return []

# ── Source 1: anitaku.com.ro ──
def anitaku_search(title):
    clean = title.strip().replace(" ", "-").lower()
    for path in [f"https://anitaku.com.ro/{clean}/", f"https://anitaku.com.ro/category/{clean}/"]:
        resp = requests.get(path, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            t = soup.find("title")
            name = t.get_text(strip=True).split(" - ")[0].split(" All")[0].split(" Archives")[0] if t else title
            return clean, name
    return None, None

def anitaku_get_stream(slug, episode_num):
    episode_url = f"https://anitaku.com.ro/{slug}-episode-{episode_num}/"
    resp = requests.get(episode_url, headers=HEADERS, timeout=TIMEOUT)
    if resp.status_code == 404:
        return None
    soup = BeautifulSoup(resp.text, "lxml")

    servers = []
    for opt in soup.select("select#mirror-select option[value]"):
        val = opt.get("value", "")
        name = opt.get_text(strip=True)
        if not val:
            continue
        try:
            decoded = base64.b64decode(val).decode()
            iframe_match = re.search(r'src="([^"]+)"', decoded)
            if iframe_match:
                servers.append({"name": name, "url": iframe_match.group(1)})
        except:
            pass

    for server in servers:
        m3u8_list = extract_m3u8(server["url"])
        if m3u8_list:
            qualities = get_qualities(m3u8_list[0])
            return {
                "source": "anitaku",
                "master_url": m3u8_list[0],
                "qualities": qualities,
                "servers": servers,
                "embed_url": None,
            }

    if servers:
        return {
            "source": "anitaku",
            "master_url": None,
            "qualities": [],
            "servers": servers,
            "embed_url": servers[0]["url"],
        }
    return None

# ── Source 2: cdn.4animo.xyz ──
def animo_search(title):
    query = '''
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        id
        title { romaji english }
      }
    }
    '''
    try:
        resp = requests.post("https://graphql.anilist.co",
            json={"query": query, "variables": {"search": title}},
            headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        data = resp.json()
        media = data.get("data", {}).get("Media")
        if media:
            ani_id = media["id"]
            name = media["title"].get("english") or media["title"].get("romaji") or title
            return ani_id, name
    except:
        pass
    return None, None

def animo_get_stream(ani_id, episode_num):
    servers = [
        ("HD-1 (VidPlay)", "hd-1"),
        ("HD-2 (MegaPlay)", "hd-2"),
        ("HD-3 (AniZone)", "hd-3"),
    ]
    server_list = []
    for name, srv in servers:
        embed_url = f"https://cdn.4animo.xyz/embed/{srv}/ani/{ani_id}/{episode_num}/sub?k=1"
        server_list.append({"name": name, "url": embed_url})

    return {
        "source": "4animo",
        "master_url": None,
        "qualities": [],
        "servers": server_list,
        "embed_url": server_list[0]["url"],
    }

# ── Source 3: gogoanimez.to ──
def gogo_search(title):
    clean = title.strip().replace(" ", "-").lower()
    resp = requests.get(f"https://gogoanimez.to/anime/{clean}/", headers=HEADERS, timeout=TIMEOUT)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "lxml")
        t = soup.find("title")
        name = t.get_text(strip=True).split(" – ")[0].split(" Online")[0] if t else title
        return clean, name
    return None, None

def gogo_get_stream(slug, episode_num):
    episode_url = f"https://gogoanimez.to/{slug}-episode-{episode_num}/"
    resp = requests.get(episode_url, headers=HEADERS, timeout=TIMEOUT)
    if resp.status_code == 404:
        return None
    soup = BeautifulSoup(resp.text, "lxml")

    servers = []
    for a in soup.select(".anime_muti_link a[data-video]"):
        name = a.get_text(strip=True)
        video = a.get("data-video", "")
        iframe_match = re.search(r'src="([^"]+)"', video)
        if iframe_match:
            servers.append({"name": name, "url": iframe_match.group(1)})

    if not servers:
        iframe = soup.find("iframe", src=True)
        if iframe:
            servers.append({"name": "Default", "url": iframe["src"]})

    for server in servers:
        m3u8_list = extract_m3u8(server["url"])
        if m3u8_list:
            qualities = get_qualities(m3u8_list[0])
            return {
                "source": "gogoanime",
                "master_url": m3u8_list[0],
                "qualities": qualities,
                "servers": servers,
                "embed_url": None,
            }

    if servers:
        return {
            "source": "gogoanime",
            "master_url": None,
            "qualities": [],
            "servers": servers,
            "embed_url": servers[0]["url"],
        }
    return None

@app.post("/stream")
def stream_anime(req: AnimeRequest):
    try:
        sources = []
        if req.source in ("auto", "anitaku"):
            slug, name = anitaku_search(req.title)
            if slug:
                result = anitaku_get_stream(slug, req.episode)
                if result:
                    result["anime"] = name
                    result["episode"] = req.episode
                    sources.append(result)

        if req.source in ("auto", "4animo"):
            ani_id, name = animo_search(req.title)
            if ani_id:
                result = animo_get_stream(ani_id, req.episode)
                if result:
                    result["anime"] = name
                    result["episode"] = req.episode
                    sources.append(result)

        if req.source in ("auto", "gogoanime"):
            slug, name = gogo_search(req.title)
            if slug:
                result = gogo_get_stream(slug, req.episode)
                if result:
                    result["anime"] = name
                    result["episode"] = req.episode
                    sources.append(result)

        if not sources:
            raise HTTPException(status_code=404, detail="No streams found from any source")

        best = sources[0]
        return {
            "status": "success",
            "anime": best["anime"],
            "episode": best["episode"],
            "master_url": best.get("master_url"),
            "qualities": best.get("qualities", []),
            "embed_url": best.get("embed_url"),
            "servers": best.get("servers", []),
            "source": best["source"],
            "all_sources": [{"source": s["source"], "has_m3u8": bool(s.get("master_url"))} for s in sources],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
