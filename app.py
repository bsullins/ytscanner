import streamlit as st
import json
import os
from googleapiclient.discovery import build
import streamlit.components.v1 as components

# YouTube API setup (if available)
YOUTUBE_API_KEY = None
try:
    YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")
except:
    pass

def get_cached_channels():
    """Get list of available channels from cached transcripts."""
    cache_dir = "transcripts_cache"
    if not os.path.exists(cache_dir):
        return []
    
    channels = {}
    files = os.listdir(cache_dir)
    
    for file in files:
        if file.endswith('.json'):
            try:
                with open(os.path.join(cache_dir, file), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if len(data) > 2:  # Only include videos with substantial transcripts
                        channel_name = data[0].get('channel_name', 'Unknown Channel')
                        if channel_name not in channels:
                            channels[channel_name] = 0
                        channels[channel_name] += 1
            except:
                continue
    
    return channels

@st.cache_data
def get_video_info(video_id):
    """Get video title and publish date using YouTube API or cache."""
    # First try to get from cache
    cache_file = f"transcripts_cache/{video_id}.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data and len(data) > 0:
                    return {
                        'title': data[0].get('title', f'Video {video_id}'),
                        'publishedAt': data[0].get('published_at', 'Unknown date')
                    }
        except:
            pass
    
    # Fallback if API not available
    return {
        'title': f'Video {video_id}',
        'publishedAt': 'Unknown date'
    }

def search_phrase_in_text(phrase, text, max_word_distance=5):
    """Search for phrase with words that can be separated by up to max_word_distance words."""
    if not phrase or not text:
        return False
    
    phrase_words = phrase.lower().split()
    if len(phrase_words) == 1:
        return phrase_words[0] in text.lower()
    
    text_words = text.lower().split()
    
    # Find positions of each phrase word in the text
    word_positions = {}
    for phrase_word in phrase_words:
        positions = []
        for i, text_word in enumerate(text_words):
            if phrase_word in text_word:
                positions.append(i)
        if not positions:  # If any phrase word is not found, return False
            return False
        word_positions[phrase_word] = positions
    
    # Check if we can find all phrase words within max_word_distance
    first_word_positions = word_positions[phrase_words[0]]
    
    for start_pos in first_word_positions:
        found_all = True
        last_found_pos = start_pos
        
        for phrase_word in phrase_words[1:]:
            found_current = False
            for pos in word_positions[phrase_word]:
                if pos > last_found_pos and pos - last_found_pos <= max_word_distance + 1:
                    last_found_pos = pos
                    found_current = True
                    break
            
            if not found_current:
                found_all = False
                break
        
        if found_all:
            return True
    
    return False

def search_cached_transcripts(search_term, channel_name=None):
    """Search through cached transcript files."""
    cache_dir = "transcripts_cache"
    if not os.path.exists(cache_dir):
        return []
    
    results = []
    files = os.listdir(cache_dir)
    
    for file in files:
        if not file.endswith('.json'):
            continue
            
        video_id = file.replace('.json', '')
        
        try:
            with open(os.path.join(cache_dir, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if not data or len(data) <= 2:
                    continue
                
                # Filter by channel if specified
                if channel_name and data[0].get('channel_name') != channel_name:
                    continue
                
                video_matches = []
                
                for entry in data:
                    if search_phrase_in_text(search_term, entry.get('text', '')):
                        video_matches.append({
                            'video_id': video_id,
                            'title': entry.get('title', f'Video {video_id}'),
                            'channel_name': entry.get('channel_name', 'Unknown Channel'),
                            'timestamp': entry.get('start', 0),
                            'text': entry.get('text', ''),
                            'published_at': entry.get('published_at', 'Unknown date')
                        })
                
                if video_matches:
                    results.append({
                        'video_id': video_id,
                        'title': video_matches[0]['title'],
                        'channel_name': video_matches[0]['channel_name'],
                        'published_at': video_matches[0]['published_at'],
                        'matches': video_matches
                    })
                    
        except Exception as e:
            continue
    
    # Sort by publish date (newest first, with unknown dates last)
    def sort_key(item):
        if item['published_at'] == 'Unknown date':
            return '0000-00-00'
        return item['published_at']
    
    results.sort(key=sort_key, reverse=True)
    return results

def format_timestamp(seconds):
    """Format seconds into HH:MM:SS format."""
    try:
        seconds = float(seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except:
        return "00:00:00"

def generate_theme_css(is_dark_mode):
    """Generate CSS based on theme selection."""
    if is_dark_mode:
        return """
        <style>
        .video-container {
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #333;
        }
        .video-title {
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .matches-container {
            margin-top: 15px;
        }
        .timestamp-item {
            display: flex;
            margin-bottom: 8px;
            padding: 8px;
            background-color: #2d2d2d;
            border-radius: 5px;
            border-left: 3px solid #0084ff;
        }
        .timestamp-link {
            width: 100px;
            color: #0084ff;
            text-decoration: none;
            font-family: monospace;
            font-weight: bold;
            margin-right: 15px;
            flex-shrink: 0;
        }
        .timestamp-link:hover {
            color: #66b3ff;
        }
        .timestamp-text {
            color: #e0e0e0;
            flex: 1;
            line-height: 1.4;
        }
        </style>
        """
    else:
        return """
        <style>
        .video-container {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
        }
        .video-title {
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .matches-container {
            margin-top: 15px;
        }
        .timestamp-item {
            display: flex;
            margin-bottom: 8px;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 3px solid #0084ff;
        }
        .timestamp-link {
            width: 100px;
            color: #0084ff;
            text-decoration: none;
            font-family: monospace;
            font-weight: bold;
            margin-right: 15px;
            flex-shrink: 0;
        }
        .timestamp-link:hover {
            color: #0056b3;
        }
        .timestamp-text {
            color: #333333;
            flex: 1;
            line-height: 1.4;
        }
        </style>
        """

def main():
    st.set_page_config(page_title="YouTube Transcript Search", page_icon="🔍", layout="wide")
    
    # Initialize session state
    if 'theme_mode' not in st.session_state:
        st.session_state.theme_mode = 'dark'
    
    # Theme toggle in sidebar
    with st.sidebar:
        st.title("Settings")
        
        # Theme toggle
        theme_label = "🌙 Dark Mode" if st.session_state.theme_mode == 'light' else "☀️ Light Mode"
        if st.button(theme_label):
            st.session_state.theme_mode = 'light' if st.session_state.theme_mode == 'dark' else 'dark'
            st.rerun()
    
    # Apply theme CSS
    is_dark_mode = st.session_state.theme_mode == 'dark'
    st.markdown(generate_theme_css(is_dark_mode), unsafe_allow_html=True)
    
    st.title("🔍 YouTube Transcript Search")
    
    # Get available channels
    channels = get_cached_channels()
    
    if not channels:
        st.warning("No cached transcripts found. Please add transcript files to the 'transcripts_cache' directory.")
        return
    
    # Create channel options for selectbox
    channel_options = [f"{channel} ({count} videos)" for channel, count in channels.items()]
    
    # Channel selection
    selected_channel_option = st.selectbox(
        "Select a channel to search:",
        channel_options,
        index=0
    )
    
    # Extract channel name from selection
    selected_channel = selected_channel_option.split(' (')[0]
    
    # Search input
    search_term = st.text_input("🔍 Enter search term:", placeholder="e.g., 'artificial intelligence', 'climate change'")
    
    # Search button and results
    if st.button("Search", type="primary") or (search_term and len(search_term) > 2):
        if not search_term:
            st.warning("Please enter a search term.")
        else:
            with st.spinner(f"Searching in {selected_channel} videos..."):
                results = search_cached_transcripts(search_term, selected_channel)
            
            if results:
                st.success(f"Found {len(results)} videos with matches for '{search_term}'")
                
                for video_result in results:
                    video_id = video_result['video_id']
                    video_title = video_result['title']
                    matches = video_result['matches']
                    
                    # Calculate dynamic height based on number of matches
                    video_height = 315  # YouTube embed height
                    margin_height = 40  # Margins and padding
                    matches_height = len(matches) * 60  # Approximate height per match
                    padding_height = 20  # Extra padding
                    total_height = video_height + margin_height + matches_height + padding_height
                    
                    # Create HTML for embedded video with timestamp results
                    html_content = f"""
                    <div class="video-container">
                        <div class="video-title">{video_title}</div>
                        <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; background: #000;">
                            <iframe id="player_{video_id}" src="https://www.youtube.com/embed/{video_id}?enablejsapi=1&origin=https://share.streamlit.io" 
                                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" 
                                    frameborder="0" allow="autoplay; encrypted-media" allowfullscreen>
                            </iframe>
                        </div>
                        <div class="matches-container">
                            <div style="font-weight: bold; margin-bottom: 10px; color: {'#ffffff' if is_dark_mode else '#333333'};">
                                {len(matches)} matches found:
                            </div>
                    """
                    
                    # Add timestamp links
                    for match in matches:
                        timestamp_formatted = format_timestamp(match['timestamp'])
                        timestamp_seconds = int(float(match['timestamp']))
                        
                        html_content += f"""
                            <div class="timestamp-item">
                                <a href="javascript:void(0)" 
                                   onclick="document.getElementById('player_{video_id}').src='https://www.youtube.com/embed/{video_id}?start={timestamp_seconds}&autoplay=1'" 
                                   class="timestamp-link">{timestamp_formatted}</a>
                                <div class="timestamp-text">{match['text']}</div>
                            </div>
                        """
                    
                    html_content += """
                        </div>
                    </div>
                    """
                    
                    # Display the embedded video with results
                    components.html(html_content, height=total_height)
                    
            else:
                st.info(f"No results found for '{search_term}' in {selected_channel} videos.")

if __name__ == "__main__":
    main()
    