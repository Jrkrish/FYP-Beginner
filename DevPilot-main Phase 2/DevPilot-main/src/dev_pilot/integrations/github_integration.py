"""
GitHub Integration Module

Provides integration with GitHub for code management, PRs, and repository operations.
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


class GitHubIntegration(BaseIntegration):
    """
    GitHub integration for DevPilot.
    
    Supports:
    - Creating repositories
    - Committing code files
    - Creating branches
    - Creating pull requests
    - Adding comments to PRs
    - Creating issues
    """
    
    API_BASE = "https://api.github.com"
    
    def __init__(self, config: IntegrationConfig):
        """
        Initialize GitHub integration.
        
        Config should include:
        - api_token: GitHub personal access token or app token
        - settings.owner: Repository owner (user or org)
        - repository: Default repository name
        - settings.default_branch: Default branch (default: main)
        """
        super().__init__(config)
        
        self.api_token = config.api_token
        self.owner = config.settings.get("owner", "")
        self.repository = config.repository or config.settings.get("repository", "")
        self.default_branch = config.settings.get("default_branch", "main")
        
        # PR settings
        self.auto_create_pr = config.settings.get("auto_create_pr", True)
        self.pr_reviewers = config.settings.get("pr_reviewers", [])
        self.pr_labels = config.settings.get("pr_labels", ["devpilot"])
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._user_info: Optional[Dict[str, Any]] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    async def connect(self) -> bool:
        """Establish connection to GitHub."""
        try:
            self._session = aiohttp.ClientSession(headers=self._get_headers())
            
            # Test authentication
            async with self._session.get(f"{self.API_BASE}/user") as response:
                if response.status != 200:
                    error = await response.text()
                    raise ValueError(f"GitHub auth failed: {error}")
                
                self._user_info = await response.json()
                logger.info(f"Connected to GitHub as: {self._user_info.get('login')}")
            
            self._set_connected(True)
            return True
            
        except Exception as e:
            self._set_error(str(e))
            logger.error(f"Failed to connect to GitHub: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Close connection to GitHub."""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self._set_connected(False)
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from GitHub: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Verify GitHub connection is healthy."""
        if not self._session:
            return False
        
        try:
            async with self._session.get(
                f"{self.API_BASE}/rate_limit"
            ) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def process_event(self, event: IntegrationEvent) -> IntegrationResult:
        """Process an integration event."""
        try:
            handlers = {
                EventType.PROJECT_CREATED: self._handle_project_created,
                EventType.CODE_GENERATED: self._handle_code_generated,
                EventType.STAGE_COMPLETED: self._handle_stage_completed,
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
        """Handle project created - create branch."""
        project_name = event.data.get("project_name", "devpilot-project")
        task_id = event.task_id or "unknown"
        
        # Create a feature branch
        branch_name = f"devpilot/{self._sanitize_branch_name(project_name)}-{task_id[:8]}"
        
        success = await self.create_branch(branch_name)
        
        return IntegrationResult(
            success=success,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message=f"Created branch: {branch_name}" if success else "Failed to create branch",
            response_data={"branch": branch_name},
        )
    
    async def _handle_code_generated(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle code generated - commit files and optionally create PR."""
        files = event.data.get("files", [])
        project_name = event.data.get("project_name", "DevPilot Project")
        task_id = event.task_id or "unknown"
        branch_name = event.data.get("branch") or f"devpilot/{self._sanitize_branch_name(project_name)}-{task_id[:8]}"
        
        if not files:
            return IntegrationResult(
                success=True,
                integration_id=self.integration_id,
                event_id=event.event_id,
                message="No files to commit",
            )
        
        # Ensure branch exists
        await self.create_branch(branch_name)
        
        # Commit all files
        commit_sha = await self.commit_files(
            files=files,
            branch=branch_name,
            message=f"[DevPilot] Generated code for {project_name}",
        )
        
        response_data = {"branch": branch_name, "commit": commit_sha}
        
        # Create PR if configured
        if self.auto_create_pr and commit_sha:
            pr = await self.create_pull_request(
                title=f"[DevPilot] {project_name}",
                body=self._format_pr_description(project_name, files, task_id),
                head=branch_name,
                base=self.default_branch,
                labels=self.pr_labels,
            )
            
            if pr:
                response_data["pr"] = pr
                
                # Add reviewers if configured
                if self.pr_reviewers:
                    await self.request_reviewers(
                        pr_number=pr.get("number"),
                        reviewers=self.pr_reviewers,
                    )
        
        return IntegrationResult(
            success=commit_sha is not None,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message=f"Committed {len(files)} files" + (f" and created PR" if response_data.get("pr") else ""),
            response_data=response_data,
        )
    
    async def _handle_stage_completed(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle stage completed - add comment to PR."""
        stage = event.data.get("stage", "Unknown")
        pr_number = event.data.get("pr_number")
        
        if pr_number:
            await self.add_pr_comment(
                pr_number=pr_number,
                body=f"✅ **Stage Completed:** {stage}",
            )
        
        return IntegrationResult(
            success=True,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message="Stage completion noted",
        )
    
    async def _handle_test_cases(self, event: IntegrationEvent) -> IntegrationResult:
        """Handle test cases generated - commit test files."""
        test_files = event.data.get("test_files", [])
        branch_name = event.data.get("branch")
        
        if not test_files or not branch_name:
            return IntegrationResult(
                success=True,
                integration_id=self.integration_id,
                event_id=event.event_id,
                message="No test files to commit",
            )
        
        commit_sha = await self.commit_files(
            files=test_files,
            branch=branch_name,
            message="[DevPilot] Added test cases",
        )
        
        return IntegrationResult(
            success=commit_sha is not None,
            integration_id=self.integration_id,
            event_id=event.event_id,
            message=f"Committed {len(test_files)} test files",
            response_data={"commit": commit_sha},
        )
    
    def _sanitize_branch_name(self, name: str) -> str:
        """Sanitize a string for use as branch name."""
        # Replace spaces and special chars with hyphens
        sanitized = "".join(c if c.isalnum() else "-" for c in name.lower())
        # Remove multiple consecutive hyphens
        while "--" in sanitized:
            sanitized = sanitized.replace("--", "-")
        return sanitized.strip("-")[:50]
    
    def _format_pr_description(
        self,
        project_name: str,
        files: List[Dict[str, Any]],
        task_id: str,
    ) -> str:
        """Format PR description."""
        file_list = "\n".join([f"- `{f.get('path', f.get('name', 'file'))}`" for f in files[:20]])
        
        return f"""## DevPilot Generated Code

This PR contains auto-generated code for project: **{project_name}**

### Task ID
`{task_id}`

### Files Changed
{file_list}
{f"_...and {len(files) - 20} more files_" if len(files) > 20 else ""}

### Review Checklist
- [ ] Code follows project conventions
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Security review completed

---
_Generated by [DevPilot](https://github.com/devpilot)_
"""
    
    # ============ GitHub API Methods ============
    
    async def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = True,
        auto_init: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new repository.
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether repo is private
            auto_init: Initialize with README
            
        Returns:
            Repository data or None
        """
        if not self._session:
            return None
        
        try:
            payload = {
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
            }
            
            # Create in org if owner is not the user
            if self.owner and self._user_info and self.owner != self._user_info.get("login"):
                url = f"{self.API_BASE}/orgs/{self.owner}/repos"
            else:
                url = f"{self.API_BASE}/user/repos"
            
            async with self._session.post(url, json=payload) as response:
                if response.status == 201:
                    data = await response.json()
                    logger.info(f"Created repository: {data.get('full_name')}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"Failed to create repository: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            return None
    
    async def create_branch(
        self,
        branch_name: str,
        from_branch: Optional[str] = None,
    ) -> bool:
        """
        Create a new branch.
        
        Args:
            branch_name: New branch name
            from_branch: Source branch (default: default_branch)
            
        Returns:
            True if created successfully
        """
        if not self._session:
            return False
        
        try:
            from_branch = from_branch or self.default_branch
            
            # Get the SHA of the source branch
            async with self._session.get(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/ref/heads/{from_branch}"
            ) as response:
                if response.status != 200:
                    return False
                data = await response.json()
                sha = data["object"]["sha"]
            
            # Create the new branch
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/refs",
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": sha,
                },
            ) as response:
                if response.status == 201:
                    logger.info(f"Created branch: {branch_name}")
                    return True
                elif response.status == 422:
                    # Branch already exists
                    logger.debug(f"Branch already exists: {branch_name}")
                    return True
                else:
                    error = await response.text()
                    logger.error(f"Failed to create branch: {error}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return False
    
    async def commit_files(
        self,
        files: List[Dict[str, Any]],
        branch: str,
        message: str,
    ) -> Optional[str]:
        """
        Commit multiple files to a branch.
        
        Args:
            files: List of files with 'path' and 'content' keys
            branch: Target branch
            message: Commit message
            
        Returns:
            Commit SHA or None
        """
        if not self._session or not files:
            return None
        
        try:
            # Get the current commit SHA
            async with self._session.get(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/ref/heads/{branch}"
            ) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                base_sha = data["object"]["sha"]
            
            # Get the base tree
            async with self._session.get(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/commits/{base_sha}"
            ) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                base_tree = data["tree"]["sha"]
            
            # Create blobs for each file
            tree_items = []
            for file in files:
                path = file.get("path", file.get("name", ""))
                content = file.get("content", "")
                
                # Create blob
                async with self._session.post(
                    f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/blobs",
                    json={
                        "content": base64.b64encode(content.encode()).decode(),
                        "encoding": "base64",
                    },
                ) as response:
                    if response.status == 201:
                        blob_data = await response.json()
                        tree_items.append({
                            "path": path,
                            "mode": "100644",
                            "type": "blob",
                            "sha": blob_data["sha"],
                        })
            
            if not tree_items:
                return None
            
            # Create tree
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/trees",
                json={
                    "base_tree": base_tree,
                    "tree": tree_items,
                },
            ) as response:
                if response.status != 201:
                    return None
                tree_data = await response.json()
            
            # Create commit
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/commits",
                json={
                    "message": message,
                    "tree": tree_data["sha"],
                    "parents": [base_sha],
                },
            ) as response:
                if response.status != 201:
                    return None
                commit_data = await response.json()
            
            # Update branch reference
            async with self._session.patch(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/git/refs/heads/{branch}",
                json={"sha": commit_data["sha"]},
            ) as response:
                if response.status == 200:
                    logger.info(f"Committed {len(files)} files: {commit_data['sha'][:7]}")
                    return commit_data["sha"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error committing files: {e}")
            return None
    
    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a pull request.
        
        Args:
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch
            labels: Labels to add
            
        Returns:
            PR data or None
        """
        if not self._session:
            return None
        
        try:
            base = base or self.default_branch
            
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/pulls",
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
            ) as response:
                if response.status == 201:
                    pr_data = await response.json()
                    logger.info(f"Created PR #{pr_data['number']}: {title}")
                    
                    # Add labels
                    if labels:
                        await self._add_labels_to_issue(
                            pr_data["number"],
                            labels,
                        )
                    
                    return pr_data
                else:
                    error = await response.text()
                    logger.error(f"Failed to create PR: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return None
    
    async def request_reviewers(
        self,
        pr_number: int,
        reviewers: List[str],
    ) -> bool:
        """
        Request reviewers for a PR.
        
        Args:
            pr_number: PR number
            reviewers: List of GitHub usernames
            
        Returns:
            True if successful
        """
        if not self._session:
            return False
        
        try:
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/pulls/{pr_number}/requested_reviewers",
                json={"reviewers": reviewers},
            ) as response:
                return response.status == 201
                
        except Exception as e:
            logger.error(f"Error requesting reviewers: {e}")
            return False
    
    async def add_pr_comment(
        self,
        pr_number: int,
        body: str,
    ) -> bool:
        """
        Add a comment to a PR.
        
        Args:
            pr_number: PR number
            body: Comment text
            
        Returns:
            True if successful
        """
        if not self._session:
            return False
        
        try:
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/issues/{pr_number}/comments",
                json={"body": body},
            ) as response:
                return response.status == 201
                
        except Exception as e:
            logger.error(f"Error adding PR comment: {e}")
            return False
    
    async def _add_labels_to_issue(
        self,
        issue_number: int,
        labels: List[str],
    ) -> bool:
        """Add labels to an issue/PR."""
        if not self._session:
            return False
        
        try:
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/issues/{issue_number}/labels",
                json={"labels": labels},
            ) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a GitHub issue.
        
        Args:
            title: Issue title
            body: Issue body
            labels: Labels to add
            assignees: Users to assign
            
        Returns:
            Issue data or None
        """
        if not self._session:
            return None
        
        try:
            payload = {
                "title": title,
                "body": body,
            }
            
            if labels:
                payload["labels"] = labels
            if assignees:
                payload["assignees"] = assignees
            
            async with self._session.post(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/issues",
                json=payload,
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    logger.info(f"Created issue #{data['number']}: {title}")
                    return data
                return None
                
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return None
    
    async def get_file_content(
        self,
        path: str,
        branch: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get file content from repository.
        
        Args:
            path: File path
            branch: Branch name
            
        Returns:
            File content or None
        """
        if not self._session:
            return None
        
        try:
            params = {}
            if branch:
                params["ref"] = branch
            
            async with self._session.get(
                f"{self.API_BASE}/repos/{self.owner}/{self.repository}/contents/{path}",
                params=params,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = base64.b64decode(data["content"]).decode()
                    return content
                return None
                
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return None
