<div align="center">

# 🎬 Anime Streaming Backend

### Stream anime from 4+ sources with a single API call

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Deploy](https://img.shields.io/badge/Deploy-Heroku-430098?style=for-the-badge&logo=heroku&logoColor=white)](https://heroku.com)

**No API keys needed. No rate limits. Just works.**

[Get Started](#-quick-start) • [API Docs](#-api-endpoints) • [Deploy](#-deploy)

</div>

---

## 🤔 Why This?

Most anime APIs are either dead, rate-limited, or require API keys. This backend:

- ✅ **Works out of the box** — Zero configuration, zero API keys
- ✅ **4 sources** — AniList, Anitaku, 4Animo, Gogoanime (auto-fallback)
- ✅ **Instant search** — Type 2 characters, get suggestions with covers
- ✅ **M3U8 + HLS** — Direct stream links, no ads, no popups
- ✅ **Self-hosted** — Your server, your rules, no middleman
- ✅ **Heroku ready** — Deploy in 60 seconds

---

## ⚡ Quick Start

```bash
git clone https://github.com/rishavbuilder/anime-streaming-backend.git
cd anime-streaming-backend
pip install -r requirements.txt
python anime_scraper.py
```

Open **http://localhost:8000** — that's it. You're streaming.

---

## 🎯 What You Can Build

| Use Case | How |
|----------|-----|
| 🎥 Personal anime player | Use the built-in UI |
| 📱 Mobile app backend | Hit `/stream` endpoint |
| 🤖 Discord bot | Fetch streams for commands |
| 📊 Anime dashboard | Use `/search` + `/anime` endpoints |
| 🔗 Link shortener with preview | Use AniList metadata API |

---

## 🛠️ API Endpoints

### `POST /stream` — Get stream for any anime
```json
{
  "title": "One Piece",
  "episode": 1,
  "source": "auto"
}
```
**Response:**
```json
{
  "status": "success",
  "anime": "One Piece",
  "episode": 1,
  "master_url": "https://...",
  "qualities": [{"resolution": "1920x1080", "url": "..."}],
  "embed_url": null,
  "servers": [{"name": "HD-1", "url": "..."}],
  "source": "anilist",
  "meta": { "title": "One Piece", "genres": ["Action", "Adventure"] }
}
```

### `GET /search?q=naruto&source=auto` — Search anime
Returns suggestions with cover art, score, episode count.

### `GET /anime/21` — Get anime details
Full metadata from AniList (genres, relations, next airing, etc.)

### `GET /proxy?url=<embed_url>` — CORS proxy
Safely proxy embed pages (removes ads, fixes paths).

---

## 📡 Sources

| Source | Stream Type | Best For |
|--------|------------|----------|
| **AniList** | HD Embed (4Animo) | Metadata + HD playback |
| **Anitaku** | M3U8 direct | Quality selection, fast |
| **4Animo** | CDN Embed | Multiple servers (HD-1/2/3) |
| **Gogoanime** | M3U8 / Embed | Sub & Dub |

Auto mode tries all sources and picks the first working one.

---

## 🚀 Deploy

### Heroku (60 seconds)
```bash
heroku create anime-api
git push heroku main
```

### Railway
```bash
railway init
railway up
```

### Docker
```bash
docker build -t anime-api .
docker run -p 8000:8000 anime-api
```

---

## 🧩 Tech Stack

```
Python 3.8+    → Backend logic
FastAPI        → REST API framework
Uvicorn        → ASGI server
BeautifulSoup4 → HTML scraping
LXML           → Fast HTML parser
HLS.js         → Client-side HLS player (CDN)
```

---

## 📂 Project Structure

```
anime-streaming-backend/
├── anime_scraper.py    # Main server (FastAPI + all scrapers)
├── index.html          # Built-in web player UI
├── requirements.txt    # Python dependencies
├── Procfile            # Heroku deployment
├── LICENSE             # MIT License
└── README.md           # This file
```

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📜 License

MIT — do whatever you want.

---

<div align="center">

**⭐ Star this repo if it helped you build something cool**

[![GitHub stars](https://img.shields.io/github/stars/rishavbuilder/anime-streaming-backend?style=social)](https://github.com/rishavbuilder/anime-streaming-backend/stargazers)

</div>
