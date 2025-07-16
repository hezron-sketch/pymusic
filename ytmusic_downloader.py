#!/usr/bin/env python3
import argparse
import sys
import os
import logging
import yt_dlp

# Suppress yt-dlp debug output
logging.getLogger("yt_dlp").setLevel(logging.ERROR)

def search_youtube(query, max_results=5):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
        'extract_flat': True,  # Fast, but less metadata
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_url = f"ytsearch{max_results}:{query}"
        info = ydl.extract_info(search_url, download=False)
        entries = info.get('entries', [])
        for entry in entries:
            if not entry.get('webpage_url') and entry.get('id'):
                entry['webpage_url'] = f"https://www.youtube.com/watch?v={entry['id']}"
        return entries

def download_audio_from_url(url, output_dir):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': False,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"Error: {e}")

def search_and_download(query, output_dir):
    print(f"Searching for: {query}")
    results = search_youtube(query, max_results=5)
    if not results:
        print("No results found.")
        return
    print("Found the following songs:")
    for idx, entry in enumerate(results, 1):
        print(f"{idx}. {entry.get('title')} ({entry.get('webpage_url')})")
    while True:
        try:
            choice = input(f"Enter the number of the song to download (1-{len(results)}), or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                print("Exiting.")
                return
            choice = int(choice)
            if 1 <= choice <= len(results):
                selected = results[choice-1]
                print(f"Downloading: {selected.get('title')} ({selected.get('webpage_url')})")
                download_audio_from_url(selected.get('webpage_url'), output_dir)
                break
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")

def interactive_prompt(output_dir):
    print("YouTube Music Downloader CLI (Interactive Mode)")
    user_input = input("Enter YouTube link or song title: ").strip()
    if user_input.startswith("http://") or user_input.startswith("https://"):
        download_audio_from_url(user_input, output_dir)
    elif user_input:
        search_and_download(user_input, output_dir)
    else:
        print("No input provided. Exiting.")

def main():
    parser = argparse.ArgumentParser(description="YouTube Music Downloader CLI")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-u', '--url', help='YouTube video URL to download audio from')
    group.add_argument('-q', '--query', help='Search query to find and download the first result')
    parser.add_argument('-o', '--output', default='.', help='Output directory (default: current)')
    args = parser.parse_args()

    if not (args.url or args.query):
        interactive_prompt(args.output)
    elif args.url:
        download_audio_from_url(args.url, args.output)
    elif args.query:
        search_and_download(args.query, args.output)

if __name__ == "__main__":
    main()
