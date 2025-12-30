"""
Jira Integration Module

Provides integration with Jira for creating issues, managing epics, and syncing user stories.
"""

import aiohttp
import base64
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


class JiraIntegration(BaseIntegration):
    """
    Jira integration for DevPilot.
    
    Supports:
    - Creating epics for projects
    - Creating stories from user stories
    - Creating sub-tasks for technical work
    - Updating issue status
    - Adding comments
    - Linking issues
    """
    
    def __init__(self, config: IntegrationConfig):
        """
        Initialize Jira integration.
        
        Config should include:
        - base_url: Jira instance URL (e.g., https://company.atlassian.net)
        - api_token: Jira API token
        - settings.email: User email for authentication
        - project_key: Default Jira project key
        - settings.issue_type_story: Issue type for stories (default: Story)
        - settings.issue_type_task: Issue type for tasks (default: Task)
        """
        super().__init__(config)
        
        self.base_url = config.base_url.rstrip("/") if config.base_url else ""
        self.api_token = config.api_token
        self.email = config.settings.get("email", "")
        self.project_key = config.project_key or config.settings.get("project_key", "")
        
        # Issue type mappings
        self.issue_type_epic = config.settings.get("issue_type_epic", "Epic")
        self.issue_type_story = config.settings.get("issue_type_story", "Story")
        self.issue_type_task = config.settings.get("issue_type_task", "Task")
        self.issue_type_bug = config.settings.get("issue_type_bug", "Bug")
        
        # Priority mappings
        self.priority_map = config.settings.get("priority_map", {
            "Critical": "Highest",
            "High": "High",
            "Medium": "Medium",
            "Low": "Low",
        })
        
        # Custom fields
        self.custom_fields = config.settings.get("custom_fields", {})
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _get_auth_header(self) -> Dict[str, str]:
        """Get authentication header."""
        if self.email and self.api_token:
            credentials = f"{self.email}:{self.api_token}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {}
    
    async def connect(self) -> bool:
        """Establish connection to Jira."""
        try:
            headers = {
                **self._get_auth_header(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            self._session = aiohttp.ClientSession(headers=headers)
            
            # Test the connection
            async with self._session.get(
                f"{self.base_url}/rest/api/3/myself"
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise ValueError(f"Jira auth failed: {error}")
                
                user_data = await response.json()
                logger.info(f"Connected to Jira as: {user_data.get('displayName')}")
            
            self._set_connected(True)
            return True
            
        except Exception as e:
            self._set_error(str(e))
            logger.error(f"Failed to connect to Jira: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Close connection to Jira."""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self._set_connected(False)
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Jira: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Verify Jira connection is healthy."""
        if not self._session:
            return False
        
        try:
            async with self._session.get(
                f"{self.base_url}/rest/api/3/myself"
            ) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def process_event(self, event: IntegrationEvent) -> IntegrationResult:
        """Process an integration event."""
        try:
            handlers = {
                EventType.PROJECT_CREATED: self._handle_project_created,
                EventType.USER_STORIES_GENERATED: self._handle_user_stories,
                EventType.STAGE_COMPLETED: self._handle_stage_completed,
                EventType.CODE_GENERATED: self._handle_code_generated,
                EventType.TEST_CASES_GENERATED: self._handle_test_cases,
            }
            
            handler = handlers.get(event.event_type)
            if handler:
                return await handler(event)
            
            return IntegrationResult(
                success=True,
                integration_id=self.integration_id,
                event_id=event.event_id,
                message="No action for this event type",
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
    
    async def _handle_project_created(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle project created event - create epic."""
        project_name = event.data.get("project_name", "DevPilot Project")
        description = event.data.get("description", "")
        
        # Create an epic for the project
        epic = await self.create_epic(
            summary=f"[DevPilot] {project_name}",
            description=f"Auto-generated epic for DevPilot project: {project_name}\n\n{description}",
            labels=["devpilot", "auto-generated"],
        )
        
        if epic:
            return IntegrationResult(
                success=True,
                integration_id=self.integration_id,
                event_id=event.event_id,
                message=f"Created epic: {epic.get('key')}",
                response_data=epic,
            )
        
        return IntegrationResult(
            success=False,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message="Failed to create epic",
        )
    
    async def _handle_user_stories(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle user stories generated - create Jira stories."""
        user_stories = event.data.get("user_stories", [])
        epic_key = event.data.get("epic_key")
        
        created_issues = []
        
        for story in user_stories:
            issue = await self.create_story(
                summary=story.get("title", "User Story"),
                description=self._format_user_story_description(story),
                priority=self._map_priority(story.get("priority", "Medium")),
                epic_key=epic_key,
                labels=["devpilot", "user-story"],
            )
            
            if issue:
                created_issues.append(issue)
        
        return IntegrationResult(
            success=len(created_issues) > 0,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message=f"Created {len(created_issues)} stories",
            response_data={"issues": created_issues},
        )
    
    async def _handle_stage_completed(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle stage completed - add comment to epic."""
        stage = event.data.get("stage", "Unknown")
        epic_key = event.data.get("epic_key")
        
        if epic_key:
            await self.add_comment(
                issue_key=epic_key,
                comment=f"✅ Stage completed: {stage}",
            )
        
        return IntegrationResult(
            success=True,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message=f"Stage completion noted",
        )
    
    async def _handle_code_generated(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle code generated - create technical tasks."""
        files = event.data.get("files", [])
        epic_key = event.data.get("epic_key")
        
        created_tasks = []
        
        for file_info in files[:10]:  # Limit to 10 tasks
            task = await self.create_task(
                summary=f"Implement: {file_info.get('name', 'file')}",
                description=f"Generated code file: {file_info.get('path', '')}\n\n```\n{file_info.get('content', '')[:500]}...\n```",
                epic_key=epic_key,
                labels=["devpilot", "code-task"],
            )
            
            if task:
                created_tasks.append(task)
        
        return IntegrationResult(
            success=True,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message=f"Created {len(created_tasks)} tasks",
            response_data={"tasks": created_tasks},
        )
    
    async def _handle_test_cases(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle test cases generated - create test tasks."""
        test_cases = event.data.get("test_cases", [])
        epic_key = event.data.get("epic_key")
        
        created_tasks = []
        
        for test in test_cases[:10]:
            task = await self.create_task(
                summary=f"Test: {test.get('name', 'Test Case')}",
                description=f"Test case: {test.get('description', '')}\n\nSteps:\n{test.get('steps', '')}",
                epic_key=epic_key,
                labels=["devpilot", "test-case"],
            )
            
            if task:
                created_tasks.append(task)
        
        return IntegrationResult(
            success=True,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message=f"Created {len(created_tasks)} test tasks",
            response_data={"tasks": created_tasks},
        )
    
    def _format_user_story_description(self, story: Dict[str, Any]) -> str:
        """Format user story as Jira description."""
        description = story.get("description", "")
        acceptance = story.get("acceptance_criteria", "")
        
        return f"""h3. Description
{description}

h3. Acceptance Criteria
{acceptance}

----
_Auto-generated by DevPilot_
"""
    
    def _map_priority(self, priority: str) -> str:
        """Map DevPilot priority to Jira priority."""
        return self.priority_map.get(priority, "Medium")
    
    # ============ Jira API Methods ============
    
    async def create_epic(
        self,
        summary: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Jira epic.
        
        Args:
            summary: Epic summary
            description: Epic description
            labels: Labels to add
            
        Returns:
            Created epic data or None
        """
        return await self._create_issue(
            issue_type=self.issue_type_epic,
            summary=summary,
            description=description,
            labels=labels,
            **kwargs,
        )
    
    async def create_story(
        self,
        summary: str,
        description: str = "",
        priority: str = "Medium",
        epic_key: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Jira story.
        
        Args:
            summary: Story summary
            description: Story description
            priority: Priority level
            epic_key: Parent epic key
            labels: Labels to add
            
        Returns:
            Created story data or None
        """
        return await self._create_issue(
            issue_type=self.issue_type_story,
            summary=summary,
            description=description,
            priority=priority,
            parent_key=epic_key,
            labels=labels,
            **kwargs,
        )
    
    async def create_task(
        self,
        summary: str,
        description: str = "",
        epic_key: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Jira task.
        
        Args:
            summary: Task summary
            description: Task description
            epic_key: Parent epic key
            labels: Labels to add
            
        Returns:
            Created task data or None
        """
        return await self._create_issue(
            issue_type=self.issue_type_task,
            summary=summary,
            description=description,
            parent_key=epic_key,
            labels=labels,
            **kwargs,
        )
    
    async def _create_issue(
        self,
        issue_type: str,
        summary: str,
        description: str = "",
        priority: Optional[str] = None,
        parent_key: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Create a Jira issue."""
        if not self._session:
            return None
        
        try:
            # Build issue payload
            fields = {
                "project": {"key": self.project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }
            
            # Add description (Jira Cloud uses ADF format)
            if description:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": description}
                            ]
                        }
                    ]
                }
            
            if priority:
                fields["priority"] = {"name": priority}
            
            if labels:
                fields["labels"] = labels
            
            # Link to epic if provided
            if parent_key and issue_type != self.issue_type_epic:
                # Use parent field for newer Jira
                fields["parent"] = {"key": parent_key}
            
            # Add custom fields
            for field_id, value in kwargs.items():
                if field_id.startswith("customfield_"):
                    fields[field_id] = value
            
            async with self._session.post(
                f"{self.base_url}/rest/api/3/issue",
                json={"fields": fields},
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    logger.info(f"Created Jira issue: {data.get('key')}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"Failed to create Jira issue: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating Jira issue: {e}")
            return None
    
    async def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any],
    ) -> bool:
        """
        Update a Jira issue.
        
        Args:
            issue_key: Issue key (e.g., PROJ-123)
            fields: Fields to update
            
        Returns:
            True if updated successfully
        """
        if not self._session:
            return False
        
        try:
            async with self._session.put(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                json={"fields": fields},
            ) as response:
                return response.status in [200, 204]
                
        except Exception as e:
            logger.error(f"Error updating Jira issue: {e}")
            return False
    
    async def add_comment(
        self,
        issue_key: str,
        comment: str,
    ) -> bool:
        """
        Add a comment to a Jira issue.
        
        Args:
            issue_key: Issue key
            comment: Comment text
            
        Returns:
            True if added successfully
        """
        if not self._session:
            return False
        
        try:
            async with self._session.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                json={
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": comment}
                                ]
                            }
                        ]
                    }
                },
            ) as response:
                return response.status in [200, 201]
                
        except Exception as e:
            logger.error(f"Error adding Jira comment: {e}")
            return False
    
    async def transition_issue(
        self,
        issue_key: str,
        transition_name: str,
    ) -> bool:
        """
        Transition an issue to a new status.
        
        Args:
            issue_key: Issue key
            transition_name: Target transition name
            
        Returns:
            True if transitioned successfully
        """
        if not self._session:
            return False
        
        try:
            # Get available transitions
            async with self._session.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
            ) as response:
                if response.status != 200:
                    return False
                data = await response.json()
            
            # Find matching transition
            transitions = data.get("transitions", [])
            transition_id = None
            for t in transitions:
                if t.get("name", "").lower() == transition_name.lower():
                    transition_id = t.get("id")
                    break
            
            if not transition_id:
                logger.warning(f"Transition '{transition_name}' not found")
                return False
            
            # Execute transition
            async with self._session.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                json={"transition": {"id": transition_id}},
            ) as response:
                return response.status == 204
                
        except Exception as e:
            logger.error(f"Error transitioning Jira issue: {e}")
            return False
    
    async def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a Jira issue by key.
        
        Args:
            issue_key: Issue key
            
        Returns:
            Issue data or None
        """
        if not self._session:
            return None
        
        try:
            async with self._session.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
                
        except Exception as e:
            logger.error(f"Error getting Jira issue: {e}")
            return None
    
    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search for issues using JQL.
        
        Args:
            jql: JQL query string
            max_results: Maximum results to return
            
        Returns:
            List of matching issues
        """
        if not self._session:
            return []
        
        try:
            async with self._session.get(
                f"{self.base_url}/rest/api/3/search",
                params={
                    "jql": jql,
                    "maxResults": max_results,
                },
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("issues", [])
                return []
                
        except Exception as e:
            logger.error(f"Error searching Jira issues: {e}")
            return []
