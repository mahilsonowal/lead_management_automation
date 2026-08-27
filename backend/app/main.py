import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import LeadInput, LeadAnalysisResponse
from app.ai.manager import ai_manager
from app.db import init_db, save_lead, log_workflow_error, get_all_leads, get_workflow_errors, update_lead_status

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("lead_analysis_api")

# Initialize database schema on startup
init_db()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Microservice for deterministic and AI-powered lead qualification, scoring, and follow-up generation.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Formats Pydantic validation errors and records them to the SQLite audit log.
    """
    error_messages = []
    for err in exc.errors():
        field_path = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        error_messages.append(f"{field_path}: {err.get('msg', 'Invalid value')}")

    logger.warning("Validation failure on %s: %s", request.url.path, error_messages)
    
    # Audit log validation error into SQLite
    try:
        raw_body = getattr(request.state, "body", None) or str(exc.body)
        log_workflow_error(
            error_type="VALIDATION_ERROR",
            error_message="; ".join(error_messages),
            lead_id="INVALID_SUBMISSION",
            payload=raw_body
        )
    except Exception as log_exc:
        logger.warning("Failed to record error log to DB: %s", log_exc)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error_type": "VALIDATION_ERROR",
            "message": "Lead payload failed data validation checks.",
            "details": error_messages
        }
    )


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint to verify service and active AI configuration status.
    """
    return {
        "status": "healthy",
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "ai_provider_configured": settings.AI_PROVIDER,
        "database": "SQLite (lead_management.db)"
    }


@app.get("/leads", tags=["Leads Database"])
async def list_leads():
    """
    Retrieves all stored leads from the SQLite database.
    """
    leads = get_all_leads()
    return {"total": len(leads), "leads": leads}


@app.get("/errors", tags=["Audit & Errors"])
async def list_errors():
    """
    Retrieves recent workflow errors from the SQLite database.
    """
    errors = get_workflow_errors()
    return {"total": len(errors), "errors": errors}


@app.post(
    "/analyze-lead",
    response_model=LeadAnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["Lead Analysis"],
    summary="Analyze, score, qualify, and persist a lead inquiry"
)
async def analyze_lead(lead: LeadInput):
    """
    Ingests raw lead details, executes AI qualification (or deterministic rules with automatic fallback),
    persists the qualified lead to SQLite, and returns structured results.
    """
    try:
        logger.info("Analyzing lead submission for email domain: @%s", lead.email.split("@")[-1])
        result = await ai_manager.analyze_lead(lead)
        logger.info(
            "Lead analyzed successfully. Score: %d | Classification: %s | Mode: %s | Provider: %s",
            result.score, result.classification, result.analysis_mode, result.provider
        )

        # Persist lead record directly to SQLite database
        try:
            lead_record_dict = {
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "requested_service": lead.requested_service,
                "message": lead.message,
                "score": result.score,
                "classification": result.classification,
                "confidence": result.confidence,
                "analysis_mode": result.analysis_mode,
                "provider": result.provider,
                "next_action": result.next_action,
                "suggested_reply": result.reply,
                "status": "PENDING_APPROVAL" if result.score < 70 else "OPEN"
            }
            lead_id = save_lead(lead_record_dict)
            logger.info("Lead saved to database with ID: %s", lead_id)
        except Exception as db_exc:
            logger.warning("Database persistence warning: %s", db_exc)

        return result
    except Exception as exc:
        logger.exception("Unexpected error during lead analysis: %s", exc)
        log_workflow_error(
            error_type="PIPELINE_ERROR",
            error_message=str(exc),
            payload={"name": lead.name, "email": lead.email}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while analyzing the lead record."
        ) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
