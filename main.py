import os
import sys
import glob
import warnings
from dotenv import load_dotenv

# Suppress deprecation and tokenizers warnings for a clean interface
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# LangChain and Community imports
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# Load environment variables (.env contains GOOGLE_API_KEY)
load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "faiss_index")
EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"

# Gemini model configuration (default model configurable in .env)
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODEL = "gemini-3.8-flash" if PRIMARY_MODEL != "gemini-3.8-flash" else "gemini-3.5-flash-lite"


def load_documents(data_dir=DATA_DIR):
    """
    Step 1: Load documents from the data/ folder.
    Reads all .txt files using TextLoader and .pdf files using PyPDFLoader.
    """
    print(f"\n[Step 1] Loading documents from '{data_dir}'...")
    documents = []

    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found.")
        return documents

    files = sorted(os.listdir(data_dir))
    for file in files:
        file_path = os.path.join(data_dir, file)
        if file.lower().endswith(".txt"):
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata["source_name"] = file
                documents.extend(loaded)
                print(f"  - Loaded text file: {file}")
            except Exception as e:
                print(f"  ! Error loading {file}: {e}")
        elif file.lower().endswith(".pdf"):
            try:
                loader = PyPDFLoader(file_path)
                loaded = loader.load()
                for doc in loaded:
                    page_num = doc.metadata.get("page", 0) + 1
                    doc.metadata["source_name"] = f"{file} (Page {page_num})"
                documents.extend(loaded)
                print(f"  - Loaded PDF file: {file} ({len(loaded)} pages)")
            except Exception as e:
                print(f"  ! Error loading {file}: {e}")

    print(f"Total document objects loaded: {len(documents)}")
    return documents


def split_documents(documents):
    """
    Step 2: Split documents into overlapping chunks.
    Matches EXP-3 parameters (chunk_size=500, chunk_overlap=50).
    """
    print("\n[Step 2] Splitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)
    print(f"Number of chunks created: {len(chunks)}")
    return chunks


def get_embeddings():
    """
    Step 3: Create Google Generative AI Embeddings model.
    Ultra-lightweight (<40MB RAM), fast, and production-ready for 512MB environments.
    """
    print(f"\n[Step 3] Initializing embedding model ({EMBEDDING_MODEL_NAME})...")
    api_key = os.getenv("GOOGLE_API_KEY")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        google_api_key=api_key
    )
    return embeddings


