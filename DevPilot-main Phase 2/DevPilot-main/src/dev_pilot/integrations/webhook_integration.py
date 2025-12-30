"""
Webhook Integration Module

Provides a generic webhook integration for custom systems.
"""

import aiohttp
import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from loguru import logger

from src.dev_pilot.integrations.base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationEvent,
    IntegrationResult,
    EventType,
)


class WebhookIntegration(BaseIntegration):
    """
    Generic webhook integration for DevPilot.
    
    Supports:
    - Sending webhooks to custom endpoints
    - Signature verification (HMAC)
    - Custom headers and authentication
    - Event filtering
    - Retry logic
    """
    
    def __init__(self, config: IntegrationConfig):
        """
        Initialize webhook integration.
        
        Config should include:
        - webhook_url: Target webhook URL
        - api_token: Secret for HMAC signing (optional)
        - settings.headers: Additional headers
        - settings.events: List of events to send (or 'all')
        - settings.retry_count: Number of retries (default: 3)
        - settings.timeout: Request timeout in seconds (default: 30)
        """
        super().__init__(config)
        
        self.webhook_url = config.webhook_url or config.settings.get("webhook_url", "")
        self.secret = config.api_token or config.settings.get("secret", "")
        
        # Custom headers
        self.custom_headers = config.settings.get("headers", {})
        
        # Event filtering
        self.enabled_events = config.settings.get("events", "all")
        
        # Retry settings
        self.retry_count = config.settings.get("retry_count", 3)
        self.timeout = config.settings.get("timeout", 30)
        
        # Payload transformation
        self.payload_template = config.settings.get("payload_template")
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DevPilot/1.0",
            **self.custom_headers,
        }
        return headers
    
    def _sign_payload(self, payload: str) -> str:
        """Sign payload with HMAC-SHA256."""
        if not self.secret:
            return ""
        
        signature = hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return f"sha256={signature}"
    
    async def connect(self) -> bool:
        """Establish connection (verify webhook URL is reachable)."""
        try:
            self._session = aiohttp.ClientSession()
            
            # Optionally verify URL is reachable with a HEAD request
            if self.webhook_url:
                try:
                    async with self._session.head(
                        self.webhook_url,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        # Accept any response as "reachable"
                        logger.info(f"Webhook URL reachable: {self.webhook_url}")
                except Exception:
                    # URL might not support HEAD, that's okay
                    logger.debug("Webhook URL HEAD check skipped")
            
            self._set_connected(True)
            return True
            
        except Exception as e:
            self._set_error(str(e))
            logger.error(f"Failed to initialize webhook: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Close connection."""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self._set_connected(False)
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting webhook: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Verify webhook is healthy."""
        return self._session is not None and bool(self.webhook_url)
    
    def _should_send_event(self, event_type: EventType) -> bool:
        """Check if event should be sent based on configuration."""
        if self.enabled_events == "all":
            return True
        
        if isinstance(self.enabled_events, list):
            return event_type.value in self.enabled_events
        
        return True
    
    async def process_event(self, event: IntegrationEvent) -> IntegrationResult:
        """Process an integration event."""
        try:
            # Check if this event should be sent
            if not self._should_send_event(event.event_type):
                return IntegrationResult(
                    success=True,
                    integration_id=self.integration_id,
                    event_id=event.event_id,
                    message="Event filtered out by configuration",
                )
            
            # Build payload
            payload = self._build_payload(event)
            
            # Send webhook
            success, response_data = await self._send_webhook(payload)
            
            return IntegrationResult(
                success=success,
                integration_id=self.integration_id,
                event_id=event.event_id,
                message="Webhook sent successfully" if success else "Webhook failed",
                response_data=response_data,
            )
            
        except Exception as e:
            self._set_error(str(e))
            return IntegrationResult(
                success=False,
                integration_id=self.integration_id,
                event_id=event.event_id,
                message="Error processing event",
                error=str(e),
            )
    
    def _build_payload(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build webhook payload from event."""
        # If custom template is provided, use it
        if self.payload_template:
            return self._apply_template(self.payload_template, event)
        
        # Default payload structure
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "task_id": event.task_id,
            "agent_id": event.agent_id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "metadata": event.metadata,
        }
    
    def _apply_template(
        self,
        template: Dict[str, Any],
        event: IntegrationEvent,
    ) -> Dict[str, Any]:
        """Apply a template to transform the payload."""
        # Simple template variable replacement
        def replace_vars(value: Any) -> Any:
            if isinstance(value, str):
                # Replace template variables like {{event.data.project_name}}
                if "{{" in value:
                    value = value.replace("{{event_id}}", event.event_id)
                    value = value.replace("{{event_type}}", event.event_type.value)
                    value = value.replace("{{task_id}}", event.task_id or "")
                    value = value.replace("{{agent_id}}", event.agent_id or "")
                    value = value.replace("{{timestamp}}", event.timestamp.isoformat())
                    
                    # Replace data fields
                    for key, val in event.data.items():
                        value = value.replace(f"{{{{data.{key}}}}}", str(val))
                
                return value
            elif isinstance(value, dict):
                return {k: replace_vars(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_vars(v) for v in value]
            return value
        
        return replace_vars(template.copy())
    
    async def _send_webhook(
        self,
        payload: Dict[str, Any],
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Send webhook with retry logic."""
        if not self._session or not self.webhook_url:
            return False, None
        
        payload_str = json.dumps(payload)
        
        headers = self._get_headers()
        
        # Add signature if secret is configured
        if self.secret:
            headers["X-DevPilot-Signature"] = self._sign_payload(payload_str)
        
        # Add event type header
        headers["X-DevPilot-Event"] = payload.get("event_type", "unknown")
        
        for attempt in range(self.retry_count):
            try:
                async with self._session.post(
                    self.webhook_url,
                    data=payload_str,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response_text = await response.text()
                    
                    if response.status < 400:
                        logger.info(f"Webhook sent successfully: {response.status}")
                        try:
                            return True, json.loads(response_text)
                        except json.JSONDecodeError:
                            return True, {"raw": response_text}
                    
                    logger.warning(
                        f"Webhook failed (attempt {attempt + 1}/{self.retry_count}): "
                        f"{response.status} - {response_text[:200]}"
                    )
                    
            except Exception as e:
                logger.warning(
                    f"Webhook error (attempt {attempt + 1}/{self.retry_count}): {e}"
                )
        
        return False, None
    
    # ============ Additional Methods ============
    
    async def send_custom_payload(
        self,
        payload: Dict[str, Any],
        url: Optional[str] = None,
    ) -> bool:
        """
        Send a custom payload to the webhook.
        
        Args:
            payload: Custom payload to send
            url: Override URL (optional)
            
        Returns:
            True if successful
        """
        original_url = self.webhook_url
        if url:
            self.webhook_url = url
        
        try:
            success, _ = await self._send_webhook(payload)
            return success
        finally:
            self.webhook_url = original_url
    
    def set_event_filter(self, events: List[str]) -> None:
        """
        Set which events should be sent.
        
        Args:
            events: List of event type values, or ["all"]
        """
        if events == ["all"]:
            self.enabled_events = "all"
        else:
            self.enabled_events = events


class WebhookRegistry:
    """
    Registry for managing multiple webhook integrations.
    
    Allows registering webhooks for specific events or event patterns.
    """
    
    def __init__(self):
        self._webhooks: Dict[str, WebhookIntegration] = {}
        self._event_mappings: Dict[EventType, List[str]] = {}
    
    def register(
        self,
        webhook_id: str,
        webhook: WebhookIntegration,
        events: Optional[List[EventType]] = None,
    ) -> None:
        """
        Register a webhook.
        
        Args:
            webhook_id: Unique webhook identifier
            webhook: Webhook integration instance
            events: Events to trigger this webhook (None = all)
        """
        self._webhooks[webhook_id] = webhook
        
        if events:
            for event_type in events:
                if event_type not in self._event_mappings:
                    self._event_mappings[event_type] = []
                self._event_mappings[event_type].append(webhook_id)
    
    def unregister(self, webhook_id: str) -> None:
        """
        Unregister a webhook.
        
        Args:
            webhook_id: Webhook identifier to remove
        """
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
        
        # Remove from event mappings
        for event_type in self._event_mappings:
            if webhook_id in self._event_mappings[event_type]:
                self._event_mappings[event_type].remove(webhook_id)
    
    def get_webhooks_for_event(
        self,
        event_type: EventType,
    ) -> List[WebhookIntegration]:
        """
        Get all webhooks that should receive an event.
        
        Args:
            event_type: Event type
            
        Returns:
            List of webhooks
        """
        webhooks = []
        
        # Get specifically mapped webhooks
        if event_type in self._event_mappings:
            for webhook_id in self._event_mappings[event_type]:
                if webhook_id in self._webhooks:
                    webhooks.append(self._webhooks[webhook_id])
        
        # Add webhooks configured for all events
        for webhook_id, webhook in self._webhooks.items():
            if webhook.enabled_events == "all" and webhook not in webhooks:
                webhooks.append(webhook)
        
        return webhooks
    
    async def dispatch_event(
        self,
        event: IntegrationEvent,
    ) -> List[IntegrationResult]:
        """
        Dispatch an event to all relevant webhooks.
        
        Args:
            event: Event to dispatch
            
        Returns:
            List of results from each webhook
        """
        webhooks = self.get_webhooks_for_event(event.event_type)
        results = []
        
        for webhook in webhooks:
            result = await webhook.process_event(event)
            results.append(result)
        
        return results
    
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks."""
        return [
            {
                "id": webhook_id,
                "url": webhook.webhook_url,
                "connected": webhook.is_connected,
                "events": webhook.enabled_events,
            }
            for webhook_id, webhook in self._webhooks.items()
        ]
