from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class LeadInput(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Full name of the lead submitter",
        examples=["Rahul Das"]
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address of the lead",
        examples=["rahul@example.com"]
    )
    company: Optional[str] = Field(
        default="",
        max_length=150,
        description="Company or business name (optional)",
        examples=["North East Digital Agency"]
    )
    requested_service: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Service or solution the lead is inquiring about",
        examples=["CRM and AI automation"]
    )
    message: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Inquiry or project details message",
        examples=["We urgently need help automating our customer support and lead follow-up process."]
    )

    @field_validator("name", "requested_service", "message", mode="before")
    @classmethod
    def strip_and_normalize(cls, value: str) -> str:
        if isinstance(value, str):
            return " ".join(value.strip().split())
        return value

    @field_validator("company", mode="before")
    @classmethod
    def normalize_company(cls, value: Optional[str]) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return " ".join(value.strip().split())
        return str(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class AIStructuredOutput(BaseModel):
    """
    Strict validation schema for JSON objects returned by AI providers.
    """
    classification: Literal["hot", "warm", "cold"] = Field(
        ...,
        description="Lead category: hot, warm, or cold"
    )
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Lead qualification score between 0 and 100"
    )
    requested_service: str = Field(
        ...,
        min_length=2,
        description="Standardized requested service name"
    )
    next_action: str = Field(
        ...,
        min_length=5,
        description="Actionable next step for the virtual assistant / sales team"
    )
    suggested_reply: str = Field(
        ...,
        min_length=10,
        description="Contextual, empathetic email reply draft"
    )
    confidence: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="AI confidence score between 0.0 and 1.0"
    )

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, value: str) -> str:
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ["hot", "warm", "cold"]:
                return val
            if "hot" in val:
                return "hot"
            if "warm" in val:
                return "warm"
        return "cold"

    @field_validator("score", mode="before")
    @classmethod
    def clamp_score(cls, value) -> int:
        try:
            num = int(float(value))
            return max(0, min(100, num))
        except (ValueError, TypeError):
            return 50


class LeadAnalysisResponse(BaseModel):
    """
    Standardized API output returned to n8n and clients.
    """
    classification: Literal["hot", "warm", "cold"] = Field(
        ...,
        description="Lead categorization: hot, warm, or cold",
        examples=["hot"]
    )
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Calculated qualification score between 0 and 100",
        examples=[100]
    )
    service_requested: str = Field(
        ...,
        description="Normalized requested service name",
        examples=["CRM and AI automation"]
    )
    next_action: str = Field(
        ...,
        description="Recommended operational next action for the team",
        examples=["Immediate direct callback within 15 minutes by Senior Automation Specialist"]
    )
    reply: str = Field(
        ...,
        description="Tailored email response draft for the lead",
        examples=["Hello Rahul Das, thank you for contacting us urgently about CRM and AI automation..."]
    )
    suggested_reply: str = Field(
        default="",
        description="Alias for reply containing the contextual email draft"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level of analysis (1.0 for deterministic rules)"
    )
    analysis_mode: Literal["ai", "rule_based_fallback", "rule_based"] = Field(
        default="rule_based",
        description="Indicates whether AI or deterministic rules performed the analysis"
    )
    provider: str = Field(
        default="rule_engine",
        description="The provider that performed the analysis (e.g. gemini, openai, ollama, rule_engine)"
    )

    @model_validator(mode="after")
    def sync_replies(self) -> "LeadAnalysisResponse":
        if not self.suggested_reply and self.reply:
            self.suggested_reply = self.reply
        elif not self.reply and self.suggested_reply:
            self.reply = self.suggested_reply
        return self
