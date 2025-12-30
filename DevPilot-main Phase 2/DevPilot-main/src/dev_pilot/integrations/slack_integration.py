"""
Slack Integration Module

Provides integration with Slack for notifications, approval requests, and updates.
"""

import aiohttp
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from src.dev_pilot.integrations.base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationEvent,
    IntegrationResult,
    EventType,
)


class SlackIntegration(BaseIntegration):
    """
    Slack integration for DevPilot.
    
    Supports:
    - Sending notifications to channels
    - Approval request messages with buttons
    - Stage completion updates
    - Rich formatted messages with attachments
    """
    
    def __init__(self, config: IntegrationConfig):
        """
        Initialize Slack integration.
        
        Config should include:
        - webhook_url: Slack incoming webhook URL
        - api_token: Bot token (optional, for advanced features)
        - settings.default_channel: Default channel for messages
        - settings.mention_users: Users to mention on approvals
        """
        super().__init__(config)
        
        self.webhook_url = config.webhook_url
        self.api_token = config.api_token
        self.default_channel = config.settings.get("default_channel", "#devpilot")
        self.mention_users = config.settings.get("mention_users", [])
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """Establish connection to Slack."""
        try:
            self._session = aiohttp.ClientSession()
            
            # Test the connection
            if self.webhook_url:
                # Webhook doesn't require auth test, just validate URL format
                if not self.webhook_url.startswith("https://hooks.slack.com/"):
                    raise ValueError("Invalid Slack webhook URL")
            
            if self.api_token:
                # Test API token
                async with self._session.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                ) as response:
                    data = await response.json()
                    if not data.get("ok"):
                        raise ValueError(f"Slack auth failed: {data.get('error')}")
            
            self._set_connected(True)
            logger.info(f"Slack integration connected: {self.name}")
            return True
            
        except Exception as e:
            self._set_error(str(e))
            logger.error(f"Failed to connect Slack: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Close connection to Slack."""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self._set_connected(False)
            logger.info(f"Slack integration disconnected: {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting Slack: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Verify Slack connection is healthy."""
        if not self._session:
            return False
        
        try:
            if self.api_token:
                async with self._session.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                ) as response:
                    data = await response.json()
                    return data.get("ok", False)
            
            # Webhook-only mode, assume healthy if session exists
            return True
            
        except Exception:
            return False
    
    async def process_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Process an integration event.
        
        Args:
            event: The event to process
            
        Returns:
            Result of the operation
        """
        try:
            # Build message based on event type
            message = self._build_message(event)
            
            if not message:
                return IntegrationResult(
                    success=True,
                    integration_id=self.integration_id,
                    event_id=event.event_id,
                    message="No message to send for this event type",
                )
            
            # Send the message
            success = await self._send_message(message)
            
            return IntegrationResult(
                success=success,
                integration_id=self.integration_id,
                event_id=event.event_id,
                message="Message sent" if success else "Failed to send message",
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
    
    def _build_message(self, event: IntegrationEvent) -> Optional[Dict[str, Any]]:
        """Build Slack message from event."""
        
        # Map event types to message builders
        builders = {
            EventType.PROJECT_CREATED: self._build_project_created_message,
            EventType.PROJECT_COMPLETED: self._build_project_completed_message,
            EventType.STAGE_COMPLETED: self._build_stage_completed_message,
            EventType.APPROVAL_REQUIRED: self._build_approval_required_message,
            EventType.STAGE_APPROVED: self._build_stage_approved_message,
            EventType.STAGE_REJECTED: self._build_stage_rejected_message,
            EventType.USER_STORIES_GENERATED: self._build_artifacts_message,
            EventType.DESIGN_DOCS_GENERATED: self._build_artifacts_message,
            EventType.CODE_GENERATED: self._build_artifacts_message,
            EventType.CUSTOM: self._build_custom_message,
        }
        
        builder = builders.get(event.event_type)
        if builder:
            return builder(event)
        
        return None
    
    def _build_project_created_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build project created message."""
        project_name = event.data.get("project_name", "Unknown Project")
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 New Project Started",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Project:*\n{project_name}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Task ID:*\n`{event.task_id or 'N/A'}`",
                        },
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Started at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                        },
                    ],
                },
            ],
        }
    
    def _build_project_completed_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build project completed message."""
        project_name = event.data.get("project_name", "Unknown Project")
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Project Completed",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Project *{project_name}* has been completed successfully!",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Task ID:*\n`{event.task_id or 'N/A'}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Completed:*\n{event.timestamp.strftime('%Y-%m-%d %H:%M')}",
                        },
                    ],
                },
            ],
        }
    
    def _build_stage_completed_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build stage completed message."""
        stage = event.data.get("stage", "Unknown Stage")
        project_name = event.data.get("project_name", "Unknown Project")
        
        stage_emojis = {
            "requirements": "📋",
            "user_stories": "📖",
            "design": "🏗️",
            "coding": "💻",
            "security": "🔒",
            "testing": "🧪",
            "qa": "✅",
            "deployment": "🚀",
        }
        emoji = stage_emojis.get(stage.lower(), "✓")
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *Stage Completed:* {stage}\nProject: {project_name}",
                    },
                },
            ],
        }
    
    def _build_approval_required_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build approval required message with action buttons."""
        stage = event.data.get("stage", "Unknown Stage")
        project_name = event.data.get("project_name", "Unknown Project")
        summary = event.data.get("summary", "Review required")
        
        # Build mentions
        mentions = " ".join([f"<@{u}>" for u in self.mention_users]) if self.mention_users else ""
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⏳ Approval Required",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{mentions}\n\n*{stage}* needs your review for project *{project_name}*",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:*\n{summary}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Task ID:*\n`{event.task_id or 'N/A'}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Stage:*\n{stage}",
                        },
                    ],
                },
                {
                    "type": "actions",
                    "block_id": f"approval_{event.event_id}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Approve",
                                "emoji": True,
                            },
                            "style": "primary",
                            "value": json.dumps({
                                "action": "approve",
                                "task_id": event.task_id,
                                "stage": stage,
                            }),
                            "action_id": "approve_stage",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "❌ Reject",
                                "emoji": True,
                            },
                            "style": "danger",
                            "value": json.dumps({
                                "action": "reject",
                                "task_id": event.task_id,
                                "stage": stage,
                            }),
                            "action_id": "reject_stage",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🔍 View Details",
                                "emoji": True,
                            },
                            "value": json.dumps({
                                "action": "view",
                                "task_id": event.task_id,
                            }),
                            "action_id": "view_details",
                        },
                    ],
                },
            ],
        }
    
    def _build_stage_approved_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build stage approved message."""
        stage = event.data.get("stage", "Unknown Stage")
        approved_by = event.data.get("approved_by", "Unknown")
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *{stage}* has been approved by {approved_by}",
                    },
                },
            ],
        }
    
    def _build_stage_rejected_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build stage rejected message."""
        stage = event.data.get("stage", "Unknown Stage")
        rejected_by = event.data.get("rejected_by", "Unknown")
        feedback = event.data.get("feedback", "No feedback provided")
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *{stage}* has been rejected by {rejected_by}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Feedback:*\n{feedback}",
                    },
                },
            ],
        }
    
    def _build_artifacts_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build artifacts generated message."""
        artifact_type = event.event_type.value.replace("_generated", "").replace("_", " ").title()
        project_name = event.data.get("project_name", "Unknown Project")
        count = event.data.get("count", "")
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📄 *{artifact_type}* generated for {project_name}" + 
                               (f" ({count} items)" if count else ""),
                    },
                },
            ],
        }
    
    def _build_custom_message(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build custom notification message."""
        title = event.data.get("title", "DevPilot Notification")
        message = event.data.get("message", "")
        
        return {
            "channel": self.default_channel,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n{message}",
                    },
                },
            ],
        }
    
    async def _send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to Slack.
        
        Args:
            message: Slack message payload
            
        Returns:
            True if sent successfully
        """
        if not self._session:
            return False
        
        try:
            # Use webhook if available
            if self.webhook_url:
                async with self._session.post(
                    self.webhook_url,
                    json=message,
                ) as response:
                    return response.status == 200
            
            # Use API token
            elif self.api_token:
                async with self._session.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json=message,
                ) as response:
                    data = await response.json()
                    return data.get("ok", False)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    async def send_direct_message(
        self,
        user_id: str,
        message: str,
        **kwargs,
    ) -> bool:
        """
        Send a direct message to a Slack user.
        
        Args:
            user_id: Slack user ID
            message: Message text
            
        Returns:
            True if sent successfully
        """
        if not self.api_token:
            logger.warning("API token required for direct messages")
            return False
        
        payload = {
            "channel": user_id,
            "text": message,
            **kwargs,
        }
        
        return await self._send_message(payload)
    
    async def update_message(
        self,
        channel: str,
        ts: str,
        message: Dict[str, Any],
    ) -> bool:
        """
        Update an existing Slack message.
        
        Args:
            channel: Channel ID
            ts: Message timestamp
            message: New message content
            
        Returns:
            True if updated successfully
        """
        if not self.api_token or not self._session:
            return False
        
        try:
            async with self._session.post(
                "https://slack.com/api/chat.update",
                headers={"Authorization": f"Bearer {self.api_token}"},
                json={
                    "channel": channel,
                    "ts": ts,
                    **message,
                },
            ) as response:
                data = await response.json()
                return data.get("ok", False)
                
        except Exception as e:
            logger.error(f"Failed to update Slack message: {e}")
            return False
