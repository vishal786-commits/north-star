import asyncio
import logging
import time

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Header, Depends

from app import metrics
from app.config import settings
from app.extractor import extract_resume
from app.analyzer import analyze_resume, analyze_fit, chat_reply
from app.ratelimit import enforce_daily_limit
from app.session import create_session, get_session, save_session, MESSAGE_LIMIT
from app.knowledge import MARKETS, DEFAULT_MARKET
from app.schemas import (
    AnalyzeResponse,
    FitResponse,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
)
from app.errors import ExtractionError, AnalysisError, SessionError, SessionNotFound

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_market(market: str) -> str:
    """Reject an unknown target market early. Returns the validated code."""
    if market not in MARKETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown market '{market}'. Choose one of: {', '.join(MARKETS)}.",
        )
    return market


@router.post("/analyze", response_model=AnalyzeResponse,
             dependencies=[Depends(enforce_daily_limit)])
async def analyze(file: UploadFile = File(...), market: str = Form(DEFAULT_MARKET)):
    t0 = time.perf_counter()

    # 1. Basic input validation — reject non-PDFs and unknown markets early.
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    market = _validate_market(market)

    # 2. Read the uploaded file into bytes, capping size to avoid memory blowups.
    pdf_bytes = await file.read()
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_upload_bytes // (1024 * 1024)} MB).",
        )

    # 3. Extract text. PyMuPDF is BLOCKING/CPU-bound, so we offload it to a
    #    thread — otherwise it would freeze the whole event loop.
    try:
        extract_t0 = time.perf_counter()
        resume_text, page_count = await asyncio.to_thread(extract_resume, pdf_bytes)
        extract_ms = (time.perf_counter() - extract_t0) * 1000
    except ExtractionError as e:
        await _record("review", "error", total_ms=_ms(t0), error_detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))

    # 4. Analyze — this is async I/O (awaiting OpenAI), so we just await it.
    try:
        analysis, meta = await analyze_resume(resume_text, page_count, market)
    except AnalysisError as e:
        await _record("review", "error", market=market, extract_ms=extract_ms, total_ms=_ms(t0), error_detail=str(e))
        raise HTTPException(status_code=502, detail=str(e))

    # 5. Store the session so the chat endpoint can use it later.
    try:
        session_id = await create_session(resume_text, analysis, kind="review", market=market)
    except SessionError as e:
        await _record("review", "error", market=market, extract_ms=extract_ms, total_ms=_ms(t0), error_detail=str(e), **meta)
        raise HTTPException(status_code=503, detail=str(e))

    # 6. Record metrics (best-effort) and return.
    await _record(
        "review", "ok", session_id=session_id, market=market, page_count=page_count,
        resume_chars=len(resume_text), score=analysis.ats.overall,
        extract_ms=extract_ms, total_ms=_ms(t0), **meta,
    )
    return AnalyzeResponse(session_id=session_id, analysis=analysis)


@router.post("/fit", response_model=FitResponse,
             dependencies=[Depends(enforce_daily_limit)])
async def fit(file: UploadFile = File(...), job_description: str = Form(...),
              market: str = Form(DEFAULT_MARKET)):
    t0 = time.perf_counter()

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    market = _validate_market(market)

    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="Please paste the job description.")

    if len(job_description) > settings.max_jd_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Job description too long (max {settings.max_jd_chars} characters).",
        )

    pdf_bytes = await file.read()
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_upload_bytes // (1024 * 1024)} MB).",
        )

    try:
        extract_t0 = time.perf_counter()
        resume_text, page_count = await asyncio.to_thread(extract_resume, pdf_bytes)
        extract_ms = (time.perf_counter() - extract_t0) * 1000
    except ExtractionError as e:
        await _record("fit", "error", total_ms=_ms(t0), error_detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))

    try:
        fit_result, meta = await analyze_fit(resume_text, page_count, job_description, market)
    except AnalysisError as e:
        await _record("fit", "error", market=market, extract_ms=extract_ms, total_ms=_ms(t0), error_detail=str(e))
        raise HTTPException(status_code=502, detail=str(e))

    try:
        session_id = await create_session(resume_text, fit_result, kind="fit", market=market)
    except SessionError as e:
        await _record("fit", "error", market=market, extract_ms=extract_ms, total_ms=_ms(t0), error_detail=str(e), **meta)
        raise HTTPException(status_code=503, detail=str(e))

    await _record(
        "fit", "ok", session_id=session_id, market=market, page_count=page_count,
        resume_chars=len(resume_text), score=fit_result.match_score,
        extract_ms=extract_ms, total_ms=_ms(t0), **meta,
    )
    return FitResponse(session_id=session_id, fit=fit_result)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    t0 = time.perf_counter()

    # 1. Load the session created during /analyze or /fit.
    try:
        data = await get_session(req.session_id)
    except SessionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SessionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 2. Enforce the per-session message limit.
    if data["message_count"] >= MESSAGE_LIMIT:
        raise HTTPException(status_code=429, detail="Message limit reached for this session.")

    # 3. Ask the coach — grounded in the resume + analysis + prior turns + market.
    try:
        reply, meta = await chat_reply(
            data["resume_text"], data["analysis"], data["history"], req.message,
            data.get("market", DEFAULT_MARKET),
        )
    except AnalysisError as e:
        await _record("chat", "error", session_id=req.session_id, total_ms=_ms(t0), error_detail=str(e))
        raise HTTPException(status_code=502, detail=str(e))

    # 4. Record the turn and refresh the session.
    data["history"].append({"role": "user", "content": req.message})
    data["history"].append({"role": "assistant", "content": reply})
    data["message_count"] += 1
    try:
        await save_session(req.session_id, data)
    except SessionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    await _record("chat", "ok", session_id=req.session_id, total_ms=_ms(t0), **meta)

    # 5. Report how many messages remain.
    remaining = max(0, MESSAGE_LIMIT - data["message_count"])
    return ChatResponse(reply=reply, messages_remaining=remaining, limit_reached=remaining == 0)


@router.post("/feedback")
async def feedback(req: FeedbackRequest):
    """Record a 👍/👎 on a result — the human relevance/quality signal."""
    await asyncio.to_thread(
        metrics.record_feedback,
        session_id=req.session_id,
        rating=req.rating,
        comment=req.comment,
    )
    return {"status": "ok"}


@router.get("/metrics")
async def get_metrics(
    token: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None),
):
    """Aggregate monitoring data for the dashboard. Guarded by admin token."""
    if settings.admin_token:
        supplied = token or x_admin_token
        if supplied != settings.admin_token:
            raise HTTPException(status_code=401, detail="Unauthorized.")
    return await asyncio.to_thread(metrics.get_metrics)


# ---- helpers ----------------------------------------------------------------

def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


async def _record(kind: str, status: str, **fields) -> None:
    """Write one metrics row off the event loop. Never raises."""
    try:
        await asyncio.to_thread(metrics.record_event, kind=kind, status=status, **fields)
    except Exception:
        logger.exception("metrics record failed (non-fatal)")
