"""Email channel services."""

from app.services.channels.email.marketing import EmailMarketingService
from app.services.channels.email.customer_service import EmailCustomerService
from app.services.channels.email.templates import EmailTemplateManager

__all__ = [
    "EmailMarketingService",
    "EmailCustomerService",
    "EmailTemplateManager",
]
