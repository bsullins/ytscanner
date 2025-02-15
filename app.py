import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import pandas as pd
import sqlite3
import datetime

# Initialize SQLite database
conn = sqlite3.connect('transcripts.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS transcripts (
        video_id TEXT PRIMARY KEY,
        title TEXT,
        timestamp TEXT,
        text TEXT,
        video_link TEXT
    )
''')
conn.commit()

# Function to fetch video data from a playlist
def get_video_data(playlist_url):
    ydl_opts = {"quiet": True, "extract_flat": True, "force_generic_extractor": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    return [{"video_id": entry["id"], "title": entry["title"]} for entry in info.get("entries", [])]

# Function to fetch transcript for a video
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return [
            {
                "timestamp": str(datetime.timedelta(seconds=int(entry["start"]))),
                "text": entry["text"],
                "video_link": f"https://www.youtube.com/watch?v={video_id}&t={int(entry['start'])}s",
            }
            for entry in transcript
        ]
    except TranscriptsDisabled:
        st.warning(f"Transcripts are disabled for video ID: {video_id}")
        return None
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Function to store transcripts in the database
def store_transcripts(video_id, title, transcript):
    for entry in transcript:
        c.execute('''
            INSERT OR IGNORE INTO transcripts (video_id, title, timestamp, text, video_link)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, title, entry["timestamp"], entry["text"], entry["video_link"]))
    conn.commit()

# Streamlit app interface
st.title("YouTube Playlist Transcript Search")

playlist_url = st.text_input("Enter YouTube Playlist URL:")
search_term = st.text_input("Enter search term:")

if st.button("Fetch and Search Transcripts"):
    if not playlist_url or not search_term:
        st.error("Please provide both a playlist URL and a search term.")
    else:
        with st.spinner("Fetching video data..."):
            video_data = get_video_data(playlist_url)
            if not video_data:
                st.error("No videos found in the provided playlist.")
            else:
                st.success(f"Found {len(video_data)} videos in the playlist.")
                for video in video_data:
                    st.write(f"Processing video: {video['title']}")
                    transcript = get_transcript(video["video_id"])
                    if transcript:
                        store_transcripts(video["video_id"], video["title"], transcript)
                st.success("Transcripts fetched and stored successfully.")

        # Search the transcripts
        c.execute('''
            SELECT title, timestamp, text, video_link FROM transcripts
            WHERE text LIKE ?
        ''', (f"%{search_term}%",))
        results = c.fetchall()

        if results:
            st.write(f"Found {len(results)} matching results:")
            for title, timestamp, text, video_link in results:
                st.write(f"**{title}** ({timestamp})")
                st.write(text)
                st.write(f"[Watch Video]({video_link})")
        else:
            st.write("No matching transcripts found.")

# Close the database connection when the app is stopped
def close_connection():
    conn.close()

st.on_event("shutdown", close_connection)