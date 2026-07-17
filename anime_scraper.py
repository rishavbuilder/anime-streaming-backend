# anime_scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse
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
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://anitaku.com.ro/",
        }, timeout=TIMEOUT)
        content = resp.text

        def fix_rel(m):
            prefix = m.group(1)
            path = m.group(2)
            if path.startswith(("http://", "https://", "//")):
                return m.group(0)
            return f'{prefix}{base}/{path.lstrip("/")}'

        content = re.sub(r'((?:src|href|action)=["\'])((?!https?://|//)[^"\']+)', fix_rel, content)

        if "4animo" in parsed.netloc:
            content = re.sub(r'fetch\(["\']((?!https?://|//)[^"\']+)', lambda m: f'fetch("{base}/{m.group(1).lstrip("/")}"', content)
            content = re.sub(r'url:\s*["\']((?!https?://|//)[^"\']+)', lambda m: f'url: "{base}/{m.group(1).lstrip("/")}"', content)
            content = re.sub(r'(["\'])(/stream/[^"\']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)
            content = re.sub(r'(["\'])(/p/[^"\']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)
            content = re.sub(r'(["\'])(/jwplayer/[^"\']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)

        if "tamilembed" in parsed.netloc or "vidmoly" in parsed.netloc or "megaplay" in parsed.netloc:
            content = re.sub(r'<script[^>]*src=["\'][^"\']*bilstedquotas[^"\']*["\'][^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<script[^>]*>.*?(?:eval|document\.write|adsbygoogle).*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<div[^>]*(?:id|class)=["\'](?:ad|ads|adv|pop|overlay|contact)[^"\']*["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL)

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

def resolve_embed_url(url, depth=0):
    if depth > 3:
        return None
    try:
        parsed = urlparse(url)
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://anitaku.com.ro/",
        }, timeout=TIMEOUT)
        text = resp.text
        m3u8_list = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', text)
        if m3u8_list:
            return {"m3u8": m3u8_list[0]}
        iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', text)
        if iframe_match:
            iframe_src = iframe_match.group(1)
            if iframe_src.startswith("//"):
                iframe_src = f"https:{iframe_src}"
            elif not iframe_src.startswith("http"):
                iframe_src = f"{parsed.scheme}://{parsed.netloc}/{iframe_src.lstrip('/')}"
            return resolve_embed_url(iframe_src, depth + 1)
        blob_match = re.search(r'["\']?(https?://[^\s"\'<>]*\.googlevideo[^\s"\'<>]*)', text)
        if blob_match:
            return {"m3u8": blob_match.group(1)}
        return None
    except:
        return None

# ── Source 1: anitaku.com.ro ──
def anitaku_scrape_meta(soup):
    meta = {}
    try:
        img = soup.select_one(".thumb img, .thumbook img")
        if img:
            meta["cover"] = img.get("src") or img.get("data-src")

        bigcover = soup.select_one(".bigcover .ime img")
        if bigcover:
            meta["banner"] = bigcover.get("src") or bigcover.get("data-src")

        title_el = soup.select_one("h1.entry-title, h1")
        if title_el:
            meta["title"] = title_el.get_text(strip=True)

        desc_el = soup.select_one(".desc, .mindesc, .entry-content .mindesc")
        if desc_el:
            meta["description"] = desc_el.get_text(strip=True)

        genres = []
        for a in soup.select(".genxed a"):
            genres.append(a.get_text(strip=True))
        meta["genres"] = genres

        spe_spans = soup.select(".spe span")
        for span in spe_spans:
            text = span.get_text(strip=True)
            if "Status:" in text:
                meta["status"] = text.replace("Status:", "").strip()
            elif "Studio:" in text:
                meta["studio"] = text.replace("Studio:", "").strip()
            elif "Released:" in text:
                meta["season_year"] = text.replace("Released:", "").strip()
            elif "Duration:" in text:
                meta["duration"] = text.replace("Duration:", "").strip()
            elif "Season:" in text:
                meta["season"] = text.replace("Season:", "").strip()

        rating_el = soup.select_one(".rating strong")
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            rating_num = re.search(r'[\d.]+', rating_text)
            if rating_num:
                meta["score"] = float(rating_num.group())

        alias_el = soup.select_one(".alter")
        if alias_el:
            meta["aliases"] = alias_el.get_text(strip=True)
    except:
        pass
    return meta

def anitaku_search(title):
    clean = title.strip().replace(" ", "-").lower()
    for path in [f"https://anitaku.com.ro/{clean}/", f"https://anitaku.com.ro/category/{clean}/"]:
        resp = requests.get(path, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            meta = anitaku_scrape_meta(soup)
            name = meta.get("title") or title
            return clean, name, meta
    return None, None, None

def anitaku_search_list(query, per_page=8):
    results = []
    seen_slugs = set()
    try:
        slug_candidates = []
        slug = query.strip().replace(" ", "-").lower()
        slug_candidates.append(slug)
        words = query.strip().lower().split()
        if len(words) > 1:
            slug_candidates.append(words[0])
            slug_candidates.append("-".join(words[:2]))

        try:
            gql = '''query ($search: String) {
              Media(search: $search, type: ANIME) {
                title { romaji english }
                synonyms
              }
            }'''
            resp = requests.post("https://graphql.anilist.co",
                json={"query": gql, "variables": {"search": query}},
                headers={"Content-Type": "application/json"}, timeout=8)
            media = resp.json().get("data", {}).get("Media", {})
            for key in ["english", "romaji"]:
                t = media.get("title", {}).get(key, "")
                if t:
                    slug_candidates.append(t.strip().lower().replace(" ", "-"))
            for syn in media.get("synonyms", []):
                if syn:
                    slug_candidates.append(syn.strip().lower().replace(" ", "-"))
        except:
            pass

        for s in slug_candidates:
            s = re.sub(r'[^a-z0-9\-]', '', s)
            if not s or s in seen_slugs:
                continue
            seen_slugs.add(s)
            for path in [f"https://anitaku.com.ro/{s}/", f"https://anitaku.com.ro/category/{s}/"]:
                try:
                    resp = requests.get(path, headers=HEADERS, timeout=8, allow_redirects=True)
                    if resp.status_code == 200 and "Page not found" not in resp.text:
                        soup = BeautifulSoup(resp.text, "lxml")
                        title_el = soup.select_one("h1.entry-title, .entry-title")
                        if not title_el:
                            title_el = soup.find("title")
                            if title_el:
                                t = title_el.get_text(strip=True)
                                t = t.split(" - ")[0].split(" All Episodes")[0].split(" Archives")[0].strip()
                        name = title_el.get_text(strip=True) if title_el else query
                        name = re.sub(r'\s*-\s*ANITAKU\.COM.*', '', name).strip()
                        name = re.sub(r'\s*All Episodes.*', '', name).strip()
                        img_el = soup.select_one(".thumb img, .thumbook img")
                        genre_els = soup.select(".genxed a")
                        desc_el = soup.select_one(".desc, .mindesc")
                        status_el = None
                        score_el = None
                        for sp in soup.select(".spe span"):
                            txt = sp.get_text(strip=True)
                            if "Status:" in txt:
                                status_el = txt.replace("Status:", "").strip()
                        rating_el = soup.select_one(".rating strong")
                        if rating_el:
                            m = re.search(r'[\d.]+', rating_el.get_text())
                            if m:
                                score_el = float(m.group())
                        if name.lower() in [r["title"].lower() for r in results]:
                            continue
                        if not name or "ANITAKU.COM" in name or len(name) < 2:
                            continue
                        results.append({
                            "id": s,
                            "title": name,
                            "cover": img_el.get("src") or img_el.get("data-src") if img_el else None,
                            "genres": [a.get_text(strip=True) for a in genre_els],
                            "status": status_el,
                            "score": score_el,
                            "description": desc_el.get_text(strip=True) if desc_el else None,
                            "format": "Anime",
                            "source": "anitaku",
                        })
                        if len(results) >= per_page:
                            return results
                        break
                except:
                    continue
    except:
        pass
    return results

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
        resolved = resolve_embed_url(server["url"])
        if resolved and resolved.get("m3u8"):
            qualities = get_qualities(resolved["m3u8"])
            return {
                "source": "anitaku",
                "master_url": resolved["m3u8"],
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

# ── Source 2: AniList + 4Animo ──
ANILIST_QUERY = '''
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english native }
    description(asHtml: false)
    coverImage { large medium color }
    bannerImage
    genres
    status
    episodes
    duration
    averageScore
    popularity
    season
    seasonYear
    format
    type
    nextAiringEpisode { episode airingAt }
    relations {
      edges {
        node { id title { romaji english } format }
        relationType
      }
    }
  }
}
'''

ANILIST_DETAIL_QUERY = '''
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title { romaji english native }
    description(asHtml: false)
    coverImage { large medium color }
    bannerImage
    genres
    status
    episodes
    duration
    averageScore
    popularity
    season
    seasonYear
    format
    type
    nextAiringEpisode { episode airingAt }
    relations {
      edges {
        node { id title { romaji english } format }
        relationType
      }
    }
  }
}
'''

def anilist_search(title):
    try:
        resp = requests.post("https://graphql.anilist.co",
            json={"query": ANILIST_QUERY, "variables": {"search": title}},
            headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        data = resp.json()
        media = data.get("data", {}).get("Media")
        if media:
            return _parse_anilist_media(media)
    except:
        pass
    return None

def anilist_detail(anime_id):
    try:
        resp = requests.post("https://graphql.anilist.co",
            json={"query": ANILIST_DETAIL_QUERY, "variables": {"id": anime_id}},
            headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        data = resp.json()
        media = data.get("data", {}).get("Media")
        if media:
            return _parse_anilist_media(media)
    except:
        pass
    return None

def _parse_anilist_media(media):
    desc = (media.get("description") or "").strip()
    desc = re.sub(r'<[^>]+>', '', desc)
    desc = re.sub(r'\n{3,}', '\n\n', desc)
    relations = []
    for edge in (media.get("relations") or {}).get("edges", []):
        node = edge.get("node", {})
        relations.append({
            "id": node.get("id"),
            "title": node.get("title", {}).get("english") or node.get("title", {}).get("romaji"),
            "format": node.get("format"),
            "relation": edge.get("relationType"),
        })
    return {
        "id": media["id"],
        "title": media["title"].get("english") or media["title"].get("romaji") or "",
        "title_romaji": media["title"].get("romaji", ""),
        "title_native": media["title"].get("native", ""),
        "description": desc,
        "cover": media.get("coverImage", {}).get("large"),
        "banner": media.get("bannerImage"),
        "color": media.get("coverImage", {}).get("color"),
        "genres": media.get("genres", []),
        "status": media.get("status"),
        "episodes": media.get("episodes"),
        "duration": media.get("duration"),
        "score": media.get("averageScore"),
        "popularity": media.get("popularity"),
        "season": media.get("season"),
        "season_year": media.get("seasonYear"),
        "format": media.get("format"),
        "next_airing": media.get("nextAiringEpisode"),
        "relations": relations,
    }

def anilist_search_list(query, page=1, per_page=8):
    gql = '''
    query ($search: String, $page: Int, $perPage: Int) {
      Page(page: $page, perPage: $perPage) {
        media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
          id
          title { romaji english }
          coverImage { medium color }
          format
          episodes
          status
          averageScore
        }
        pageInfo { total lastPage hasNextPage }
      }
    }
    '''
    try:
        resp = requests.post("https://graphql.anilist.co",
            json={"query": gql, "variables": {"search": query, "page": page, "perPage": per_page}},
            headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        data = resp.json()
        page_data = data.get("data", {}).get("Page", {})
        results = []
        for m in page_data.get("media", []):
            results.append({
                "id": m["id"],
                "title": m["title"].get("english") or m["title"].get("romaji") or "",
                "title_romaji": m["title"].get("romaji", ""),
                "cover": m.get("coverImage", {}).get("medium"),
                "color": m.get("coverImage", {}).get("color"),
                "format": m.get("format"),
                "episodes": m.get("episodes"),
                "status": m.get("status"),
                "score": m.get("averageScore"),
            })
        info = page_data.get("pageInfo", {})
        return {"results": results, "total": info.get("total"), "has_next": info.get("hasNextPage")}
    except:
        return {"results": [], "total": 0, "has_next": False}

def anilist_get_stream(anime_id, episode_num, title=""):
    servers = [
        ("HD-1 (VidPlay)", "hd-1"),
        ("HD-2 (MegaPlay)", "hd-2"),
        ("HD-3 (AniZone)", "hd-3"),
    ]
    server_list = []
    for name, srv in servers:
        embed_url = f"https://cdn.4animo.xyz/embed/{srv}/ani/{anime_id}/{episode_num}/sub?k=1"
        server_list.append({"name": name, "url": embed_url})

    meta = anilist_detail(anime_id)

    return {
        "source": "anilist",
        "master_url": None,
        "qualities": [],
        "servers": server_list,
        "embed_url": server_list[0]["url"],
        "meta": meta,
    }

# ── Source 2b: 4Animo direct ──
def animo_get_stream(anime_id, episode_num):
    servers = [
        ("HD-1 (VidPlay)", "hd-1"),
        ("HD-2 (MegaPlay)", "hd-2"),
        ("HD-3 (AniZone)", "hd-3"),
    ]
    server_list = []
    for name, srv in servers:
        embed_url = f"https://cdn.4animo.xyz/embed/{srv}/ani/{anime_id}/{episode_num}/sub?k=1"
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

@app.get("/search")
def search_anime(q: str, source: str = "auto", page: int = 1):
    if not q or len(q.strip()) < 2:
        return {"results": [], "total": 0, "has_next": False}
    query = q.strip()
    results = []
    has_next = False
    total = 0
    if source in ("auto", "anilist", "4animo", "gogoanime"):
        anilist_data = anilist_search_list(query, page=page)
        results += anilist_data["results"]
        has_next = anilist_data.get("has_next", False)
        total += anilist_data.get("total", 0)
    if source in ("auto", "anitaku"):
        anitaku_results = anitaku_search_list(query)
        results += anitaku_results
        total += len(anitaku_results)
    seen = set()
    unique = []
    for r in results:
        key = r.get("title", "").lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return {"results": unique, "total": total, "has_next": has_next}

@app.get("/anime/{anime_id}")
def get_anime_detail(anime_id: int):
    meta = anilist_detail(anime_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Anime not found")
    return {"status": "success", "anime": meta}

@app.post("/stream")
def stream_anime(req: AnimeRequest):
    try:
        sources = []
        meta = None

        if req.source in ("auto", "anilist"):
            ani_data = anilist_search(req.title)
            if ani_data:
                result = anilist_get_stream(ani_data["id"], req.episode)
                if result:
                    result["anime"] = ani_data["title"]
                    result["episode"] = req.episode
                    if not meta and result.get("meta"):
                        meta = result["meta"]
                    sources.append(result)

        if req.source in ("auto", "anitaku"):
            slug, name, anitaku_meta = anitaku_search(req.title)
            if slug:
                result = anitaku_get_stream(slug, req.episode)
                if result:
                    result["anime"] = name
                    result["episode"] = req.episode
                    if anitaku_meta:
                        result["meta"] = anitaku_meta
                    if not meta and anitaku_meta:
                        meta = anitaku_meta
                    sources.append(result)

        if req.source in ("auto", "4animo"):
            anidata = anilist_search(req.title)
            if anidata:
                result = animo_get_stream(anidata["id"], req.episode)
                if result:
                    result["anime"] = anidata["title"]
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
        resp_data = {
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
        if meta:
            resp_data["meta"] = meta
        elif best.get("meta"):
            resp_data["meta"] = best["meta"]
        return resp_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
