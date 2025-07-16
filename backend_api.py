from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import yt_dlp
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str

class SongResult(BaseModel):
    title: str
    url: str

class SearchResponse(BaseModel):
    results: List[SongResult]

class DownloadRequest(BaseModel):
    url: str


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

class DownloadResponse(BaseModel):
    status: str
    filename: str = None
    error: str = None

def search_youtube(query, max_results=5):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_url = f"ytsearch{max_results}:{query}"
        info = ydl.extract_info(search_url, download=False)
        entries = info.get('entries', [])
        results = []
        for entry in entries:
            url = entry.get('webpage_url') or (f"https://www.youtube.com/watch?v={entry['id']}" if entry.get('id') else None)
            if url:
                results.append(SongResult(title=entry.get('title', 'Unknown'), url=url))
        return results

@app.post("/search", response_model=SearchResponse)
def search_endpoint(req: SearchRequest):
    results = search_youtube(req.query)
    return SearchResponse(results=results)

@app.post("/download", response_model=DownloadResponse)
def download_endpoint(req: DownloadRequest):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join('.', '%(title)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return DownloadResponse(status="success", filename=os.path.basename(mp3_filename))
    except Exception as e:
        return DownloadResponse(status="error", error=str(e)) 
