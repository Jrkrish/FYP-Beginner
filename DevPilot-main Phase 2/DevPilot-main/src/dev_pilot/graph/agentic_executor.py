"""
Agentic Graph Executor Module

Bridge between the new multi-agent system and the existing GraphExecutor interface.
Provides backward compatibility while leveraging the agent-based architecture.
"""

from typing import Any, Dict, List, Optional
import uuid
import asyncio
from loguru import logger

from src.dev_pilot.cache.redis_cache import flush_redis_cache, save_state_to_redis, get_state_from_redis
import src.dev_pilot.utils.constants as const
from src.dev_pilot.state.sdlc_state import SDLCState, UserStoryList, UserStories


class AgenticGraphExecutor:
    """
    Graph executor that uses the multi-agent system for SDLC workflow execution.
    
    Provides the same interface as GraphExecutor but delegates to specialized
    agents for each phase of the SDLC process.
    """
    
    def __init__(
        self,
        llm: Any,
        use_agents: bool = True,
        fallback_graph: Optional[Any] = None,
    ):
        """
        Initialize the agentic executor.
        
        Args:
            llm: Language model instance
            use_agents: Whether to use agent-based execution (True) or fallback to legacy
            fallback_graph: Optional legacy graph for fallback mode
        """
        self.llm = llm
        self.use_agents = use_agents
        self.fallback_graph = fallback_graph
        
        # Import here to avoid circular imports
        self._agentic_system = None
        self._initialized = False
        
        # Session tracking
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"AgenticGraphExecutor created (use_agents={use_agents})")
    
    async def _ensure_initialized(self):
        """Ensure the agentic system is initialized."""
        if self._initialized:
            return
        
        if self.use_agents:
            try:
                from src.dev_pilot.core.agentic_system import AgenticSystem
                self._agentic_system = AgenticSystem(llm=self.llm)
                await self._agentic_system.initialize()
                self._initialized = True
                logger.info("AgenticSystem initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AgenticSystem: {e}")
                self.use_agents = False
                self._initialized = True
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(coro)
    
    def get_thread(self, task_id: str) -> Dict[str, Any]:
        """Get thread configuration for task."""
        return {"configurable": {"thread_id": task_id}}
    
    # ============ Main Interface Methods ============
    
    def start_workflow(self, project_name: str) -> Dict[str, Any]:
        """
        Start a new SDLC workflow.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Dict with task_id and initial state
        """
        return self._run_async(self._start_workflow_async(project_name))
    
    async def _start_workflow_async(self, project_name: str) -> Dict[str, Any]:
        """Async implementation of start_workflow."""
        await self._ensure_initialized()
        
        flush_redis_cache()
        
        # Generate task ID
        task_id = f"sdlc-session-{uuid.uuid4().hex[:8]}"
        
        if self.use_agents and self._agentic_system:
            try:
                # Create project using agentic system
                project = await self._agentic_system.create_project(
                    project_name=project_name,
                )

                # Start the workflow execution
                workflow_result = await self._agentic_system.start_project_workflow(
                    project["project_id"]
                )

                # Map to legacy state format
                state = self._create_initial_state(project_name, task_id)

                # Store session mapping
                self._sessions[task_id] = {
                    "project_id": project["project_id"],
                    "project_name": project_name,
                    "stage": const.PROJECT_INITILIZATION,
                    "execution_id": workflow_result["execution_id"],
                }

                # Save to Redis for compatibility
                save_state_to_redis(task_id, state)

                logger.info(f"Started agentic workflow: {task_id} with execution: {workflow_result['execution_id']}")
                return {"task_id": task_id, "state": state}
                
            except Exception as e:
                logger.error(f"Agentic workflow failed, using fallback: {e}")
                return self._fallback_start_workflow(project_name, task_id)
        else:
            return self._fallback_start_workflow(project_name, task_id)
    
    def _fallback_start_workflow(self, project_name: str, task_id: str) -> Dict[str, Any]:
        """Fallback to legacy graph execution."""
        if self.fallback_graph:
            thread = self.get_thread(task_id)
            state = None
            for event in self.fallback_graph.stream(
                {"project_name": project_name}, thread, stream_mode="values"
            ):
                state = event
            
            current_state = self.fallback_graph.get_state(thread)
            save_state_to_redis(task_id, current_state)
            return {"task_id": task_id, "state": state}
        else:
            # Minimal state without graph
            state = self._create_initial_state(project_name, task_id)
            save_state_to_redis(task_id, state)
            return {"task_id": task_id, "state": state}
    
    def _create_initial_state(self, project_name: str, task_id: str) -> Dict[str, Any]:
        """Create initial state structure."""
        return {
            "project_name": project_name,
            "task_id": task_id,
            "requirements": [],
            "user_stories": None,
            "design_documents": None,
            "code_generated": None,
            "security_recommendations": None,
            "test_cases": None,
            "qa_testing_comments": None,
            "deployment_feedback": None,
            "artifacts": {},
            "next_node": const.REVIEW_USER_STORIES,
        }
    
    def generate_stories(self, task_id: str, requirements: List[str]) -> Dict[str, Any]:
        """
        Generate user stories from requirements.
        
        Args:
            task_id: Session task ID
            requirements: List of requirement strings
            
        Returns:
            Dict with task_id and updated state
        """
        return self._run_async(self._generate_stories_async(task_id, requirements))
    
    async def _generate_stories_async(self, task_id: str, requirements: List[str]) -> Dict[str, Any]:
        """Async implementation of generate_stories."""
        await self._ensure_initialized()
        
        saved_state = get_state_from_redis(task_id)
        if not saved_state:
            saved_state = {}
        
        saved_state["requirements"] = requirements
        saved_state["next_node"] = const.REVIEW_USER_STORIES
        
        if self.use_agents and self._agentic_system:
            try:
                session = self._sessions.get(task_id, {})
                project_id = session.get("project_id")
                
                if project_id:
                    # Submit requirements to agentic system
                    await self._agentic_system.submit_requirements(
                        project_id=project_id,
                        requirements=requirements,
                    )
                
                # Use BA agent to generate user stories
                result = await self._agentic_system.execute_agent_task(
                    agent_type="business_analyst",
                    task_type="generate_user_stories",
                    input_data={
                        "project_name": saved_state.get("project_name", ""),
                        "requirements": requirements,
                    },
                )
                
                # Convert result to legacy format
                user_stories = self._convert_user_stories(result)
                saved_state["user_stories"] = user_stories
                
                # Update session
                if task_id in self._sessions:
                    self._sessions[task_id]["stage"] = const.GENERATE_USER_STORIES
                
                save_state_to_redis(task_id, saved_state)
                logger.info(f"Generated user stories via agent for {task_id}")
                
                return {"task_id": task_id, "state": saved_state}
                
            except Exception as e:
                logger.error(f"Agent story generation failed: {e}")
                return self._fallback_generate_stories(task_id, saved_state)
        else:
            return self._fallback_generate_stories(task_id, saved_state)
    
    def _fallback_generate_stories(self, task_id: str, saved_state: Dict) -> Dict[str, Any]:
        """Fallback story generation."""
        if self.fallback_graph:
            return self._update_and_resume_graph(saved_state, task_id, "get_user_requirements")
        else:
            # Generate mock stories for testing
            saved_state["user_stories"] = self._create_mock_user_stories(
                saved_state.get("requirements", [])
            )
            save_state_to_redis(task_id, saved_state)
            return {"task_id": task_id, "state": saved_state}
    
    def _convert_user_stories(self, result: Dict[str, Any]) -> UserStoryList:
        """Convert agent result to UserStoryList format."""
        stories = result.get("user_stories", [])
        user_story_objects = []
        
        for i, story in enumerate(stories):
            if isinstance(story, dict):
                user_story_objects.append(UserStories(
                    id=story.get("id", i + 1),
                    title=story.get("title", f"User Story {i + 1}"),
                    description=story.get("description", ""),
                    priority=story.get("priority", 3),
                    acceptance_criteria=story.get("acceptance_criteria", ""),
                ))
            elif isinstance(story, str):
                user_story_objects.append(UserStories(
                    id=i + 1,
                    title=f"User Story {i + 1}",
                    description=story,
                    priority=3,
                    acceptance_criteria="To be defined",
                ))
        
        return UserStoryList(user_stories=user_story_objects)
    
    def _create_mock_user_stories(self, requirements: List[str]) -> UserStoryList:
        """Create mock user stories for testing."""
        stories = []
        for i, req in enumerate(requirements):
            stories.append(UserStories(
                id=i + 1,
                title=f"Story for: {req[:50]}",
                description=f"As a user, I want {req}",
                priority=3,
                acceptance_criteria="Given the feature is implemented, when the user uses it, then it works as expected.",
            ))
        return UserStoryList(user_stories=stories)
    
    def graph_review_flow(
        self,
        task_id: str,
        status: str,
        feedback: Optional[str],
        review_type: str,
    ) -> Dict[str, Any]:
        """
        Handle review flow for any stage.
        
        Args:
            task_id: Session task ID
            status: "approved" or "feedback"
            feedback: Optional feedback text
            review_type: Type of review (from constants)
            
        Returns:
            Dict with task_id and updated state
        """
        return self._run_async(
            self._graph_review_flow_async(task_id, status, feedback, review_type)
        )
    
    async def _graph_review_flow_async(
        self,
        task_id: str,
        status: str,
        feedback: Optional[str],
        review_type: str,
    ) -> Dict[str, Any]:
        """Async implementation of graph_review_flow."""
        await self._ensure_initialized()
        
        saved_state = get_state_from_redis(task_id)
        if not saved_state:
            raise ValueError(f"No state found for task: {task_id}")
        
        # Determine agent and next stage based on review type
        agent_mapping = {
            const.REVIEW_USER_STORIES: {
                "agent": "business_analyst",
                "task": "revise_user_stories",
                "next_approved": const.REVIEW_DESIGN_DOCUMENTS,
                "state_field": "user_stories",
                "status_field": "user_stories_review_status",
                "feedback_field": "user_stories_feedback",
                "node_name": "review_user_stories",
            },
            const.REVIEW_DESIGN_DOCUMENTS: {
                "agent": "architect",
                "task": "create_design_document",
                "next_approved": const.REVIEW_CODE,
                "state_field": "design_documents",
                "status_field": "design_documents_review_status",
                "feedback_field": "design_documents_feedback",
                "node_name": "review_design_documents",
            },
            const.REVIEW_CODE: {
                "agent": "developer",
                "task": "generate_code",
                "next_approved": const.REVIEW_SECURITY_RECOMMENDATIONS,
                "state_field": "code_generated",
                "status_field": "code_review_status",
                "feedback_field": "code_review_feedback",
                "node_name": "code_review",
            },
            const.REVIEW_SECURITY_RECOMMENDATIONS: {
                "agent": "security",
                "task": "security_review",
                "next_approved": const.REVIEW_TEST_CASES,
                "state_field": "security_recommendations",
                "status_field": "security_review_status",
                "feedback_field": "security_review_comments",
                "node_name": "security_review",
            },
            const.REVIEW_TEST_CASES: {
                "agent": "qa",
                "task": "generate_test_cases",
                "next_approved": const.REVIEW_QA_TESTING,
                "state_field": "test_cases",
                "status_field": "test_case_review_status",
                "feedback_field": "test_case_review_feedback",
                "node_name": "review_test_cases",
            },
            const.REVIEW_QA_TESTING: {
                "agent": "qa",
                "task": "qa_testing",
                "next_approved": const.END_NODE,
                "state_field": "qa_testing_comments",
                "status_field": "qa_testing_status",
                "feedback_field": "qa_testing_feedback",
                "node_name": "qa_review",
            },
        }
        
        mapping = agent_mapping.get(review_type)
        if not mapping:
            raise ValueError(f"Unsupported review type: {review_type}")
        
        # Update state fields
        saved_state[mapping["status_field"]] = status
        saved_state[mapping["feedback_field"]] = feedback
        
        if status == "feedback":
            saved_state["next_node"] = review_type
        else:
            saved_state["next_node"] = mapping["next_approved"]
        
        # Always try agentic system first, but fall back gracefully
        agent_success = False
        if self.use_agents and self._agentic_system:
            try:
                session = self._sessions.get(task_id, {})
                project_id = session.get("project_id")
                execution_id = session.get("execution_id")

                if status == "approved" and project_id and execution_id:
                    logger.info(f"Approving stage {review_type} for project {project_id}")
                    # Try to approve stage in agentic system
                    try:
                        await self._agentic_system.approve_stage(
                            project_id=project_id,
                            feedback=feedback,
                        )
                        agent_success = True
                    except Exception as approve_error:
                        logger.warning(f"Agent approval failed, continuing manually: {approve_error}")

                    # Execute next agent if approved and agent system is working
                    if agent_success:
                        next_agent = self._get_next_agent(review_type)
                        logger.info(f"Next agent config: {next_agent}")
                        if next_agent:
                            try:
                                logger.info(f"Executing next agent: {next_agent['agent']} for task: {next_agent['task']}")
                                result = await self._agentic_system.execute_agent_task(
                                    agent_type=next_agent["agent"],
                                    task_type=next_agent["task"],
                                    input_data={
                                        "project_name": saved_state.get("project_name", ""),
                                        "requirements": saved_state.get("requirements", []),
                                        "user_stories": saved_state.get("user_stories"),
                                        "design_documents": saved_state.get("design_documents"),
                                        "code_generated": saved_state.get("code_generated"),
                                    },
                                )
                                logger.info(f"Next agent result: {result}")

                                # Update state with result
                                if next_agent["state_field"] in result:
                                    saved_state[next_agent["state_field"]] = result[next_agent["state_field"]]
                                    logger.info(f"Updated state field {next_agent['state_field']}")
                                else:
                                    logger.warning(f"No {next_agent['state_field']} in result")
                            except Exception as agent_error:
                                logger.warning(f"Next agent execution failed, continuing manually: {agent_error}")
                        else:
                            logger.warning(f"No next agent found for review type: {review_type}")

                elif status == "feedback":
                    # Try to re-execute current agent with feedback
                    if project_id:
                        try:
                            await self._agentic_system.reject_stage(
                                project_id=project_id,
                                feedback=feedback or "Please revise",
                            )
                            agent_success = True
                        except Exception as reject_error:
                            logger.warning(f"Agent rejection failed, continuing manually: {reject_error}")

                    if agent_success:
                        try:
                            result = await self._agentic_system.execute_agent_task(
                                agent_type=mapping["agent"],
                                task_type=mapping["task"],
                                input_data={
                                    "project_name": saved_state.get("project_name", ""),
                                    "requirements": saved_state.get("requirements", []),
                                    "feedback": feedback,
                                    "previous_output": saved_state.get(mapping["state_field"]),
                                },
                            )

                            if mapping["state_field"] in result:
                                saved_state[mapping["state_field"]] = result[mapping["state_field"]]
                        except Exception as feedback_error:
                            logger.warning(f"Agent feedback execution failed, continuing manually: {feedback_error}")

                if agent_success:
                    logger.info(f"Review flow completed via agent: {review_type} -> {status}")
                else:
                    logger.info(f"Agent system not available or failed, using manual progression: {review_type} -> {status}")

            except Exception as e:
                logger.error(f"Agent review flow failed completely: {e}")
                agent_success = False

        # Always save state and return, regardless of agent success
        save_state_to_redis(task_id, saved_state)
        return {"task_id": task_id, "state": saved_state}
    
    def _get_next_agent(self, current_review: str) -> Optional[Dict[str, str]]:
        """Get the next agent configuration after approval."""
        next_mapping = {
            const.REVIEW_USER_STORIES: {
                "agent": "architect",
                "task": "create_design_document",
                "state_field": "design_documents",
            },
            const.REVIEW_DESIGN_DOCUMENTS: {
                "agent": "developer",
                "task": "generate_code",
                "state_field": "code_generated",
            },
            const.REVIEW_CODE: {
                "agent": "security",
                "task": "security_review",
                "state_field": "security_recommendations",
            },
            const.REVIEW_SECURITY_RECOMMENDATIONS: {
                "agent": "qa",
                "task": "generate_test_cases",
                "state_field": "test_cases",
            },
            const.REVIEW_TEST_CASES: {
                "agent": "qa",
                "task": "qa_testing",
                "state_field": "qa_testing_comments",
            },
            const.REVIEW_QA_TESTING: {
                "agent": "devops",
                "task": "deploy",
                "state_field": "deployment_feedback",
            },
        }
        return next_mapping.get(current_review)
    
    def _fallback_review_flow(
        self,
        task_id: str,
        saved_state: Dict,
        node_name: str,
    ) -> Dict[str, Any]:
        """Fallback review flow using legacy graph."""
        if self.fallback_graph:
            return self._update_and_resume_graph(saved_state, task_id, node_name)
        else:
            save_state_to_redis(task_id, saved_state)
            return {"task_id": task_id, "state": saved_state}
    
    def _update_and_resume_graph(
        self,
        saved_state: Dict,
        task_id: str,
        as_node: str,
    ) -> Dict[str, Any]:
        """Update and resume legacy graph."""
        if not self.fallback_graph:
            save_state_to_redis(task_id, saved_state)
            return {"task_id": task_id, "state": saved_state}
        
        thread = self.get_thread(task_id)
        self.fallback_graph.update_state(thread, saved_state, as_node=as_node)
        
        state = None
        for event in self.fallback_graph.stream(None, thread, stream_mode="values"):
            logger.debug(f"Event Received: {event}")
            state = event
        
        current_state = self.fallback_graph.get_state(thread)
        save_state_to_redis(task_id, current_state)
        
        return {"task_id": task_id, "state": state}
    
    def get_updated_state(self, task_id: str) -> Dict[str, Any]:
        """Get the current state for a task."""
        saved_state = get_state_from_redis(task_id)
        return {"task_id": task_id, "state": saved_state}
    
    # ============ Agent-Specific Methods ============
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get status of all agents.
        
        Returns:
            Dict with agent status information
        """
        if self.use_agents and self._agentic_system:
            return self._agentic_system.get_system_status()
        return {"agents": {}, "use_agents": False}
    
    def get_session_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return self._sessions.get(task_id)
    
    def is_using_agents(self) -> bool:
        """Check if agent mode is active."""
        return self.use_agents and self._agentic_system is not None
