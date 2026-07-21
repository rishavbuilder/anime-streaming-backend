# anime_scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response, StreamingResponse
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
WH_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
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

        content = re.sub(r'((?:src|href|action)=["\'])((?!https?://|//)[^"\'']+)', fix_rel, content)

        if "4animo" in parsed.netloc:
            content = re.sub(r'fetch\(["\']((?!https?://|//)[^"\'']+)', lambda m: f'fetch("{base}/{m.group(1).lstrip("/")}"', content)
            content = re.sub(r'url:\s*["\']((?!https?://|//)[^"\'']+)', lambda m: f'url: "{base}/{m.group(1).lstrip("/")}"', content)
            content = re.sub(r'(["\'])(/stream/[^"\'']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)
            content = re.sub(r'(["\'])(/p/[^"\'']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)
            content = re.sub(r'(["\'])(/jwplayer/[^"\'']*)', lambda m: f'{m.group(1)}{base}{m.group(2)}', content)

        if "tamilembed" in parsed.netloc or "vidmoly" in parsed.netloc or "megaplay" in parsed.netloc:
            content = re.sub(r'<script[^>]*src=["\'][^"\'']*bilstedquotas[^"\'']*["\'][^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<script[^>]*>.*?(?:eval|document\.write|adsbygoogle).*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<div[^>]*(?:id|class)=["\'](?:ad|ads|adv|pop|overlay|contact)[^"\'']*["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL)

        headers = {"Content-Type": "text/html"}
        return Response(content=content, headers=headers, media_type="text/html")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/stream-proxy")
def stream_proxy(url: str):
    try:
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://watchhentai.net/",
        }
        resp = requests.get(url, headers=req_headers, timeout=30, stream=True)
        resp_headers = {
            "Content-Type": resp.headers.get("Content-Type", "video/mp4"),
            "Access-Control-Allow-Origin": "*",
        }
        if "Content-Length" in resp.headers:
            resp_headers["Content-Length"] = resp.headers["Content-Length"]
        if "Content-Range" in resp.headers:
            resp_headers["Content-Range"] = resp.headers["Content-Range"]
        def stream():
            try:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk
            except:
                pass
            finally:
                resp.close()
        return StreamingResponse(stream(), headers=resp_headers, media_type=resp_headers["Content-Type"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))