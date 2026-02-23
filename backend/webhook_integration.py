# ============================================================================
# WEBHOOK INTEGRATION
# ============================================================================

"""
Webhook integration for real-time notifications and callbacks
"""

import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# WEBHOOK EVENT TYPES
# ============================================================================

class WebhookEventType(str, Enum):
    """Types of webhook events"""
    CANDIDATE_SUBMITTED = "candidate.submitted"
    CANDIDATE_PROCESSED = "candidate.processed"
    CANDIDATE_EVALUATED = "candidate.evaluated"
    BATCH_STARTED = "batch.started"
    BATCH_COMPLETED = "batch.completed"
    CANDIDATE_HIRED = "candidate.hired"
    CANDIDATE_REJECTED = "candidate.rejected"


# ============================================================================
# WEBHOOK MANAGER
# ============================================================================

class WebhookManager:
    """
    Manages webhook subscriptions and delivery
    """

    def __init__(self):
        """Initialize webhook manager"""
        self.subscriptions: Dict[str, List[str]] = {}
        self.timeout = 10.0  # HTTP timeout in seconds
        self.max_retries = 3

    def subscribe(
        self,
        webhook_url: str,
        event_types: List[WebhookEventType]
    ) -> Dict[str, Any]:
        """
        Subscribe to webhook events

        Args:
            webhook_url: URL to receive webhook POST requests
            event_types: List of event types to subscribe to

        Returns:
            Subscription confirmation
        """
        subscription_id = f"wh_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        for event_type in event_types:
            if event_type not in self.subscriptions:
                self.subscriptions[event_type] = []
            self.subscriptions[event_type].append(webhook_url)

        logger.info(f"Webhook subscribed: {webhook_url} for events: {[e.value for e in event_types]}")

        return {
            "subscription_id": subscription_id,
            "webhook_url": webhook_url,
            "events": [e.value for e in event_types],
            "status": "active"
        }

    def unsubscribe(
        self,
        webhook_url: str,
        event_type: Optional[WebhookEventType] = None
    ) -> Dict[str, Any]:
        """
        Unsubscribe from webhook events

        Args:
            webhook_url: URL to unsubscribe
            event_type: Specific event type, or None for all events

        Returns:
            Unsubscription confirmation
        """
        removed_count = 0

        if event_type:
            # Unsubscribe from specific event
            if event_type in self.subscriptions:
                if webhook_url in self.subscriptions[event_type]:
                    self.subscriptions[event_type].remove(webhook_url)
                    removed_count += 1
        else:
            # Unsubscribe from all events
            for event in list(self.subscriptions.keys()):
                if webhook_url in self.subscriptions[event]:
                    self.subscriptions[event].remove(webhook_url)
                    removed_count += 1

        logger.info(f"Webhook unsubscribed: {webhook_url} from {removed_count} events")

        return {
            "webhook_url": webhook_url,
            "removed_subscriptions": removed_count,
            "status": "inactive"
        }

    async def send_webhook(
        self,
        event_type: WebhookEventType,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Send webhook to all subscribers of an event type

        Args:
            event_type: Type of event
            data: Event payload data
            headers: Optional additional headers

        Returns:
            List of delivery results
        """
        if event_type not in self.subscriptions:
            logger.warning(f"No subscribers for event: {event_type}")
            return []

        webhook_urls = self.subscriptions[event_type]

        # Prepare webhook payload
        payload = {
            "event": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        # Prepare headers
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-HR-Automation-Webhook/1.0"
        }
        if headers:
            default_headers.update(headers)

        # Send to all subscribers
        delivery_results = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for url in webhook_urls:
                for attempt in range(self.max_retries):
                    try:
                        response = await client.post(
                            url,
                            json=payload,
                            headers=default_headers
                        )

                        delivery_results.append({
                            "webhook_url": url,
                            "status_code": response.status_code,
                            "success": 200 <= response.status_code < 300,
                            "attempt": attempt + 1
                        })

                        if response.status_code >= 500 and attempt < self.max_retries - 1:
                            # Server error, retry
                            continue
                        else:
                            # Success or client error, don't retry
                            break

                    except httpx.TimeoutException:
                        logger.warning(f"Webhook timeout: {url}")
                        if attempt < self.max_retries - 1:
                            continue
                        else:
                            delivery_results.append({
                                "webhook_url": url,
                                "status_code": None,
                                "success": False,
                                "error": "timeout",
                                "attempt": attempt + 1
                            })

                    except Exception as e:
                        logger.error(f"Webhook error: {url} - {str(e)}")
                        delivery_results.append({
                            "webhook_url": url,
                            "status_code": None,
                            "success": False,
                            "error": str(e),
                            "attempt": attempt + 1
                        })
                        break

        # Log results
        successful = sum(1 for r in delivery_results if r.get("success"))
        logger.info(
            f"Webhook sent: {event_type.value} to {len(webhook_urls)} subscribers, "
            f"{successful} successful"
        )

        return delivery_results


# ============================================================================
# WEBHOOK EVENT BUILDERS
# ============================================================================

def build_candidate_submitted_event(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build candidate submitted event payload"""
    return {
        "candidate": {
            "name": candidate_data.get("candidate_name"),
            "email": candidate_data.get("candidate_email"),
            "job_title": candidate_data.get("job_title")
        },
        "submitted_at": datetime.now().isoformat()
    }


def build_candidate_processed_event(
    candidate_data: Dict[str, Any],
    processing_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Build candidate processed event payload"""
    return {
        "candidate": {
            "name": candidate_data.get("candidate_name"),
            "email": candidate_data.get("candidate_email"),
            "job_title": candidate_data.get("job_title")
        },
        "result": {
            "score": processing_result.get("evaluation_score"),
            "decision": processing_result.get("evaluation", {}).get("decision"),
            "summary": processing_result.get("summary"),
            "cv_link": processing_result.get("cv_link")
        },
        "processed_at": datetime.now().isoformat()
    }


def build_candidate_evaluated_event(
    candidate_data: Dict[str, Any],
    evaluation: Dict[str, Any]
) -> Dict[str, Any]:
    """Build candidate evaluated event payload"""
    return {
        "candidate": {
            "name": candidate_data.get("candidate_name"),
            "email": candidate_data.get("candidate_email"),
            "job_title": candidate_data.get("job_title")
        },
        "evaluation": {
            "score": evaluation.get("score"),
            "decision": evaluation.get("decision"),
            "reasoning": evaluation.get("reasoning"),
            "strengths": evaluation.get("strengths"),
            "gaps": evaluation.get("gaps")
        },
        "evaluated_at": datetime.now().isoformat()
    }


def build_batch_started_event(
    batch_id: str,
    total_candidates: int,
    job_title: str
) -> Dict[str, Any]:
    """Build batch started event payload"""
    return {
        "batch_id": batch_id,
        "job_title": job_title,
        "total_candidates": total_candidates,
        "started_at": datetime.now().isoformat()
    }


def build_batch_completed_event(
    batch_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Build batch completed event payload"""
    return {
        "batch_id": batch_result.get("batch_id"),
        "job_title": batch_result.get("results", [{}])[0].get("result", {}).get("job_title", "Unknown"),
        "total_candidates": batch_result.get("total_candidates"),
        "successful": batch_result.get("successful"),
        "failed": batch_result.get("failed"),
        "average_score": batch_result.get("average_score"),
        "completed_at": batch_result.get("completed_at")
    }


# ============================================================================
# LANGGRAPH WEBHOOK INTEGRATION
# ============================================================================

async def send_candidate_webhooks(state: Dict[str, Any], webhook_manager: WebhookManager):
    """
    Send webhooks at appropriate points in workflow

    This function can be called from LangGraph nodes
    """
    # Send candidate submitted event (first node)
    if not state.get("webhook_sent_submitted", False):
        event = build_candidate_submitted_event(state)
        await webhook_manager.send_webhook(
            WebhookEventType.CANDIDATE_SUBMITTED,
            event
        )
        state["webhook_sent_submitted"] = True

    # Send candidate processed event (after evaluation)
    if state.get("evaluation_score") is not None and not state.get("webhook_sent_processed", False):
        event = build_candidate_processed_event(state, state)
        await webhook_manager.send_webhook(
            WebhookEventType.CANDIDATE_PROCESSED,
            event
        )
        state["webhook_sent_processed"] = True

        # Send evaluated event
        evaluation_event = build_candidate_evaluated_event(state, state.get("evaluation", {}))
        await webhook_manager.send_webhook(
            WebhookEventType.CANDIDATE_EVALUATED,
            evaluation_event
        )
        state["webhook_sent_evaluated"] = True

    return state


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global webhook manager instance
webhook_manager = WebhookManager()


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance"""
    return webhook_manager


def subscribe_to_webhook(
    webhook_url: str,
    event_types: List[str]
) -> Dict[str, Any]:
    """
    Subscribe to webhook events

    Args:
        webhook_url: URL to receive webhooks
        event_types: List of event type strings

    Returns:
        Subscription confirmation
    """
    # Convert string event types to enums
    event_enums = []
    for event_type in event_types:
        try:
            event_enums.append(WebhookEventType(event_type))
        except ValueError:
            logger.warning(f"Invalid event type: {event_type}")

    return webhook_manager.subscribe(webhook_url, event_enums)


def unsubscribe_from_webhook(
    webhook_url: str,
    event_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Unsubscribe from webhook events

    Args:
        webhook_url: URL to unsubscribe
        event_type: Optional specific event type

    Returns:
        Unsubscription confirmation
    """
    event_enum = WebhookEventType(event_type) if event_type else None
    return webhook_manager.unsubscribe(webhook_url, event_enum)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def example_webhook_usage():
        """Example of webhook integration"""

        # Subscribe to events
        subscription = subscribe_to_webhook(
            webhook_url="https://your-app.com/webhooks/hr",
            event_types=[
                "candidate.submitted",
                "candidate.processed",
                "candidate.evaluated"
            ]
        )

        print(f"Subscribed: {subscription}")

        # Send test event
        test_candidate = {
            "candidate_name": "John Doe",
            "candidate_email": "john@example.com",
            "job_title": "Senior AI Engineer"
        }

        await webhook_manager.send_webhook(
            WebhookEventType.CANDIDATE_SUBMITTED,
            build_candidate_submitted_event(test_candidate)
        )

        # Unsubscribe
        unsubscribe_from_webhook(
            webhook_url="https://your-app.com/webhooks/hr"
        )

    # asyncio.run(example_webhook_usage())
