# YouTube Music Downloader CLI

A simple command-line tool to download music from YouTube as MP3 files.

## Features
- Download audio from a YouTube video URL
- Search YouTube and download the first result
- Converts audio to MP3 (requires ffmpeg)

## Installation

1. Clone this repository or copy the files to your machine.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install ffmpeg (required for MP3 conversion):
   - On Ubuntu/Debian:
     ```bash
     sudo apt-get install ffmpeg
     ```
   - On Fedora:
     ```bash
     sudo dnf install ffmpeg
     ```
   - On MacOS (with Homebrew):
     ```bash
     brew install ffmpeg
     ```

## Usage

Run the CLI tool from the `player` directory:

### Download by YouTube URL
```bash
python ytmusic_downloader.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --output /path/to/save
```

### Download by Search Query
```bash
python ytmusic_downloader.py --query "artist song name" --output /path/to/save
```

- The `--output` argument is optional (defaults to current directory).
- If `pydub` or `ffmpeg` is not installed, the audio will be saved in its original format (usually .webm or .mp4).

## Notes
- Make sure you comply with YouTube's Terms of Service when downloading content.
- For best results, ensure both `pydub` and `ffmpeg` are installed for MP3 conversion. 