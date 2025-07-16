from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import List
import yt_dlp
import os
import tempfile
import re
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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

def sanitize_filename(name):
    """Remove invalid characters from filename"""
    return re.sub(r'[\\/*?:"<>|]', "", name)

@app.post("/download")
async def download_endpoint(req: DownloadRequest):
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    # YouTubeDL options for high quality audio
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'verbose': True,  # For debugging
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',  # Highest quality
        }],
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'audioformat': 'mp3',
        'keepvideo': False,
        'writethumbnail': False,
        'noprogress': True,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'buffersize': 1024 * 1024 * 16,  # 16MB buffer
        'http_chunk_size': 10485760,  # 10MB chunks
        'extractor_args': {
            'youtube': {
                'player_skip': ['js', 'configs', 'webpage'],
            }
        },
        'concurrent_fragment_downloads': 10,  # Parallel downloads
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            
            # Verify file size
            file_size = os.path.getsize(mp3_filename)
            if file_size < 1024 * 1024:  # Less than 1MB is suspicious
                raise Exception(f"File too small ({file_size} bytes), likely download failed")
            
            # Read file content
            with open(mp3_filename, 'rb') as f:
                content = f.read()
            
            # Get sanitized filename
            title = info.get('title', 'audio')
            filename = f"{sanitize_filename(title)}.mp3"
            
            return Response(
                content=content,
                media_type='audio/mpeg',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': str(file_size)
                }
            )
            
    except Exception as e:
        return Response(
            content=str(e),
            status_code=500,
            media_type='text/plain'
        )
    finally:
        # Clean up temporary files
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)

if __name__ == "__main__":
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True if os.environ.get("DEV") == "1" else False
    )
