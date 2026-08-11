import streamlit as st
import os
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
# Design system
# ---------------------------------------------------------------------------
# Palette:
#   --void        #0A0E1A   deep space background
#   --panel       #121A2E   sidebar / card surface
#   --panel-line  #223055   hairline borders on panels
#   --signal-amber#FFB454   primary accent — sunlight / active state
#   --signal-teal #4FD8C4   secondary accent — telemetry readouts
#   --text-main   #E8ECF4   primary text
#   --text-muted  #8B99B8   secondary / caption text
#
# Type:
#   Display  -> Space Grotesk (geometric, literal "space" pun, used sparingly)
#   Body     -> IBM Plex Sans (clean, readable)
#   Mono     -> IBM Plex Mono (telemetry data: page numbers, citations, stats)
#
# Signature element: a "telemetry strip" under the hero showing live-looking
# mission stats, plus a pure-CSS starfield (no external image = no licensing
# risk, and it can actually twinkle).

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --void: #0A0E1A;
        --panel: #121A2E;
        --panel-line: #223055;
        --signal-amber: #FFB454;
        --signal-teal: #4FD8C4;
        --text-main: #E8ECF4;
        --text-muted: #8B99B8;
    }

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
        color: var(--text-main);
    }

    /* ---------------- Starfield background (pure CSS, no image assets) --- */
    .stApp {
        background: var(--void);
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
            radial-gradient(2px 2px at 60% 20%, var(--signal-amber) 100%, transparent);
        background-repeat: repeat;
        background-size: 600px 600px;
        animation: drift 90s linear infinite;
    }

    @keyframes drift {
        from { background-position: 0 0; }
        to   { background-position: -600px 300px; }
    }

    /* ---------------- Sidebar ("Mission Control") ------------------------- */
    section[data-testid="stSidebar"] {
        background-color: var(--panel);
        border-right: 1px solid var(--panel-line);
    }
    .eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.15em;
        color: var(--signal-teal);
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }

    /* ---------------- Hero ------------------------------------------------ */
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        text-align: center;
        color: var(--text-main);
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
    }
    .hero-title .accent { color: var(--signal-amber); }
    .hero-subtitle {
        text-align: center;
        color: var(--text-muted);
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }

    /* ---------------- Telemetry strip -------------------------------------- */
    .telemetry-strip {
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
    }
    .telemetry-strip span.val { color: var(--signal-teal); font-weight: 500; }

    /* ---------------- Sample question chips -------------------------------- */
    div[data-testid="stButton"] > button {
        background: var(--panel);
        border: 1px solid var(--panel-line);
        color: var(--text-main);
        border-radius: 8px;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.85rem;
        text-align: left;
        padding: 0.6rem 0.9rem;
        transition: border-color 0.15s ease;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: var(--signal-amber);
        color: var(--signal-amber);
    }

    /* ---------------- Status badges ---------------------------------------- */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        margin-top: 5px;
    }
    .status-active {
        background-color: rgba(79, 216, 196, 0.12);
        color: var(--signal-teal);
        border: 1px solid rgba(79, 216, 196, 0.35);
    }
    .status-inactive {
        background-color: rgba(255, 100, 100, 0.1);
        color: #ff6464;
        border: 1px solid rgba(255, 100, 100, 0.3);
    }

    /* ---------------- Citation footer inside chat answers ------------------ */
    .citation-block {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
        border-left: 2px solid var(--signal-amber);
        padding-left: 0.6rem;
        margin-top: 0.5rem;
    }
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
st.sidebar.markdown("<div class='eyebrow'>QUICK.LAUNCH</div>", unsafe_allow_html=True)
st.sidebar.markdown("### 🚀 Explore by Topic")

topic_prompts = {
    "🇮🇳 Indian Space Tech": "What are the key milestones of India's space program?",
    "🌕 Moon Exploration": "What have we learned about the Moon's formation and surface?",
    "🔴 Mars": "What do we currently know about the surface and atmosphere of Mars?",
    "🛰️ Satellites": "How do satellites stay in orbit around Earth?",
}
for label, question in topic_prompts.items():
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.queued_prompt = question
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
# Sample questions (shown when chat is empty)
# ---------------------------------------------------------------------------
SAMPLE_QUESTIONS = [
    "What causes solar flares?",
    "How do black holes form?",
    "Why does Mars appear red?",
    "What is the life cycle of a star?",
    "How do we detect exoplanets?",
    "What causes the phases of the Moon?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "queued_prompt" not in st.session_state:
    st.session_state.queued_prompt = None

if not st.session_state.messages:
    st.markdown("<div class='eyebrow' style='text-align:center;'>SUGGESTED QUERIES</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, q in enumerate(SAMPLE_QUESTIONS):
        if cols[i % 3].button(q, key=f"sample_{i}", use_container_width=True):
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