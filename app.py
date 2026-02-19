import os
import requests
import streamlit as st
from datetime import date
from pathlib import Path
from openai import OpenAI

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI News Briefing",
    page_icon="🎙️",
    layout="centered"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0f0f0f;
    color: #f0f0f0;
}

h1 {
    font-family: 'Playfair Display', serif;
    font-size: 2.8rem;
    color: #f0f0f0;
    letter-spacing: -1px;
}

.subtitle {
    color: #888;
    font-size: 1rem;
    margin-top: -12px;
    margin-bottom: 32px;
}

.stTextInput > div > div > input {
    background-color: #1a1a1a;
    color: #f0f0f0;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 1rem;
}

.stButton > button {
    background-color: #f0f0f0;
    color: #0f0f0f;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 10px 28px;
    font-size: 1rem;
    width: 100%;
    transition: opacity 0.2s;
}

.stButton > button:hover {
    opacity: 0.85;
}

.article-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

.article-num {
    color: #666;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.article-title {
    font-weight: 600;
    font-size: 0.95rem;
    margin: 4px 0;
    color: #f0f0f0;
}

.article-source {
    color: #888;
    font-size: 0.8rem;
}

.script-box {
    background: #1a1a1a;
    border-left: 3px solid #f0f0f0;
    border-radius: 0 8px 8px 0;
    padding: 20px 24px;
    font-size: 0.92rem;
    line-height: 1.8;
    color: #ccc;
    white-space: pre-wrap;
    margin: 16px 0;
}

.tip {
    color: #555;
    font-size: 0.82rem;
    margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Topic map ─────────────────────────────────────────────────────────────────
TOPIC_MAP = {
    'politics'     : ('', 'politics government election'),
    'political'    : ('', 'politics government election'),
    'world'        : ('general', ''),
    'technology'   : ('technology', ''),
    'tech'         : ('technology', ''),
    'science'      : ('science', ''),
    'business'     : ('business', ''),
    'economy'      : ('business', ''),
    'finance'      : ('business', ''),
    'health'       : ('health', ''),
    'medical'      : ('health', ''),
    'sports'       : ('sports', ''),
    'cricket'      : ('sports', ''),
    'football'     : ('sports', ''),
    'entertainment': ('entertainment', ''),
    'movies'       : ('entertainment', ''),
    'music'        : ('entertainment', ''),
}

VOICE = 'nova'

# ── Helper functions ──────────────────────────────────────────────────────────
def safe_str(value):
    return value if isinstance(value, str) else ''

def detect_topic(prompt):
    for keyword, (category, search) in TOPIC_MAP.items():
        if keyword in prompt.lower():
            return keyword, category, search
    return None, None, None

def fetch_articles(category, search_query, count=5):
    if search_query:
        url    = 'https://newsapi.org/v2/everything'
        params = {'q': search_query, 'language': 'en',
                  'sortBy': 'publishedAt', 'pageSize': count * 2}
    else:
        url    = 'https://newsapi.org/v2/top-headlines'
        params = {'category': category, 'language': 'en', 'pageSize': count * 2}

    params['apiKey'] = st.session_state.newsapi_key
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get('status') != 'ok':
        raise ValueError(f"NewsAPI error: {data.get('message')}")

    articles = []
    for a in data.get('articles', []):
        title       = safe_str(a.get('title'))
        description = safe_str(a.get('description'))
        content     = safe_str(a.get('content')) or description
        source      = safe_str(a.get('source', {}).get('name')) or 'Unknown'
        published   = safe_str(a.get('publishedAt'))[:10]

        if not title or '[Removed]' in title or '[Removed]' in description:
            continue

        articles.append({'title': title, 'description': description,
                         'content': content, 'source': source, 'published': published})

    return articles[:count]

def summarize_article(client, article):
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {
                'role': 'system',
                'content': (
                    'You are a professional news anchor. '
                    'Summarize the article in 2-3 conversational spoken sentences. '
                    'No bullet points. No markdown.'
                )
            },
            {
                'role': 'user',
                'content': (
                    f"Title: {article['title']}\n"
                    f"Description: {article['description']}\n"
                    f"Content: {article['content']}"
                )
            }
        ],
        max_tokens=150,
        temperature=0.5,
    )
    return resp.choices[0].message.content.strip()

