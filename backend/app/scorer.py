from app.models import LeadInput, LeadAnalysisResponse


def analyze_lead_rules(lead: LeadInput) -> LeadAnalysisResponse:
    """
    Deterministic rule-based lead qualification and scoring algorithm.
    Calculates score (0-100), determines classification (hot, warm, cold),
    assigns recommended operational next action, and drafts a contextual reply.
    """
    score = 0
    message_lower = lead.message.lower()
    service_lower = lead.requested_service.lower()

    # Rule 1: Urgency signals (+30 points)
    urgency_keywords = [
        "urgent", "urgently", "immediately", "asap",
        "right away", "emergency", "critical", "deadline", "soon as possible"
    ]
    has_urgency = any(kw in message_lower for kw in urgency_keywords)
    if has_urgency:
        score += 30

    # Rule 2: High-value service keywords (+25 points)
    target_services = [
        "automation", "crm", "ai", "customer support",
        "workflow", "virtual assistant", "pipeline", "bot", "agent"
    ]
    has_target_service = any(svc in service_lower for svc in target_services)
    if has_target_service:
        score += 25

    # Rule 3: Company presence (+20 points)
    if lead.company and lead.company.strip():
        score += 20

    # Rule 4: Valid email (+15 points) - Verified via Pydantic EmailStr
    if lead.email and "@" in lead.email:
        score += 15

    # Rule 5: Message depth & detail >= 30 chars (+10 points)
    if len(lead.message.strip()) >= 30:
        score += 10

    # Clamp score between 0 and 100
    final_score = max(0, min(100, score))

    # Determine classification, next action, and tailored draft reply
    if final_score >= 70:
        classification = "hot"
        next_action = "Immediate direct callback within 15 minutes by Senior Automation Specialist"
        reply = (
            f"Hello {lead.name}, thank you for reaching out with high priority regarding {lead.requested_service}. "
            f"We have fast-tracked your request, and our Senior Automation team is preparing a customized action plan to assist you immediately."
        )
    elif final_score >= 40:
        classification = "warm"
        next_action = "Send service portfolio deck and schedule standard discovery call within 24 hours"
        reply = (
            f"Hello {lead.name}, thank you for contacting us about {lead.requested_service}. "
            f"We have received your project details and will share our service portfolio and calendar links to schedule a discovery call within 24 hours."
        )
    else:
        classification = "cold"
        next_action = "Enroll in automated nurture sequence"
        reply = (
            f"Hello {lead.name}, thank you for your inquiry about {lead.requested_service}. "
            f"We have logged your request and will send across our getting-started guide and automation resources shortly."
        )

    return LeadAnalysisResponse(
        classification=classification,
        score=final_score,
        service_requested=lead.requested_service,
        next_action=next_action,
        reply=reply
    )
