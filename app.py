import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import sqlite3
import pandas as pd
import datetime

# 🎯 Set up SQLite database to store transcripts
DB_NAME = "transcripts.db"


def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            timestamp TEXT,
            text TEXT,
            video_link TEXT
        )
    """)
    conn.commit()
    conn.close()


# ✅ Function to fetch video metadata from a playlist
def get_video_data(playlist_url):
    ydl_opts = {"quiet": True, "extract_flat": True, "force_generic_extractor": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    return [{"video_id": entry["id"], "title": entry["title"]} for entry in info.get("entries", [])]


# ✅ Function to fetch transcripts for a video
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
    except:
        return None


# ✅ Store transcripts in SQLite database
def store_transcripts(video_id, title, transcript):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for entry in transcript:
        cursor.execute("""
            INSERT OR IGNORE INTO transcripts (video_id, title, timestamp, text, video_link) 
            VALUES (?, ?, ?, ?, ?)
        """, (video_id, title, entry["timestamp"], entry["text"], entry["video_link"]))

    conn.commit()
    conn.close()


# ✅ Fetch transcripts for all videos in a playlist & store in DB
def fetch_and_store_transcripts(playlist_url):
    video_data = get_video_data(playlist_url)
    for video in video_data:
        transcript = get_transcript(video["video_id"])
        if transcript:
            store_transcripts(video["video_id"], video["title"], transcript)


# ✅ Search for transcripts in the database
def search_transcripts(keyword):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = f"SELECT * FROM transcripts WHERE text LIKE ?"
    cursor.execute(query, (f"%{keyword}%",))
    results = cursor.fetchall()

    conn.close()
    return results


# ✅ Convert search results into DataFrame
def results_to_df(results):
    return pd.DataFrame(results, columns=["video_id", "title", "timestamp", "text", "video_link"])


# 🚀 Streamlit Web App
def main():
    st.title("🔎 YouTube Transcript Search")

    # 🎥 Enter playlist URL
    playlist_url = st.text_input("Enter YouTube Playlist URL:")

    if st.button("Fetch Transcripts"):
        with st.spinner("Fetching transcripts... This may take a few minutes."):
            fetch_and_store_transcripts(playlist_url)
        st.success("✅ Transcripts saved to database!")

    # 🔍 Search box for transcripts
    search_keyword = st.text_input("Search for a keyword in transcripts:")

    if st.button("Search"):
        results = search_transcripts(search_keyword)
        if results:
            df = results_to_df(results)
            st.write(df)

            # Download results as CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Results as CSV", csv, "search_results.csv", "text/csv")

            # Show embedded videos
            for _, row in df.iterrows():
                st.markdown(f"### [{row['title']}]({row['video_link']}) ({row['timestamp']})")
                st.write(row["text"])
                start_seconds = int(row["timestamp"].split(":")[-1])
                st.video(f"https://www.youtube.com/embed/{row['video_id']}?start={start_seconds}&autoplay=1")

        else:
            st.warning("No results found.")


if __name__ == "__main__":
    create_database()  # Create DB if not exists
    main()
