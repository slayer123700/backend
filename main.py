
# backend/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import os
import fitz  # PyMuPDF
import docx
from fastapi.responses import StreamingResponse

app = FastAPI()

# Allow frontend (React) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-frontend.onrender.com"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🌟 Replace with your OpenAI API key (after revoking the old one!)
OPENAI_API_KEY = "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"
MODEL = "gpt-3.5-turbo"

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []

@app.post("/chat")
async def chat(request: ChatRequest):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = request.history + [{"role": "user", "content": request.message}]

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True
    }

    async def event_stream():
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                if response.status_code != 200:
                    error_text = await response.text()
                    yield f"data: {error_text}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line.strip() and line.startswith(""):
                        yield f"{line}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = ""

        if file.filename.endswith(".pdf"):
            doc = fitz.open(stream=await file.read(), filetype="pdf")
            for page in doc:
                content += page.get_text() + "\n"
            doc.close()

        elif file.filename.endswith(".docx"):
            doc = docx.Document(await file.read())
            content = "\n".join([para.text for para in doc.paragraphs])

        elif file.filename.endswith(".txt"):
            content = (await file.read()).decode("utf-8")

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        return {"text": content[:5000]}  # Limit to 5000 characters

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
