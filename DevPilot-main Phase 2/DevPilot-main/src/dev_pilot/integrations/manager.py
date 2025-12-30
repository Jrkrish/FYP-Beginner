"""
Integration Manager Module

Manages all external integrations, event routing, and lifecycle.
"""

from typing import Any, Dict, List, Optional, Type
import asyncio
from datetime import datetime
from loguru import logger

from src.dev_pilot.integrations.base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationEvent,
    IntegrationResult,
    IntegrationStatus,
    EventType,
)


class IntegrationManager:
    """
    Manages external integrations for DevPilot.
    
    Responsibilities:
    - Register and manage integrations
    - Route events to appropriate integrations
    - Handle integration lifecycle
    - Provide integration status and metrics
    """
    
    _instance: Optional["IntegrationManager"] = None
    
    def __init__(self):
        """Initialize the integration manager."""
        self._integrations: Dict[str, BaseIntegration] = {}
        self._integration_types: Dict[str, Type[BaseIntegration]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._event_processor_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._events_processed = 0
        self._events_failed = 0
        
        logger.info("IntegrationManager initialized")
    
    @classmethod
    def get_instance(cls) -> "IntegrationManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = IntegrationManager()
        return cls._instance
    
    # ============ Integration Type Registration ============
    
    def register_integration_type(
        self,
        type_name: str,
        integration_class: Type[BaseIntegration],
    ):
        """
        Register an integration type.
        
        Args:
            type_name: Type identifier (e.g., "slack", "jira")
            integration_class: Integration class to use
        """
        self._integration_types[type_name] = integration_class
        logger.info(f"Registered integration type: {type_name}")
    
    def get_available_types(self) -> List[str]:
        """Get list of available integration types."""
        return list(self._integration_types.keys())
    
    # ============ Integration Lifecycle ============
    
    async def add_integration(self, config: IntegrationConfig) -> BaseIntegration:
        """
        Add and initialize a new integration.
        
        Args:
            config: Integration configuration
            
        Returns:
            The created integration instance
        """
        if config.integration_id in self._integrations:
            raise ValueError(f"Integration already exists: {config.integration_id}")
        
        # Get the integration class
        integration_class = self._integration_types.get(config.integration_type)
        if not integration_class:
            raise ValueError(f"Unknown integration type: {config.integration_type}")
        
        # Create and connect the integration
        integration = integration_class(config)
        
        if config.enabled:
            try:
                await integration.connect()
            except Exception as e:
                logger.error(f"Failed to connect integration {config.name}: {e}")
        
        self._integrations[config.integration_id] = integration
        logger.info(f"Added integration: {config.name}")
        
        return integration
    
    async def remove_integration(self, integration_id: str) -> bool:
        """
        Remove an integration.
        
        Args:
            integration_id: Integration to remove
            
        Returns:
            True if removed
        """
        integration = self._integrations.get(integration_id)
        if not integration:
            return False
        
        try:
            await integration.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting integration: {e}")
        
        del self._integrations[integration_id]
        logger.info(f"Removed integration: {integration_id}")
        
        return True
    
    async def enable_integration(self, integration_id: str) -> bool:
        """Enable an integration."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return False
        
        integration.config.enabled = True
        
        if not integration.is_connected:
            await integration.connect()
        
        return True
    
    async def disable_integration(self, integration_id: str) -> bool:
        """Disable an integration."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return False
        
        integration.config.enabled = False
        return True
    
    def get_integration(self, integration_id: str) -> Optional[BaseIntegration]:
        """Get an integration by ID."""
        return self._integrations.get(integration_id)
    
    def get_integrations(self) -> List[BaseIntegration]:
        """Get all integrations."""
        return list(self._integrations.values())
    
    def get_integrations_by_type(self, integration_type: str) -> List[BaseIntegration]:
        """Get integrations by type."""
        return [
            i for i in self._integrations.values()
            if i.integration_type == integration_type
        ]
    
    # ============ Event Processing ============
    
    async def start(self):
        """Start the integration manager."""
        if self._running:
            return
        
        self._running = True
        self._event_processor_task = asyncio.create_task(self._process_events())
        logger.info("IntegrationManager started")
    
    async def stop(self):
        """Stop the integration manager."""
        self._running = False
        
        if self._event_processor_task:
            self._event_processor_task.cancel()
            try:
                await self._event_processor_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all integrations
        for integration in self._integrations.values():
            try:
                await integration.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {integration.name}: {e}")
        
        logger.info("IntegrationManager stopped")
    
    async def emit_event(self, event: IntegrationEvent):
        """
        Emit an event to be processed by integrations.
        
        Args:
            event: The event to emit
        """
        await self._event_queue.put(event)
        logger.debug(f"Event emitted: {event.event_type.value}")
    
    async def emit(
        self,
        event_type: EventType,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Convenience method to emit an event.
        
        Args:
            event_type: Type of event
            project_id: Associated project ID
            task_id: Associated task ID
            data: Event data
            **kwargs: Additional event attributes
        """
        event = IntegrationEvent.create(
            event_type=event_type,
            project_id=project_id,
            task_id=task_id,
            data=data,
            **kwargs,
        )
        await self.emit_event(event)
    
    async def _process_events(self):
        """Background task to process events."""
        while self._running:
            try:
                # Wait for an event with timeout
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the event
                await self._route_event(event)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _route_event(self, event: IntegrationEvent):
        """
        Route an event to appropriate integrations.
        
        Args:
            event: The event to route
        """
        tasks = []
        
        for integration in self._integrations.values():
            if integration.should_process_event(event):
                tasks.append(self._process_with_integration(integration, event))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    self._events_failed += 1
                    logger.error(f"Integration processing failed: {result}")
                elif isinstance(result, IntegrationResult):
                    self._events_processed += 1
                    if not result.success:
                        self._events_failed += 1
    
    async def _process_with_integration(
        self,
        integration: BaseIntegration,
        event: IntegrationEvent,
    ) -> IntegrationResult:
        """Process an event with a specific integration."""
        try:
            return await integration.process_event(event)
        except Exception as e:
            logger.error(f"Error processing event with {integration.name}: {e}")
            return IntegrationResult(
                success=False,
                integration_id=integration.integration_id,
                event_id=event.event_id,
                message="Processing failed",
                error=str(e),
            )
    
    # ============ Direct Operations ============
    
    async def send_notification(
        self,
        title: str,
        message: str,
        integration_type: Optional[str] = None,
        **kwargs,
    ) -> List[IntegrationResult]:
        """
        Send a notification via integrations.
        
        Args:
            title: Notification title
            message: Notification message
            integration_type: Specific type to use (None = all)
            **kwargs: Additional arguments
            
        Returns:
            List of results from each integration
        """
        results = []
        
        integrations = (
            self.get_integrations_by_type(integration_type)
            if integration_type
            else self.get_integrations()
        )
        
        for integration in integrations:
            if integration.is_enabled and integration.is_connected:
                try:
                    result = await integration.send_notification(
                        title=title,
                        message=message,
                        **kwargs,
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Notification failed for {integration.name}: {e}")
        
        return results
    
    # ============ Health & Status ============
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all integrations.
        
        Returns:
            Health status of all integrations
        """
        results = {}
        
        for integration_id, integration in self._integrations.items():
            try:
                healthy = await integration.health_check()
                results[integration_id] = {
                    "name": integration.name,
                    "type": integration.integration_type,
                    "healthy": healthy,
                    "status": integration.status.value,
                }
            except Exception as e:
                results[integration_id] = {
                    "name": integration.name,
                    "type": integration.integration_type,
                    "healthy": False,
                    "error": str(e),
                }
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration manager status."""
        return {
            "running": self._running,
            "total_integrations": len(self._integrations),
            "active_integrations": sum(
                1 for i in self._integrations.values()
                if i.status == IntegrationStatus.ACTIVE
            ),
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
            "queue_size": self._event_queue.qsize(),
            "integrations": [
                i.get_status() for i in self._integrations.values()
            ],
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get integration metrics."""
        return {
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
            "success_rate": (
                (self._events_processed - self._events_failed) / self._events_processed
                if self._events_processed > 0
                else 1.0
            ),
            "queue_size": self._event_queue.qsize(),
            "integrations_by_status": {
                status.value: sum(
                    1 for i in self._integrations.values()
                    if i.status == status
                )
                for status in IntegrationStatus
            },
        }


# Convenience function
def get_integration_manager() -> IntegrationManager:
    """Get the singleton integration manager instance."""
    return IntegrationManager.get_instance()
