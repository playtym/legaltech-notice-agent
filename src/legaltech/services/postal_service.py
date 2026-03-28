import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PostalServiceMock:
    """
    Mock integration for Delhivery/India Post APIs.
    """
    @staticmethod
    def dispatch_notice(notice_id: str, recipient_address: str, recipient_name: str) -> dict:
        """
        Simulates pushing a generated PDF notice to a physical print & post fulfillment center.
        """
        tracking_number = f"RPAD{uuid.uuid4().hex[:8].upper()}IN"
        logger.info(f"Dispatched physical notice for {notice_id} to {recipient_name} at {recipient_address}.")
        return {
            "status": "dispatched",
            "partner": "India Post (RPAD)",
            "tracking_id": tracking_number,
            "estimated_delivery_days": 5,
            "dispatched_at": datetime.utcnow().isoformat()
        }
