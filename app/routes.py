import asyncio
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.extractor import extract_resume
from app.analyzer import analyze_resume, chat_reply
from app.session import create_session, get_session, save_session, MESSAGE_LIMIT
from app.schemas import AnalyzeResponse, ChatRequest, ChatResponse
from app.errors import ExtractionError, AnalysisError, SessionError, SessionNotFound

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    # 1. Basic input validation — reject non-PDFs early.
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    # 2. Read the uploaded file into bytes.
    pdf_bytes = await file.read()

    # 3. Extract text. PyMuPDF is BLOCKING/CPU-bound, so we offload it to a
    #    thread — otherwise it would freeze the whole event loop.
    try:
        resume_text, page_count = await asyncio.to_thread(extract_resume, pdf_bytes)
    except ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 4. Analyze — this is async I/O (awaiting OpenAI), so we just await it.
    try:
        analysis = await analyze_resume(resume_text, page_count)
    except AnalysisError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 5. Store the session so the chat endpoint can use it later.
    try:
        session_id = await create_session(resume_text, analysis)
    except SessionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 6. Return the analysis plus the session id.
    return AnalyzeResponse(session_id=session_id, analysis=analysis)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # 1. Load the session created during /analyze.
    try:
        data = await get_session(req.session_id)
    except SessionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SessionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 2. Enforce the per-session message limit.
    if data["message_count"] >= MESSAGE_LIMIT:
        raise HTTPException(status_code=429, detail="Message limit reached for this session.")

    # 3. Ask the coach — grounded in the resume + analysis + prior turns.
    try:
        reply = await chat_reply(
            data["resume_text"], data["analysis"], data["history"], req.message
        )
    except AnalysisError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 4. Record the turn and refresh the session.
    data["history"].append({"role": "user", "content": req.message})
    data["history"].append({"role": "assistant", "content": reply})
    data["message_count"] += 1
    try:
        await save_session(req.session_id, data)
    except SessionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 5. Report how many messages remain.
    remaining = max(0, MESSAGE_LIMIT - data["message_count"])
    return ChatResponse(reply=reply, messages_remaining=remaining, limit_reached=remaining == 0)