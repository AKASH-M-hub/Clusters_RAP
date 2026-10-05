from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from pdf_service import pdf_store
from agent_orchestrator import run_agent

app = FastAPI(title="Budgeted Agent API")

# Setup CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    try:
        pdf_store.load_pdf(file_path, doc_id)
        return {"doc_id": doc_id, "filename": file.filename, "pages": len(pdf_store.doc)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.post("/chat")
async def chat(doc_id: str = Form(...), question: str = Form(...)):
    if pdf_store.doc_id != doc_id:
        raise HTTPException(status_code=404, detail="Document not loaded or ID mismatch. Please upload again.")
        
    # Run the agent using qwen2.5:3b via local Ollama
    result = run_agent(question, doc_id, model='qwen2.5:3b')
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
