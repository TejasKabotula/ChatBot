import os
import sys

# Configure single-thread limits to prevent memory bloat on 512MB containers
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from main import build_or_load_vectorstore, create_rag_chain, answer_question

# Global state for RAG pipeline
rag_state = {
    "vectorstore": None,
    "retriever": None,
    "chain": None,
    "prompt": None,
    "llm": None,
    "ready": False
}


def init_rag_system():
    if rag_state["ready"]:
        return True

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("WARNING: GOOGLE_API_KEY is not set in environment variables.")
        return False

    try:
        if not rag_state["vectorstore"]:
            rag_state["vectorstore"] = build_or_load_vectorstore(force_rebuild=False)
        retriever, chain, prompt, llm = create_rag_chain(rag_state["vectorstore"])
        rag_state["retriever"] = retriever
        rag_state["chain"] = chain
        rag_state["prompt"] = prompt
        rag_state["llm"] = llm
        rag_state["ready"] = True
        print("SVEC FAQ Chatbot RAG Pipeline ready!")
        return True
    except Exception as e:
        print(f"Error initializing RAG pipeline: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize RAG vector store and pipeline at startup
    print("Initializing SVEC FAQ Chatbot RAG Pipeline for FastAPI...")
    try:
        # Pre-load vector store cache
        rag_state["vectorstore"] = build_or_load_vectorstore(force_rebuild=False)
        init_rag_system()
    except Exception as e:
        print(f"Startup notice: {e}")
    yield


app = FastAPI(
    title="Sri Vasavi Engineering College (SVEC) FAQ Chatbot",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy" if rag_state["ready"] else "pending_key" if not os.getenv("GOOGLE_API_KEY") else "loading",
        "college": "Sri Vasavi Engineering College (Autonomous)",
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "has_api_key": bool(os.getenv("GOOGLE_API_KEY"))
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if not rag_state["ready"]:
        init_rag_system()

    if not rag_state["ready"]:
        if not os.getenv("GOOGLE_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_API_KEY is not configured in Render. Please add your Gemini API key in the Render Dashboard (Environment tab)."
            )
        raise HTTPException(status_code=503, detail="RAG system is still loading documents. Please try again shortly.")

    try:
        answer, sources, _ = answer_question(
            query=query,
            retriever=rag_state["retriever"],
            chain=rag_state["chain"],
            prompt=rag_state["prompt"],
            llm=rag_state["llm"]
        )
        return ChatResponse(answer=answer, sources=sources)
    except Exception as e:
        print(f"Error answering query '{query}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve static frontend files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.api_route("/", methods=["GET", "HEAD"])
def serve_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SVEC FAQ Bot API is running. Place index.html in the static/ folder."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting SVEC FAQ Chatbot server on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=False)
