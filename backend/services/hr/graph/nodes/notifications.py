# ============================================================================
# Notification nodes: fan-out, email, Slack, WhatsApp
# ============================================================================

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def fan_out_notifications(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fan out for parallel notifications"""
    logger.info(f"Fanning out notifications for {state.get('candidate_name')}")
    return state


async def send_hr_email_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Send email notification to HR (placeholder)"""
    try:
        if state.get("notify_hr"):
            hr_email = state.get("hr_email", "hr@company.com")
            candidate_name = state.get("candidate_name", "candidate")
            score = state.get("evaluation_score", 0)
            message = state.get("notification_message", "")
            logger.info(f"📧 Email would be sent to {hr_email}: {candidate_name} - {message} (Score: {score})")
        else:
            logger.info("Email notification skipped (notify_hr=False)")
    except Exception as e:
        error_msg = f"Email notification error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
    return state


async def send_slack_notification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Send Slack notification (placeholder)"""
    try:
        if state.get("notify_hr"):
            candidate_name = state.get("candidate_name", "candidate")
            score = state.get("evaluation_score", 0)
            tag = state.get("tag", "unknown")
            logger.info(f"💬 Slack notification: {candidate_name} ({tag}, Score: {score})")
        else:
            logger.info("Slack notification skipped (notify_hr=False)")
    except Exception as e:
        error_msg = f"Slack notification error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
    return state


async def send_whatsapp_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Send WhatsApp notification (placeholder)"""
    try:
        if state.get("notify_hr"):
            candidate_name = state.get("candidate_name", "candidate")
            logger.info(f"📱 WhatsApp: New candidate {candidate_name}")
        else:
            logger.info("WhatsApp notification skipped (notify_hr=False)")
    except Exception as e:
        error_msg = f"WhatsApp notification error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
    return state
