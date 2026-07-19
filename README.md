# Anime Streaming Backend

A powerful FastAPI-based backend server for searching, scraping, and streaming anime from multiple sources with a built-in web player UI.

## Features

- **Multi-Source Streaming** — Streams from 4 sources: AniList, Anitaku, 4Animo, Gogoanime
- **Auto Source Selection** — Automatically picks the best available source
- **HLS Player** — Built-in HLS.js video player with quality selection
- **Search with Suggestions** — Real-time anime search with cover art previews
- **Embed Proxy** — CORS-safe proxy for iframe embeds
- **Anime Metadata** — Fetches cover, description, genres, score, status, relations from AniList GraphQL API
- **Multiple Servers** — Switch between HD-1, HD-2, HD-3 embed servers
- **Deploy Anywhere** — Ready for Heroku, Railway, or any VPS

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Scraping:** BeautifulSoup4, lxml, Requests
- **Data Source:** AniList GraphQL API
- **Player:** HLS.js (client-side)
- **Frontend:** Vanilla HTML/CSS/JS (no framework)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web player UI |
| GET | `/search?q=<query>&source=<auto\|anilist\|anitaku\|gogoanime>&page=<n>` | Search anime |
| GET | `/anime/<anilist_id>` | Get anime details from AniList |
| POST | `/stream` | Fetch stream (body: `{title, episode, source}`) |
| GET | `/proxy?url=<embed_url>` | Proxy embed pages safely |

## Installation

```bash
git clone https://github.com/rishavbuilder/anime-streaming-backend.git
cd anime-streaming-backend
pip install -r requirements.txt
python anime_scraper.py
```

Server starts at `http://localhost:8000`

## Deployment (Heroku)

```bash
heroku create your-app-name
git push heroku main
```

Procfile is already configured.

## Usage

1. Open `http://localhost:8000` in browser
2. Type anime title — suggestions appear automatically
3. Select episode number and source (or keep Auto)
4. Click **Stream** — video plays in the built-in player
5. Switch servers using the server bar below the player

## Sources

| Source | Type | Notes |
|--------|------|-------|
| **AniList** | GraphQL API + 4Animo embeds | Best metadata, HD embeds |
| **Anitaku** | Web scraping | M3U8 streams, multiple mirrors |
| **4Animo** | CDN embeds | HD-1/HD-2/HD-3 servers |
| **Gogoanime** | Web scraping | Sub/Dub support |

## License

MIT
