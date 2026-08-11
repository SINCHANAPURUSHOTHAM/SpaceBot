import streamlit as st
import os
import base64
import random
from dotenv import load_dotenv

from retrieve import answer_question_gemini

# Load environment variables from .env
load_dotenv()

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SpaceBot | Mission Control for Space Knowledge",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Topic registry
# ---------------------------------------------------------------------------
# Each topic has:
#   - label / emoji for the sidebar button
#   - a fallback gradient (used until you drop a real image in assets/)
#   - an asset filename to look for in ./assets/ (jpg or png, either works)
#   - a set of sample questions tailored to that topic
#
# TO ADD YOUR OWN IMAGES: create an "assets" folder next to app.py and drop in
# files named exactly as listed below (e.g. assets/sun.jpg). The app auto-
# detects them and switches the background — no code changes needed.
ASSET_DIR = "assets"

TOPICS = {
    "home": {
        "label": "🏠 Home",
        "asset": "home",
        "fallback_gradient": "radial-gradient(ellipse at 50% 0%, #1a2547 0%, #0A0E1A 60%)",
        "sample_questions": [
            "What causes solar flares?",
            "How do black holes form?",
            "Why does Mars appear red?",
            "What is the life cycle of a star?",
            "How do we detect exoplanets?",
            "What causes the phases of the Moon?",
        ],
    },
    "sun": {
        "label": "☀️ The Sun",
        "asset": "sun",
        "fallback_gradient": "radial-gradient(ellipse at 50% 30%, #3d2410 0%, #1a0f05 45%, #0A0E1A 80%)",
        "sample_questions": [
            "What causes solar flares?",
            "What is inside the Sun's core?",
            "What is the solar wind?",
            "Why do sunspots appear dark?",
            "What will happen to the Sun in the future?",
            "How does nuclear fusion power the Sun?",
        ],
    },
    "moon": {
        "label": "🌕 The Moon",
        "asset": "moon",
        "fallback_gradient": "radial-gradient(ellipse at 50% 30%, #2a2f42 0%, #14182a 45%, #0A0E1A 80%)",
        "sample_questions": [
            "What causes the phases of the Moon?",
            "How did the Moon form?",
            "Why do we only see one side of the Moon?",
            "What causes tides on Earth?",
            "What are lunar maria?",
            "Is there water on the Moon?",
        ],
    },
    "mars": {
        "label": "🔴 Mars",
        "asset": "mars",
        "fallback_gradient": "radial-gradient(ellipse at 50% 30%, #3d1a10 0%, #1f0d08 45%, #0A0E1A 80%)",
        "sample_questions": [
            "Why does Mars appear red?",
            "What is the atmosphere of Mars made of?",
            "Is there evidence of water on Mars?",
            "What are Phobos and Deimos?",
            "What is the climate like on Mars?",
            "Could Mars have supported life?",
        ],
    },
    "satellites": {
        "label": "🛰️ Satellites",
        "asset": "satellites",
        "fallback_gradient": "radial-gradient(ellipse at 50% 30%, #10303d 0%, #081a1f 45%, #0A0E1A 80%)",
        "sample_questions": [
            "How do satellites stay in orbit around Earth?",
            "What's the difference between LEO and geostationary orbit?",
            "How does satellite communication work?",
            "What is space debris and why does it matter?",
            "How does GPS use satellites to find location?",
            "What keeps a satellite from falling back to Earth?",
        ],
    },
    "missions": {
        "label": "🚀 Space Missions",
        "asset": "missions",
        "fallback_gradient": "radial-gradient(ellipse at 50% 30%, #2a1a3d 0%, #150d1f 45%, #0A0E1A 80%)",
        "sample_questions": [
            "What was the significance of the Apollo missions?",
            "How do space telescopes like Hubble work?",
            "What have Voyager 1 and 2 discovered?",
            "How does the International Space Station stay in orbit?",
            "What is the purpose of Mars rover missions?",
            "How do scientists plan interplanetary missions?",
        ],
    },
    "indian_space": {
        "label": "🇮🇳 Indian Space Tech",
        "asset": "indian_space",
        "fallback_gradient": "radial-gradient(ellipse at 50% 30%, #1a3d1f 0%, #0d1f10 45%, #0A0E1A 80%)",
        "sample_questions": [
            "What are the key milestones of India's space program?",
            "What is the Chandrayaan mission?",
            "What is the PSLV and what does it do?",
            "What is the Gaganyaan mission?",
            "How does NISAR combine NASA and ISRO technology?",
            "What communication satellites has India launched?",
        ],
    },
}


