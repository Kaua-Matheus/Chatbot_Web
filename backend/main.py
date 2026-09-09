import os
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

API_KEY = os.getenv("API_KEY")
AI_MODEL = os.getenv("API_MODEL", "gemini-3.6-flash")

if not API_KEY:
    raise RuntimeError("API_KEY não foi encontrada no arquivo .env")

# Inicializa o cliente oficial
client = genai.Client(api_key=API_KEY)

app = FastAPI(title="Gemini Chat API")

# Habilita CORS para permitir que o React faça requisições
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, defina o domínio exato do React ex: ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas Pydantic
class Message(BaseModel):
    role: str  # "user" ou "model"
    text: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []

def convert_history_to_genai_types(history: List[Message]) -> List[types.Content]:
    """
    Converte o histórico vindo da requisição JSON do React para o formato 
    types.Content exigido pela API do Gemini.
    """
    genai_history = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        genai_history.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg.text)]
            )
        )
    return genai_history

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    try:
        # 1. Converte o histórico enviado do React
        formatted_history = convert_history_to_genai_types(request.history)

        # 2. Cria uma sessão de Chat descartável configurada com o histórico acumulado
        chat = client.chats.create(
            model=AI_MODEL,
            history=formatted_history
        )

        # 3. Gerador assíncrono para o StreamingResponse
        async def generate():
            # Executa o envio via Chat.send_message_stream
            response_stream = chat.send_message_stream(request.message)
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))