from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import List
import yt_dlp
import os
import tempfile
import re
import random
import time
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

def search_youtube(query, max_results=5):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
        'extract_flat': True,
        # Rotate user agents to avoid detection
        'user_agent': get_random_user_agent(),
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

def get_random_user_agent():
    """Return a random user agent to avoid detection"""
    agents = [
        # Popular browsers
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15',
        
        # Mobile browsers
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        
        # Add more user agents as needed
    ]
    return random.choice(agents)

@app.post("/download")
async def download_endpoint(req: DownloadRequest):
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    # YouTubeDL options with anti-detection measures
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'audioformat': 'mp3',
        'keepvideo': False,
        'writethumbnail': False,
        'noprogress': True,
        
        # Anti-detection settings
        'user_agent': get_random_user_agent(),
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'ignoreerrors': True,
        'no_check_certificate': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'cookiefile': 'cookies.txt',  # Optional: Create this file if you have cookies
        
        # Throttle to appear more human-like
        'throttledratelimit': 500000,  # 500 KB/s
        'sleep_interval': random.randint(1, 5),
        'max_sleep_interval': 8,
        
        # Browser simulation
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Add random delay to simulate human behavior
            time.sleep(random.uniform(0.5, 2.5))
            
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
        port=int(os.environ.get("PORT", 10000)),
        reload=True if os.environ.get("DEV") == "1" else False
    )