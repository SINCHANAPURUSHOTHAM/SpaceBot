"""
SpaceChat retrieval + generation
---------------------------------
Given a user question:
  1. Embed the question with the same model used at ingestion time.
  2. Similarity-search the Chroma store for the top-k most relevant chunks.
  3. Assemble those chunks (with citations) into a system prompt.
  4. Call Claude to answer using only that retrieved context.

Import `answer_question()` from app.py to wire this into the Streamlit UI.
"""

import os

import chromadb
from anthropic import Anthropic
from google import genai
from sentence_transformers import SentenceTransformer

CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "spacechat_docs"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CLAUDE_MODEL = "claude-sonnet-4-6"   # confirmed working in your test.py
GEMINI_MODEL = "gemini-flash-latest"  # Google keeps this alias pointed at their current stable Flash model
TOP_K = 5

_embedder = None
_collection = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
    return _embedder


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def retrieve_chunks(question, top_k=TOP_K):
    """Returns the top-k most relevant chunks with their metadata."""
    embedder = _get_embedder()
    collection = _get_collection()

    query_embedding = embedder.encode([question]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=top_k)

    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"text": doc, "metadata": meta})
    return chunks


def build_context_block(chunks):
    """Formats retrieved chunks into a labeled context block for the prompt."""
    parts = []
    for i, c in enumerate(chunks, start=1):
        m = c["metadata"]
        label = f"[Source {i}: {m['source']}, {m['chapter']}, p.{m['page']}]"
        parts.append(f"{label}\n{c['text']}")
    return "\n\n---\n\n".join(parts)


SYSTEM_PROMPT = (
    "You are SpaceChat, a research assistant answering questions about space "
    "science and technology using only the provided source excerpts. "
    "Cite the source number (e.g. 'Source 2') for every claim. "
    "If the excerpts don't contain the answer, say so plainly instead of guessing."
)


def answer_question(question, api_key, model=CLAUDE_MODEL, max_tokens=1000, temperature=0.3):
    """Full RAG call using Claude: retrieve -> build prompt -> ask Claude -> return answer + sources."""
    chunks = retrieve_chunks(question)
    context = build_context_block(chunks)

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Context:\n\n{context}\n\nQuestion: {question}"}
        ],
    )

    answer_text = response.content[0].text
    sources = [
        {"chapter": c["metadata"]["chapter"], "page": c["metadata"]["page"], "source": c["metadata"]["source"]}
        for c in chunks
    ]
    return answer_text, sources


def answer_question_gemini(question, api_key, model=GEMINI_MODEL, max_tokens=1000, temperature=0.3, top_k=TOP_K):
    """Full RAG call using Gemini's free-tier API instead of Claude."""
    chunks = retrieve_chunks(question, top_k=top_k)
    context = build_context_block(chunks)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=f"{SYSTEM_PROMPT}\n\nContext:\n\n{context}\n\nQuestion: {question}",
        config={"max_output_tokens": max_tokens, "temperature": temperature},
    )

    answer_text = response.text
    sources = [
        {"chapter": c["metadata"]["chapter"], "page": c["metadata"]["page"], "source": c["metadata"]["source"]}
        for c in chunks
    ]
    return answer_text, sources


if __name__ == "__main__":
    # quick manual smoke test — using Gemini's free tier
    from dotenv import load_dotenv
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    q = "What causes solar flares?"
    ans, srcs = answer_question_gemini(q, api_key=gemini_key)
    print("ANSWER:\n", ans)
    print("\nSOURCES:")
    for s in srcs:
        print(" -", s)