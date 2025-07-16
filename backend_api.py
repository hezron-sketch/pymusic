from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import yt_dlp
import os
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import tempfile

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

@app.post("/download")
async def download_endpoint(req: DownloadRequest):
    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(tempfile.gettempdir(), "yt_downloads")
    os.makedirs(temp_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': False,  # Set to False for debugging
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': '/usr/bin/ffmpeg',  # Ensure ffmpeg is available
        'extractaudio': True,
        'audioformat': 'mp3',
        'keepvideo': False,
        'writethumbnail': False,
        'noprogress': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            
            # Verify file size
            file_size = os.path.getsize(mp3_filename)
            if file_size < 100 * 1024:  # Less than 100KB is suspicious
                raise Exception(f"File too small ({file_size} bytes), likely download failed")
            
            # Read file and return as response
            with open(mp3_filename, 'rb') as f:
                file_content = f.read()
            
            # Clean up
            os.remove(mp3_filename)
            
            return {
                "status": "success",
                "filename": os.path.basename(mp3_filename),
                "content": file_content,
                "content_type": "audio/mpeg"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True if os.environ.get("DEV") == "1" else False
    )