def build_or_load_vectorstore(force_rebuild=False):
    """
    Step 4: Store in FAISS or reload from local disk if already cached.
    """
    embeddings = get_embeddings()

    if not force_rebuild and os.path.exists(INDEX_PATH):
        print(f"\n[Step 4] Loading cached FAISS vector store from '{INDEX_PATH}'...")
        try:
            vectorstore = FAISS.load_local(
                INDEX_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("Vector store loaded successfully from local disk cache.")
            return vectorstore
        except Exception as e:
            print(f"Could not load local index ({e}). Rebuilding...")

    print("\n[Step 4] Building FAISS vector store from data/ folder...")
    documents = load_documents(DATA_DIR)
    if not documents:
        raise RuntimeError("No documents found in data/ directory to index.")

    chunks = split_documents(documents)
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Save to local directory for instant restarts
    vectorstore.save_local(INDEX_PATH)
    print(f"FAISS vector store created and saved to '{INDEX_PATH}'.")
    return vectorstore


def get_llm(model_name=PRIMARY_MODEL):
    """
    Step 8: Calls Gemini to generate the answer.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\nWARNING: GOOGLE_API_KEY is not set in your .env file!")
        print("Please set GOOGLE_API_KEY=your_key in .env to call Gemini.")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        max_retries=1
    )


GREETINGS = {
    "hi", "hello", "hey", "hola", "namaste", "good morning", "good afternoon",
    "good evening", "howdy", "sup", "what's up", "whats up", "greetings"
}
COURTESIES = {
    "thanks", "thank you", "thank you so much", "thx", "bye", "goodbye", "see you", "cya"
}


def create_rag_chain(vectorstore):
    """
    Steps 6, 7 & 8: Build Retriever, Prompt, and RAG Chain.
    Retrieves top k=4 most relevant chunks to keep citations accurate and avoid noise.
    """
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    prompt = ChatPromptTemplate.from_template(
        """You are the official student assistance AI for Sri Vasavi Engineering College (Autonomous), Pedatadepalli, Tadepalligudem.

Core Guidelines:
1. Speak naturally, warmly, and authoritatively as the college assistant.
2. NEVER use robotic meta-phrases such as "based on the provided documents", "according to the context", "as stated in the documents", or "based on the provided text". Answer directly and professionally (for example: "At Sri Vasavi Engineering College, students must maintain a minimum of 75% attendance...").
3. Use the following verified college context to formulate your response:
{context}

4. If the context does not contain enough information to answer the question, politely say:
"I do not have verified records on that in the college documents. Please contact the SVEC administrative office or visit https://srivasaviengg.ac.in."
5. Format your answers clearly using bullet points and bold titles when describing courses, rules, or statistics.

Question: {question}

Answer:"""
    )

    llm = get_llm(PRIMARY_MODEL)
    chain = prompt | llm | StrOutputParser()
    return retriever, chain, prompt, llm


def answer_question(query, retriever, chain, prompt, llm):
    """
    Executes RAG pipeline for a given user question and returns response + sources.
    Handles greetings and courtesies cleanly without citing unnecessary source documents.
    """
    normalized = query.lower().strip().strip("!?.,")

    # Fast-path for greetings
    if normalized in GREETINGS or any(normalized.startswith(g + " ") for g in GREETINGS):
        greeting_reply = (
            "Hello! I am the official AI Assistant for **Sri Vasavi Engineering College (Autonomous)**.\n\n"
            "How can I assist you today? You can ask me about:\n"
            "• **Courses & Intake**: B.Tech and M.Tech specializations\n"
            "• **Attendance Rules**: Minimum criteria & condonation policies\n"
            "• **Exams & Regulations**: Semester exams, credit systems & grading\n"
            "• **Placements**: Top recruiters, highest packages & statistics\n"
            "• **Research & Faculty**: Patents, published papers & facilities"
        )
        return greeting_reply, [], []

    # Fast-path for courtesies and pleasantries
    if normalized in COURTESIES or any(normalized.startswith(c + " ") for c in COURTESIES):
        courtesy_reply = (
            "You're very welcome! If you have any further questions about Sri Vasavi Engineering College, "
            "feel free to ask. Have a great day!"
        )
        return courtesy_reply, [], []

    # Retrieve relevant document chunks
    retrieved_docs = retriever.invoke(query)

    if not retrieved_docs:
        return "I do not have verified records on that in the college documents. Please contact the SVEC administrative office or visit https://srivasaviengg.ac.in.", []

    # Combine context
    context = "\n\n".join(doc.page_content for doc in retrieved_docs)

    # Extract unique source names
    sources = []
    for doc in retrieved_docs:
        src = doc.metadata.get("source_name") or os.path.basename(doc.metadata.get("source", "Unknown"))
        if src not in sources:
            sources.append(src)

    try:
        response = chain.invoke({
            "context": context,
            "question": query
        })
    except Exception as e:
        error_msg = str(e)
        if any(keyword in error_msg for keyword in ("503", "UNAVAILABLE", "demand", "404", "NOT_FOUND")):
            print(f"\n[Notice] {PRIMARY_MODEL} returned a server status. Switching to {FALLBACK_MODEL}...")
            fallback_llm = get_llm(FALLBACK_MODEL)
            fallback_chain = prompt | fallback_llm | StrOutputParser()
            response = fallback_chain.invoke({
                "context": context,
                "question": query
            })
        else:
            raise e

    # If the response couldn't answer the question from records, omit sources
    if "do not have verified records" in response.lower() or "not available in the college" in response.lower():
        sources = []

    return response, sources, retrieved_docs


def main():
    print("=" * 65)
    print("      Sri Vasavi Engineering College (SVEC) FAQ Chatbot (RAG)")
    print("=" * 65)

    force_rebuild = "--rebuild" in sys.argv
    vectorstore = build_or_load_vectorstore(force_rebuild=force_rebuild)
    retriever, chain, prompt, llm = create_rag_chain(vectorstore)

    print("\nChatbot is ready! Ask any questions about SVEC (courses, attendance, exams, placements).")
    print("Type 'exit' or 'quit' to end the session.\n")

    # If run in non-interactive / batch mode with argument
    cli_args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if cli_args:
        query = " ".join(cli_args)
        print(f"Question: {query}")
        print("\nSearching SVEC knowledge base & generating response...")
        answer, sources, _ = answer_question(query, retriever, chain, prompt, llm)
        print("\n" + "-" * 50)
        print("ANSWER:")
        print(answer)
        if sources:
            print("\nSOURCES:")
            for src in sources:
                print(f"  • {src}")
        print("-" * 50)
        return

    # Interactive Loop
    while True:
        try:
            query = input("\nEnter your question: ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("Thank you for using SVEC FAQ Chatbot. Goodbye!")
                break

            print("\nSearching SVEC knowledge base & generating response...")
            answer, sources, _ = answer_question(query, retriever, chain, prompt, llm)

            print("\n" + "-" * 50)
            print("ANSWER:")
            print(answer)
            if sources:
                print("\nSOURCES:")
                for src in sources:
                    print(f"  • {src}")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\nSession ended. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    main()
