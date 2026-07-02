from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
import database as db
import rag_engine as rag
from pydantic import BaseModel

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
# We need to make sure the directories exist. They should since we created them for Flask.
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Background processing state
processing_status = {"is_processing": False, "message": "Boşta"}

# Initialize RAG at startup
@app.on_event("startup")
async def startup_event():
    rag.init_rag()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/history")
async def get_history():
    sessions = db.get_sessions()
    return {"sessions": sessions}

@app.get("/history/{session_id}")
async def get_session_messages(session_id: str):
    messages = db.get_messages(session_id)
    return {"messages": messages}

@app.post("/new_session")
async def create_session():
    session_id = db.create_session()
    return {"session_id": session_id}

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id
    message = req.message
    
    if not session_id:
        return {"error": "Session ID gerekli"}
    if not message:
        return {"error": "Mesaj gerekli"}
        
    # Save user message
    db.add_message(session_id, "user", message)
    
    # Get answer from RAG
    answer = rag.ask_question(message)
    
    # Save bot message
    db.add_message(session_id, "bot", answer)
    
    # Auto-update session title based on the first question
    messages = db.get_messages(session_id)
    if len(messages) <= 2: # 1 user, 1 bot
        title = message[:30] + "..." if len(message) > 30 else message
        db.update_session_title(session_id, title)
    
    return {"response": answer}

def _background_process_pdfs():
    global processing_status
    try:
        processing_status["is_processing"] = True
        processing_status["message"] = "PDF'ler okunuyor ve vektörlere dönüştürülüyor. Lütfen bekleyin..."
        rag.process_pdfs()
        processing_status["message"] = "İşlem başarıyla tamamlandı."
    except Exception as e:
        processing_status["message"] = f"Hata: {str(e)}"
    finally:
        processing_status["is_processing"] = False

@app.post("/process_pdfs")
async def process_pdfs(background_tasks: BackgroundTasks):
    global processing_status
    if processing_status["is_processing"]:
        return {"status": "already_processing", "message": "Şu anda zaten bir işlem yürütülüyor."}
    
    # Start processing in a background thread to avoid blocking the API
    background_tasks.add_task(_background_process_pdfs)
    
    return {"status": "started", "message": "PDF işleme başlatıldı."}

@app.get("/process_status")
async def get_process_status():
    global processing_status
    return processing_status