# RizviGPT Backend Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Add College Documents

Create a `data` folder in the root directory and add PDF documents:

```bash
mkdir -p data
# Copy your college PDFs, syllabus, handbooks, etc. to data/
```

### 3. Run the Backend

```bash
cd backend
python app.py
```

The API will start at `http://localhost:8000`

### 4. Ingest Documents (First Time)

After starting the server, ingest your documents:

```bash
curl -X POST http://localhost:8000/ingest
```

## API Endpoints

### Chat
- **POST** `/chat` - Send a message
- **POST** `/chat/stream` - Streaming response

### Admin
- **POST** `/ingest` - Ingest new documents
- **DELETE** `/vector-store` - Clear all documents
- **GET** `/sessions` - List all sessions
- **DELETE** `/session/{id}` - Clear session history

### Search
- **GET** `/search?query=...&k=3` - Search documents

## Testing

### Test Basic Chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What courses are offered in computer science?",
    "use_rag": true
  }'
```

### Test with Session
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me about admission process",
    "session_id": "test-session-123",
    "use_rag": true
  }'
```

### Check Health
```bash
curl http://localhost:8000/health
```

## Features

✅ **RAG Integration** - Searches college documents for context  
✅ **Groq LLM** - Fast responses using Llama 3.1  
✅ **Conversation History** - Optional MongoDB storage  
✅ **Streaming** - Real-time response streaming  
✅ **Session Management** - Track conversations  
✅ **Document Ingestion** - Easy PDF upload  

## Architecture

```
User Query → RAG Search → Context → LLM → Response
                ↓
         Vector Store (ChromaDB)
                ↓
         Chat History (MongoDB - Optional)
```

## Troubleshooting

**Error: No module named 'xyz'**
- Run: `pip install -r requirements.txt`

**Error: GROQ_API_KEY not found**
- Add your API key to `.env` file

**Error: No documents found**
- Add PDFs to `data/` folder
- Run `/ingest` endpoint

**MongoDB not working**
- It's optional! The app works without it
- Install MongoDB locally or use MongoDB Atlas

## Next Steps

1. ✅ Backend is ready!
2. Build frontend (Next.js/React)
3. Add authentication
4. Deploy (Railway, Render, or Vercel)

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`