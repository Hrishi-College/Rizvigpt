from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from datetime import datetime
import uuid
import os

from llm_service import create_llm_service  # Updated import
from rag_service import RAGService
from db_service import DBService
from models.schemas import (
    ChatRequest, 
    ChatResponse, 
    IngestRequest, 
    IngestResponse,
    HealthResponse
)

# Initialize FastAPI
app = FastAPI(
    title="CollegeGPT API",
    description="AI-powered college assistant with RAG and Local LLM support",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
print("Initializing services...")
llm_service = create_llm_service()  # Auto-detects local or Groq
rag_service = RAGService()
db_service = DBService()
print("Services initialized!")

@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "CollegeGPT API with Local LLM Support",
        "version": "2.0.0",
        "model_type": "local" if llm_service.use_local_model else "groq",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check health of all services"""
    
    # Check which model is being used
    model_info = {
        "type": "local" if llm_service.use_local_model else "groq",
        "available": True
    }
    
    if llm_service.use_local_model:
        model_info["device"] = llm_service.device
        model_info["path"] = os.getenv("LOCAL_MODEL_PATH", "./trained_model/final_model")
    
    return HealthResponse(
        status="healthy",
        services={
            "llm": model_info.get("available", False),
            "llm_type": model_info.get("type", "unknown"),
            "rag": rag_service.vector_store is not None,
            "database": db_service.enabled
        },
        timestamp=datetime.utcnow()
    )

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """Main chat endpoint with RAG support"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        chat_history = db_service.get_conversation_history(session_id) if request.session_id else []
        
        context = None
        if request.use_rag:
            context = rag_service.get_context(request.query, k=3)
        
        # Generate response (automatically uses local or Groq based on config)
        response = llm_service.generate_response(
            query=request.query,
            context=context,
            chat_history=chat_history
        )
        
        db_service.save_conversation(
            session_id=session_id,
            user_message=request.query,
            bot_response=response,
            context_used=context
        )
        
        return ChatResponse(
            response=response,
            context_used=context if request.use_rag else None,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        chat_history = db_service.get_conversation_history(session_id) if request.session_id else []
        
        context = None
        if request.use_rag:
            context = rag_service.get_context(request.query, k=3)
        
        async def generate():
            full_response = ""
            for chunk in llm_service.generate_streaming_response(
                query=request.query,
                context=context,
                chat_history=chat_history
            ):
                full_response += chunk
                yield chunk
            
            # Save after streaming completes
            db_service.save_conversation(
                session_id=session_id,
                user_message=request.query,
                bot_response=full_response,
                context_used=context
            )
        
        return StreamingResponse(generate(), media_type="text/plain")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/switch-model", tags=["Admin"])
async def switch_model(use_local: bool):
    """
    Switch between local and Groq models
    Requires server restart in production
    """
    try:
        global llm_service
        
        local_model_path = os.getenv("LOCAL_MODEL_PATH", "./trained_model/final_model")
        
        if use_local and not os.path.exists(local_model_path):
            raise HTTPException(
                status_code=400, 
                detail=f"Local model not found at {local_model_path}"
            )
        
        llm_service = create_llm_service()
        
        return {
            "status": "success",
            "message": f"Switched to {'local' if use_local else 'groq'} model",
            "model_type": "local" if llm_service.use_local_model else "groq"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", response_model=IngestResponse, tags=["Admin"])
async def ingest_documents(request: IngestRequest):
    """Ingest documents into vector database"""
    try:
        data_path = request.data_path or "./data"
        
        doc_count = 0
        if os.path.exists(data_path):
            doc_count = len([f for f in os.listdir(data_path) if f.endswith('.pdf')])
        
        rag_service.ingest_documents(data_path)
        
        return IngestResponse(
            status="success",
            message=f"Documents ingested successfully from {data_path}",
            documents_processed=doc_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/vector-store", tags=["Admin"])
async def clear_vector_store():
    """Clear all documents from vector store"""
    try:
        rag_service.clear_vector_store()
        return {"status": "success", "message": "Vector store cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions", tags=["Admin"])
async def get_sessions():
    """Get all conversation sessions"""
    try:
        sessions = db_service.get_all_sessions()
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}", tags=["Admin"])
async def clear_session(session_id: str):
    """Clear conversation history for a session"""
    try:
        success = db_service.clear_session(session_id)
        if success:
            return {"status": "success", "message": f"Session {session_id} cleared"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", tags=["Search"])
async def search_documents(query: str, k: int = 3):
    """Search documents without generating response"""
    try:
        results = rag_service.search(query, k=k)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model-info", tags=["Info"])
async def get_model_info():
    """Get information about the current model"""
    info = {
        "model_type": "local" if llm_service.use_local_model else "groq",
        "status": "active"
    }
    
    if llm_service.use_local_model:
        info["device"] = llm_service.device
        info["model_path"] = os.getenv("LOCAL_MODEL_PATH", "./trained_model/final_model")
    else:
        info["model_name"] = llm_service.model
    
    return info

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="localhost", port=port, reload=True)