def build_script(topic, summaries):
    today   = date.today().strftime('%B %d, %Y')
    intro   = (f"Good day! Welcome to your AI News Briefing for {today}. "
               f"Here is your summary of the top news in {topic.capitalize()}.")
    stories = '\n\n'.join(
        f"Story {i}: {s['title']}. Reported by {s['source']}. {s['summary']}"
        for i, s in enumerate(summaries, 1)
    )
    outro   = "That's your briefing for today. Stay informed, and have a great day!"
    return '\n\n'.join([intro, stories, outro])

def generate_audio(client, script, topic):
    output_file = f'briefing_{topic}.mp3'
    tts = client.audio.speech.create(model='tts-1', voice=VOICE, input=script)
    tts.stream_to_file(output_file)
    return output_file

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("<h1>🎙️ AI News Briefing</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Type a topic — get a spoken news briefing in seconds</p>",
            unsafe_allow_html=True)

# ── Sidebar: API keys ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API Keys")
    openai_key  = st.text_input("OpenAI API Key",  type="password", placeholder="sk-...")
    newsapi_key = st.text_input("NewsAPI Key",      type="password", placeholder="your key...")

    if openai_key:
        st.session_state.openai_key  = openai_key
    if newsapi_key:
        st.session_state.newsapi_key = newsapi_key

    st.markdown("---")
    st.markdown("**Get your keys:**")
    st.markdown("- [OpenAI API Key](https://platform.openai.com/api-keys)")
    st.markdown("- [NewsAPI Key](https://newsapi.org/register) *(free)*")
    st.markdown("---")
    st.markdown("**Supported topics:**")
    st.markdown("`politics` `tech` `business`  \n`health` `sports` `science`  \n`entertainment` `world`")

# ── Main input ────────────────────────────────────────────────────────────────
prompt = st.text_input(
    label="Your prompt",
    placeholder='e.g. "give me summary of top news in tech"',
    label_visibility="collapsed"
)
st.markdown("<p class='tip'>Try: \"give me top news in politics\" or \"what's happening in sports\"</p>",
            unsafe_allow_html=True)

run = st.button("🎙️ Generate Briefing")

# ── Pipeline ──────────────────────────────────────────────────────────────────
if run:
    # Validate keys
    if not st.session_state.get('openai_key') or not st.session_state.get('newsapi_key'):
        st.error("⛔ Please enter both API keys in the sidebar first.")
        st.stop()

    if not prompt.strip():
        st.error("⛔ Please enter a prompt.")
        st.stop()

    # Detect topic
    topic, category, search = detect_topic(prompt)
    if not topic:
        st.error(f"⚠️ Could not detect a topic from: \"{prompt}\"")
        st.info("Try keywords like: politics, tech, business, health, sports, science, entertainment")
        st.stop()

    client = OpenAI(api_key=st.session_state.openai_key)

    # Fetch
    with st.spinner(f"📡 Fetching {topic} headlines..."):
        try:
            articles = fetch_articles(category, search)
        except Exception as e:
            st.error(f"Failed to fetch news: {e}")
            st.stop()

    if not articles:
        st.warning("No articles found. Try a different topic.")
        st.stop()

    # Show articles
    st.markdown(f"### 📰 Top {len(articles)} Headlines — {topic.capitalize()}")
    for i, a in enumerate(articles, 1):
        st.markdown(f"""
        <div class='article-card'>
            <div class='article-num'>Story {i} · {a['published']}</div>
            <div class='article-title'>{a['title']}</div>
            <div class='article-source'>{a['source']}</div>
        </div>
        """, unsafe_allow_html=True)

    # Summarize
    with st.spinner("🤖 Summarizing with GPT..."):
        summaries = []
        progress  = st.progress(0)
        for i, a in enumerate(articles, 1):
            summaries.append({
                'title'  : a['title'],
                'source' : a['source'],
                'summary': summarize_article(client, a),
            })
            progress.progress(i / len(articles))
        progress.empty()

    # Build script
    script = build_script(topic, summaries)
    st.markdown("### 🎙️ Briefing Script")
    st.markdown(f"<div class='script-box'>{script}</div>", unsafe_allow_html=True)

    # Audio
    with st.spinner("🔊 Generating audio..."):
        try:
            audio_file = generate_audio(client, script, topic)
        except Exception as e:
            st.error(f"Audio generation failed: {e}")
            st.stop()

    st.markdown("### ▶️ Listen")
    st.audio(audio_file, format="audio/mp3")

    # Download button
    with open(audio_file, 'rb') as f:
        st.download_button(
            label="⬇️ Download MP3",
            data=f,
            file_name=f"briefing_{topic}.mp3",
            mime="audio/mp3"
        )
