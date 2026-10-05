# Budgeted AI Agent (5-Call Max)

An ultra-efficient, locally-hosted Agentic RAG system designed specifically for tiny LLMs (like `qwen2.5:3b` via Ollama). 

This project solves the "context window overload" and "premature termination" problems of small models by implementing a rigid **5-Tool Call Budget** and an advanced Python backend capable of auto-correcting the LLM's mistakes.

## 🚀 Key Hackathon Features

1. **Multi-Keyword Intersection Engine:** 
   Instead of searching for a single generic word (like "elections" which might return 20 pages and blow the budget), the LLM extracts an array of specific keywords. The backend instantly finds the intersection of pages containing *all* keywords, narrowing the results down to 1 or 2 pages.
   
2. **NLTK Synonym Expansion (The "Synonym Trap"):**
   If the LLM searches for a word that doesn't exist in the PDF (e.g., "stealing"), the backend uses `nltk.corpus.wordnet` to automatically expand the word into synonyms (e.g., "theft"). It searches for all synonyms simultaneously and returns the correct page without the LLM ever knowing it made a mistake.

3. **Built-in Auto-Spellchecker:**
   When a PDF is uploaded, the backend builds a dynamic vocabulary RAM map. If the LLM passes a misspelled keyword (e.g., "absentism"), the backend uses Python's native `difflib` to auto-correct it to the closest valid word in the PDF ("absenteeism") *before* running the search.

4. **Transparent JSON Tracing:**
   Every tool call, argument, and fallback action is perfectly logged in a live UI trace panel, and saved to a `trace_history.json` file for auditing and evaluation.

## 🛠️ Tech Stack
* **LLM Engine:** Ollama (`qwen2.5:3b`)
* **Backend:** FastAPI, Python, PyMuPDF (`fitz`), NLTK, Difflib
* **Frontend:** React, Vite, TypeScript

## ⚙️ How to Run

### 1. Start the Backend
```bash
cd budget_agent/backend
pip install -r requirements.txt
python main.py
```

### 2. Start the Frontend
Open a new terminal window:
```bash
cd budget_agent/frontend
npm install
npm run dev
```

### 3. Open the App
Navigate to `http://localhost:5173` in your browser. Upload a PDF and test the 5-Call Orchestrator!