@st.cache_data
def get_topic_background_css(topic_key):
    """
    Returns a CSS background-image declaration for a topic.
    If a real image exists in assets/<topic>.jpg or .png, it's base64-embedded
    and used directly. Otherwise falls back to the topic's themed gradient
    layered under the starfield, so the app looks complete before real
    images are added.
    """
    topic = TOPICS[topic_key]
    for ext in ("jpg", "jpeg", "png"):
        path = os.path.join(ASSET_DIR, f"{topic['asset']}.{ext}")
        if os.path.exists(path):
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            mime = "jpeg" if ext in ("jpg", "jpeg") else "png"
            # Dark overlay gradient on top of the real photo keeps text readable
            return (
                f"linear-gradient(180deg, rgba(10,14,26,0.75) 0%, rgba(10,14,26,0.92) 100%), "
                f"url(data:image/{mime};base64,{encoded})"
            )
    return topic["fallback_gradient"]


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "queued_prompt" not in st.session_state:
    st.session_state.queued_prompt = None
if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = "home"

current_topic = TOPICS[st.session_state.selected_topic]
background_css = get_topic_background_css(st.session_state.selected_topic)

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {{
        --void: #0A0E1A;
        --panel: #121A2E;
        --panel-line: #223055;
        --signal-amber: #FFB454;
        --signal-teal: #4FD8C4;
        --text-main: #E8ECF4;
        --text-muted: #8B99B8;
    }}

    html, body, [class*="css"] {{
        font-family: 'IBM Plex Sans', sans-serif;
        color: var(--text-main);
    }}

    /* ---------------- Dynamic topic background --------------------------- */
    .stApp {{
        background-color: var(--void);
        background-image:
            radial-gradient(1px 1px at 20% 30%, #ffffff 100%, transparent),
            radial-gradient(1px 1px at 75% 15%, #ffffff 100%, transparent),
            radial-gradient(1.5px 1.5px at 50% 60%, #ffffff 100%, transparent),
            radial-gradient(1px 1px at 90% 80%, #ffffff 100%, transparent),
            radial-gradient(1px 1px at 10% 85%, #ffffff 100%, transparent),
            radial-gradient(1.5px 1.5px at 35% 45%, #ffffff 100%, transparent),
            radial-gradient(1px 1px at 65% 90%, #ffffff 100%, transparent),
            radial-gradient(1px 1px at 85% 40%, #ffffff 100%, transparent),
            radial-gradient(2px 2px at 15% 55%, var(--signal-teal) 100%, transparent),
            radial-gradient(2px 2px at 60% 20%, var(--signal-amber) 100%, transparent),
            {background_css};
        background-repeat: repeat, repeat, repeat, repeat, repeat, repeat, repeat, repeat, repeat, repeat, no-repeat;
        background-size: 600px 600px, 600px 600px, 600px 600px, 600px 600px, 600px 600px, 600px 600px, 600px 600px, 600px 600px, 600px 600px, 600px 600px, cover;
        background-position: 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, center;
        background-attachment: scroll, scroll, scroll, scroll, scroll, scroll, scroll, scroll, scroll, scroll, fixed;
        transition: background-image 0.6s ease;
    }}

    /* ---------------- Sidebar ("Mission Control") ------------------------- */
    section[data-testid="stSidebar"] {{
        background-color: var(--panel);
        border-right: 1px solid var(--panel-line);
    }}
    .eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.15em;
        color: var(--signal-teal);
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }}

    /* ---------------- Hero ------------------------------------------------ */
    .hero-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        text-align: center;
        color: var(--text-main);
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
    }}
    .hero-title .accent {{ color: var(--signal-amber); }}
    .hero-subtitle {{
        text-align: center;
        color: var(--text-muted);
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }}
    .topic-pill {{
        display: block;
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--signal-amber);
        margin-bottom: 0.6rem;
    }}

    /* ---------------- Telemetry strip -------------------------------------- */
    .telemetry-strip {{
        display: flex;
        justify-content: center;
        gap: 2.5rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: var(--text-muted);
        border-top: 1px solid var(--panel-line);
        border-bottom: 1px solid var(--panel-line);
        padding: 0.6rem 0;
        margin-bottom: 1.8rem;
        background: rgba(10, 14, 26, 0.55);
        backdrop-filter: blur(4px);
    }}
    .telemetry-strip span.val {{ color: var(--signal-teal); font-weight: 500; }}

    /* ---------------- Sample question chips -------------------------------- */
    div[data-testid="stButton"] > button {{
        background: rgba(18, 26, 46, 0.85);
        border: 1px solid var(--panel-line);
        color: var(--text-main);
        border-radius: 8px;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.85rem;
        text-align: left;
        padding: 0.6rem 0.9rem;
        transition: border-color 0.15s ease;
        backdrop-filter: blur(4px);
    }}
    div[data-testid="stButton"] > button:hover {{
        border-color: var(--signal-amber);
        color: var(--signal-amber);
    }}

    /* Active topic button in the sidebar gets a highlighted border */
    div[data-testid="stSidebar"] div[data-testid="stButton"].active-topic > button {{
        border-color: var(--signal-amber);
        color: var(--signal-amber);
    }}

    /* ---------------- Status badges ---------------------------------------- */
    .status-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        margin-top: 5px;
    }}
    .status-active {{
        background-color: rgba(79, 216, 196, 0.12);
        color: var(--signal-teal);
        border: 1px solid rgba(79, 216, 196, 0.35);
    }}
    .status-inactive {{
        background-color: rgba(255, 100, 100, 0.1);
        color: #ff6464;
        border: 1px solid rgba(255, 100, 100, 0.3);
    }}

    /* ---------------- Citation footer inside chat answers ------------------ */
    .citation-block {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
        border-left: 2px solid var(--signal-amber);
        padding-left: 0.6rem;
        margin-top: 0.5rem;
    }}

    /* Chat message bubbles get a translucent panel so they read over any bg */
    div[data-testid="stChatMessage"] {{
        background: rgba(18, 26, 46, 0.75);
        backdrop-filter: blur(6px);
        border-radius: 10px;
        border: 1px solid var(--panel-line);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------------
# Sidebar — "Mission Control"
# ---------------------------------------------------------------------------
st.sidebar.markdown("<div class='eyebrow'>SYS.CONFIG</div>", unsafe_allow_html=True)
st.sidebar.markdown("### 🛠️ Configuration")

env_key = os.getenv("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    value=env_key,
    placeholder="Paste your Gemini API key here",
    help="Free tier key from aistudio.google.com/apikey. Loaded from .env if available."
)

if api_key:
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "Loaded"
    st.sidebar.markdown(
        f"<div class='status-badge status-active'>KEY ACTIVE ({masked_key})</div>",
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        "<div class='status-badge status-inactive'>NO API KEY FOUND</div>",
        unsafe_allow_html=True
    )

st.sidebar.markdown("---")
st.sidebar.markdown("<div class='eyebrow'>MODEL.PARAMS</div>", unsafe_allow_html=True)
st.sidebar.markdown("### 🤖 Model Settings")

with st.sidebar.expander("⚙️ Advanced Parameters"):
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1,
                             help="Lower = more grounded in the source text. Higher = more creative phrasing.")
    max_tokens = st.slider("Max Tokens", 200, 2000, 1000, 100)
    top_k = st.slider("Chunks Retrieved (top-k)", 1, 10, 5, 1,
                       help="How many book excerpts to pull in per question.")

st.sidebar.markdown("---")
st.sidebar.markdown("<div class='eyebrow'>TOPIC.SELECT</div>", unsafe_allow_html=True)
st.sidebar.markdown("### 🧭 Browse by Topic")

for topic_key, topic in TOPICS.items():
    if st.sidebar.button(topic["label"], use_container_width=True, key=f"topic_{topic_key}"):
        st.session_state.selected_topic = topic_key
        st.session_state.queued_prompt = None
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Clear Chat History", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown("<div class='hero-title'>Space<span class='accent'>Bot</span></div>", unsafe_allow_html=True)
st.markdown(
    "<div class='hero-subtitle'>Ask anything about space science — every answer is grounded and cited from the source text.</div>",
    unsafe_allow_html=True
)
if st.session_state.selected_topic != "home":
    st.markdown(f"<div class='topic-pill'>▸ Exploring: {current_topic['label']}</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="telemetry-strip">
        <div>SOURCE <span class="val">Astronomy 2e (OpenStax)</span></div>
        <div>MODEL <span class="val">Gemini Flash</span></div>
        <div>MODE <span class="val">Retrieval-Augmented</span></div>
        <div>STATUS <span class="val">Nominal</span></div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------------
# Sample questions — dynamically follows the selected topic
# ---------------------------------------------------------------------------
st.markdown(
    f"<div class='eyebrow' style='text-align:center;'>SUGGESTED QUERIES — {current_topic['label'].split(' ', 1)[1].upper()}</div>",
    unsafe_allow_html=True
)
cols = st.columns(3)
for i, q in enumerate(current_topic["sample_questions"]):
    if cols[i % 3].button(q, key=f"sample_{st.session_state.selected_topic}_{i}", use_container_width=True):
        st.session_state.queued_prompt = q
        st.rerun()
st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("sources"):
            citation_lines = "<br>".join(
                f"[{i+1}] {s['source']} — p.{s['page']}"
                for i, s in enumerate(message["sources"])
            )
            st.markdown(f"<div class='citation-block'>{citation_lines}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Input handling — either a typed message or a queued sample/topic question
# ---------------------------------------------------------------------------
typed_prompt = st.chat_input("Ask SpaceBot anything about space science...")
prompt = st.session_state.queued_prompt or typed_prompt
st.session_state.queued_prompt = None  # consume it so it doesn't re-fire

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        if not api_key:
            message_placeholder.error(
                "API key missing! Add your Gemini API key in the sidebar or your .env file."
            )
        else:
            try:
                with st.spinner("Scanning the archive..."):
                    answer_text, sources = answer_question_gemini(
                        prompt,
                        api_key=api_key,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_k=top_k,
                    )
                message_placeholder.markdown(answer_text)
                citation_lines = "<br>".join(
                    f"[{i+1}] {s['source']} — p.{s['page']}"
                    for i, s in enumerate(sources)
                )
                st.markdown(f"<div class='citation-block'>{citation_lines}</div>", unsafe_allow_html=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer_text,
                    "sources": sources,
                })
            except Exception as e:
                message_placeholder.error(f"**An error occurred**: {e}")