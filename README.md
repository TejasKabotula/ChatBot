# Sri Vasavi Engineering College (SVEC) - FAQ Chatbot (RAG)

An intelligent AI-powered FAQ chatbot for **Sri Vasavi Engineering College (Autonomous)**, Tadepalligudem. Built with **Retrieval-Augmented Generation (RAG)** using **LangChain**, **FAISS**, **HuggingFace Embeddings**, **Google Gemini**, and a **FastAPI** web interface.

---

## Features
- **Grounded AI Answers**: Grounded strictly in official college documents (attendance policies, B.Tech/M.Tech courses, examination rules, placements, and research dossier).
- **No Hallucinations**: Politely states if verified information is not found in the documents.
- **Source Verification**: Every response displays the exact source files and PDF page numbers consulted.
- **Modern Clean UI**: Designed with collegiate navy tones, organic pill shapes, responsive mobile support, and the official SVEC emblem.
- **Fast Local Indexing**: FAISS index is cached locally for instant startup.

---

## Project Structure
```text
SVEC-RAG-Chatbot/
├── data/                       # Verified college documents (.txt + .pdf)
│   ├── attendance.txt
│   ├── courses.txt
│   ├── exams.txt
│   ├── placements.txt
│   └── svec_research_dossier.pdf
├── static/                     # Web Frontend
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── logo.png
├── app.py                      # FastAPI Web Server
├── main.py                     # Core RAG Pipeline & CLI Chatbot
├── requirements.txt            # Python Dependencies
├── Procfile                    # Cloud Process File
├── render.yaml                 # Render 1-Click Blueprint
├── Dockerfile                  # Container Deployment
└── .gitignore
```

---

## Quick Start (Local Run)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Tejaskumar001/ChatBot.git
   cd ChatBot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.5-flash-lite
   ```

4. **Run the FastAPI Web App**:
   ```bash
   python -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```
   Open `http://localhost:8000` in your browser.

5. **Run via Terminal (CLI Mode)**:
   ```bash
   python main.py
   ```

---

## Cloud Deployment Guide

### Option 1: Deploy to Render (Recommended - Free Tier)

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Deploy SVEC FAQ Chatbot"
   git push origin main
   ```

2. Go to **[Render.com](https://render.com)** and sign in with GitHub.
3. Click **New +** &rarr; **Web Service**.
4. Connect your repository: `Tejaskumar001/ChatBot`.
5. Configure the service:
   - **Name**: `svec-faq-chatbot`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
6. Scroll down to **Environment Variables** and add:
   - `GOOGLE_API_KEY`: `<Your Gemini API Key>`
   - `GEMINI_MODEL`: `gemini-3.5-flash-lite`
   - `PYTHON_VERSION`: `3.11.9`
7. Click **Create Web Service**. Your chatbot will be live with a free `https://...onrender.com` URL!

---

### Option 2: Deploy to Railway

1. Go to **[Railway.app](https://railway.app)** and sign in with GitHub.
2. Click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select `Tejaskumar001/ChatBot`.
4. In **Variables**, add:
   - `GOOGLE_API_KEY`: `<Your Gemini API Key>`
   - `GEMINI_MODEL`: `gemini-3.5-flash-lite`
5. Railway will automatically detect the `Procfile` / `Dockerfile` and deploy your app.
6. Under the service settings, click **Generate Domain** to get your public HTTPS URL.
