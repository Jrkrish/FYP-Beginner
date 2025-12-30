from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import asyncio
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from functools import lru_cache
from pydantic import BaseModel
from src.dev_pilot.LLMS.groqllm import GroqLLM
from src.dev_pilot.LLMS.geminillm import GeminiLLM
from src.dev_pilot.graph.graph_builder import GraphBuilder
from src.dev_pilot.graph.graph_executor import GraphExecutor
from src.dev_pilot.graph.agentic_executor import AgenticGraphExecutor
from src.dev_pilot.dto.sdlc_request import SDLCRequest
from src.dev_pilot.dto.sdlc_response import SDLCResponse
import uvicorn
from contextlib import asynccontextmanager
from src.dev_pilot.utils.logging_config import setup_logging
from loguru import logger

## Setup logging level
setup_logging(log_level="DEBUG")

gemini_models = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro-exp-03-25"
]

# Updated Groq models - removed deprecated gemma2-9b-it
groq_models = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768"
]


# ============ New Request/Response Models for Agent API ============

class CreateProjectRequest(BaseModel):
    """Request to create a new project."""
    project_name: str
    requirements: Optional[List[str]] = None
    use_agents: bool = True


class ProjectResponse(BaseModel):
    """Response for project operations."""
    status: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    message: str
    data: Optional[Dict[str, Any]] = None


class ApproveStageRequest(BaseModel):
    """Request to approve a stage."""
    task_id: str
    feedback: Optional[str] = None


class RejectStageRequest(BaseModel):
    """Request to reject a stage with feedback."""
    task_id: str
    feedback: str


class AgentStatusResponse(BaseModel):
    """Response for agent status."""
    agents: Dict[str, Any]
    system_status: Dict[str, Any]


# ============ WebSocket Connection Manager ============

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.task_subscriptions: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if task_id:
            if task_id not in self.task_subscriptions:
                self.task_subscriptions[task_id] = []
            self.task_subscriptions[task_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, task_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if task_id and task_id in self.task_subscriptions:
            if websocket in self.task_subscriptions[task_id]:
                self.task_subscriptions[task_id].remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass
    
    async def send_to_task(self, task_id: str, message: dict):
        if task_id in self.task_subscriptions:
            for connection in self.task_subscriptions[task_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


ws_manager = ConnectionManager()

def load_app():
     uvicorn.run(app, host="0.0.0.0", port=8000)

class Settings:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")        

@lru_cache()
def get_settings():
    return Settings()

def validate_api_keys(settings: Settings = Depends(get_settings)):
    required_keys = {
        'GEMINI_API_KEY': settings.GEMINI_API_KEY,
        'GROQ_API_KEY': settings.GROQ_API_KEY
    }
    
    missing_keys = [key for key, value in required_keys.items() if not value]
    if missing_keys:
        raise HTTPException(
            status_code=500,
            detail=f"Missing required API keys: {', '.join(missing_keys)}"
        )
    return settings


# Initialize the LLM and GraphBuilder instances once and store them in the app state
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    llm = GeminiLLM(model=gemini_models[0], api_key=settings.GEMINI_API_KEY).get_llm_model()
    
    # Legacy graph setup
    graph_builder = GraphBuilder(llm=llm)
    graph = graph_builder.setup_graph()
    graph_executor = GraphExecutor(graph)
    
    # New agentic executor (with fallback to legacy graph)
    agentic_executor = AgenticGraphExecutor(
        llm=llm,
        use_agents=True,
        fallback_graph=graph,
    )
    
    app.state.llm = llm
    app.state.graph = graph
    app.state.graph_executor = graph_executor
    app.state.agentic_executor = agentic_executor
    
    logger.info("Application initialized with both legacy and agentic executors")
    yield
    
    # Clean up resources
    app.state.llm = None
    app.state.graph = None
    app.state.graph_executor = None
    app.state.agentic_executor = None

app = FastAPI(
    title="DevPilot API",
    description="AI-powered SDLC API using Langgraph",
    version="1.0.0",
    lifespan=lifespan
)

logger.info("Application starting up...")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to DevPilot API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

@app.post("/api/v1/sdlc/start", response_model=SDLCResponse)
async def start_sdlc(
    sdlc_request: SDLCRequest,
    settings: Settings = Depends(validate_api_keys)
    ):

    try:
        graph_executor = app.state.graph_executor
        
        if isinstance (graph_executor, GraphExecutor) == False:
            raise Exception("Graph Executor not initialized")
        
        graph_response = graph_executor.start_workflow(sdlc_request.project_name)
        
        logger.debug(f"Start Workflow Response: {graph_response}")
        
        return SDLCResponse(
            status="success",
            message="SDLC process started successfully",
            task_id=graph_response["task_id"],
            state=graph_response["state"]
        )
    
    except Exception as e:
        error_response = SDLCResponse(
            status="error",
            message="Failed to start the process",
            error=str(e)
        )
        return JSONResponse(status_code=500, content=error_response.model_dump())
    
    
@app.post("/api/v1/sdlc/user_stories", response_model=SDLCResponse)
async def start_sdlc(
    sdlc_request: SDLCRequest,
    settings: Settings = Depends(validate_api_keys)
    ):

    try:
        graph_executor = app.state.graph_executor
        
        if isinstance (graph_executor, GraphExecutor) == False:
            raise Exception("Graph Executor not initialized")
        
        graph_response = graph_executor.generate_stories(sdlc_request.task_id, sdlc_request.requirements)
        
        logger.debug(f"Generate Stories Response: {graph_response}")
        
        return SDLCResponse(
            status="success",
            message="User Stories generated successfully",
            task_id=graph_response["task_id"],
            state=graph_response["state"]
        )
    
    except Exception as e:
        error_response = SDLCResponse(
            status="error",
            message="Failed to generate user stories",
            error=str(e)
        )
        return JSONResponse(status_code=500, content=error_response.model_dump())
    

@app.post("/api/v1/sdlc/progress_flow", response_model=SDLCResponse)
async def progress_sdlc(
    sdlc_request: SDLCRequest,
    settings: Settings = Depends(validate_api_keys)
    ):

    try:

        graph_executor = app.state.graph_executor
        
        if isinstance (graph_executor, GraphExecutor) == False:
            raise Exception("Graph Executor not initialized")
        
        graph_response = graph_executor.graph_review_flow(
            sdlc_request.task_id, 
            sdlc_request.status, 
            sdlc_request.feedback,
            sdlc_request.next_node)
        
        logger.debug(f"Flow Node: {sdlc_request.next_node}")
        logger.debug(f"Progress Flow Response: {graph_response}")
        
        return SDLCResponse(
            status="success",
            message="Flow progressed successfully to next step",
            task_id=graph_response["task_id"],
            state=graph_response["state"]
        )
    
    except Exception as e:
        error_response = SDLCResponse(
            status="error",
            message="Failed to progress the flow",
            error=str(e)
        )
        return JSONResponse(status_code=500, content=error_response.model_dump())


# ============ API v2: Agent-Based Endpoints ============

@app.post("/api/v2/projects", response_model=ProjectResponse)
async def create_project_v2(
    request: CreateProjectRequest,
    settings: Settings = Depends(validate_api_keys)
):
    """
    Create a new project using the multi-agent system.
    
    This endpoint uses the new agentic executor which leverages
    specialized AI agents for each phase of the SDLC.
    """
    try:
        agentic_executor = app.state.agentic_executor
        
        if not isinstance(agentic_executor, AgenticGraphExecutor):
            raise Exception("Agentic Executor not initialized")
        
        # Start workflow
        result = agentic_executor.start_workflow(request.project_name)
        
        # If requirements provided, generate stories immediately
        if request.requirements:
            result = agentic_executor.generate_stories(
                result["task_id"],
                request.requirements
            )
        
        # Notify via WebSocket
        await ws_manager.broadcast({
            "type": "project_created",
            "task_id": result["task_id"],
            "project_name": request.project_name,
        })
        
        return ProjectResponse(
            status="success",
            task_id=result["task_id"],
            message="Project created successfully with agent system",
            data={"state": result.get("state", {})}
        )
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        return JSONResponse(
            status_code=500,
            content=ProjectResponse(
                status="error",
                message=f"Failed to create project: {str(e)}"
            ).model_dump()
        )


@app.get("/api/v2/projects/{task_id}/status", response_model=ProjectResponse)
async def get_project_status_v2(
    task_id: str,
    settings: Settings = Depends(validate_api_keys)
):
    """Get the current status of a project."""
    try:
        agentic_executor = app.state.agentic_executor
        
        if not isinstance(agentic_executor, AgenticGraphExecutor):
            raise Exception("Agentic Executor not initialized")
        
        result = agentic_executor.get_updated_state(task_id)
        session_info = agentic_executor.get_session_info(task_id)
        
        return ProjectResponse(
            status="success",
            task_id=task_id,
            message="Project status retrieved",
            data={
                "state": result.get("state", {}),
                "session": session_info,
                "using_agents": agentic_executor.is_using_agents(),
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get project status: {e}")
        return JSONResponse(
            status_code=500,
            content=ProjectResponse(
                status="error",
                message=f"Failed to get status: {str(e)}"
            ).model_dump()
        )


@app.post("/api/v2/projects/{task_id}/approve", response_model=ProjectResponse)
async def approve_stage_v2(
    task_id: str,
    request: ApproveStageRequest,
    settings: Settings = Depends(validate_api_keys)
):
    """Approve the current stage and progress to the next."""
    try:
        agentic_executor = app.state.agentic_executor
        
        if not isinstance(agentic_executor, AgenticGraphExecutor):
            raise Exception("Agentic Executor not initialized")
        
        # Get current state to determine review type
        current = agentic_executor.get_updated_state(task_id)
        state = current.get("state", {})
        next_node = state.get("next_node", "")
        
        result = agentic_executor.graph_review_flow(
            task_id=task_id,
            status="approved",
            feedback=request.feedback,
            review_type=next_node,
        )
        
        # Notify via WebSocket
        await ws_manager.send_to_task(task_id, {
            "type": "stage_approved",
            "task_id": task_id,
            "stage": next_node,
        })
        
        return ProjectResponse(
            status="success",
            task_id=task_id,
            message=f"Stage '{next_node}' approved",
            data={"state": result.get("state", {})}
        )
        
    except Exception as e:
        logger.error(f"Failed to approve stage: {e}")
        return JSONResponse(
            status_code=500,
            content=ProjectResponse(
                status="error",
                message=f"Failed to approve: {str(e)}"
            ).model_dump()
        )


@app.post("/api/v2/projects/{task_id}/reject", response_model=ProjectResponse)
async def reject_stage_v2(
    task_id: str,
    request: RejectStageRequest,
    settings: Settings = Depends(validate_api_keys)
):
    """Reject the current stage with feedback for revision."""
    try:
        agentic_executor = app.state.agentic_executor
        
        if not isinstance(agentic_executor, AgenticGraphExecutor):
            raise Exception("Agentic Executor not initialized")
        
        # Get current state to determine review type
        current = agentic_executor.get_updated_state(task_id)
        state = current.get("state", {})
        next_node = state.get("next_node", "")
        
        result = agentic_executor.graph_review_flow(
            task_id=task_id,
            status="feedback",
            feedback=request.feedback,
            review_type=next_node,
        )
        
        # Notify via WebSocket
        await ws_manager.send_to_task(task_id, {
            "type": "stage_rejected",
            "task_id": task_id,
            "stage": next_node,
            "feedback": request.feedback,
        })
        
        return ProjectResponse(
            status="success",
            task_id=task_id,
            message=f"Stage '{next_node}' rejected for revision",
            data={"state": result.get("state", {})}
        )
        
    except Exception as e:
        logger.error(f"Failed to reject stage: {e}")
        return JSONResponse(
            status_code=500,
            content=ProjectResponse(
                status="error",
                message=f"Failed to reject: {str(e)}"
            ).model_dump()
        )


@app.get("/api/v2/agents/status")
async def get_agents_status(
    settings: Settings = Depends(validate_api_keys)
):
    """Get status of all agents in the system."""
    try:
        agentic_executor = app.state.agentic_executor
        
        if not isinstance(agentic_executor, AgenticGraphExecutor):
            return {
                "status": "legacy_mode",
                "message": "Running in legacy mode without agents",
                "agents": {}
            }
        
        status = agentic_executor.get_agent_status()
        
        return {
            "status": "success",
            "using_agents": agentic_executor.is_using_agents(),
            "system_status": status,
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


# ============ WebSocket Endpoint for Real-Time Updates ============

@app.websocket("/ws/agents")
async def websocket_agents(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent updates.
    
    Clients can subscribe to receive updates about:
    - Agent status changes
    - Workflow progress
    - Stage completions
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            # Handle subscription to specific task
            if data.get("action") == "subscribe" and data.get("task_id"):
                task_id = data["task_id"]
                if task_id not in ws_manager.task_subscriptions:
                    ws_manager.task_subscriptions[task_id] = []
                if websocket not in ws_manager.task_subscriptions[task_id]:
                    ws_manager.task_subscriptions[task_id].append(websocket)
                await websocket.send_json({
                    "type": "subscribed",
                    "task_id": task_id,
                })
            
            # Handle unsubscribe
            elif data.get("action") == "unsubscribe" and data.get("task_id"):
                task_id = data["task_id"]
                if task_id in ws_manager.task_subscriptions:
                    if websocket in ws_manager.task_subscriptions[task_id]:
                        ws_manager.task_subscriptions[task_id].remove(websocket)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "task_id": task_id,
                })
            
            # Handle status request
            elif data.get("action") == "get_status":
                agentic_executor = app.state.agentic_executor
                if isinstance(agentic_executor, AgenticGraphExecutor):
                    status = agentic_executor.get_agent_status()
                    await websocket.send_json({
                        "type": "status",
                        "data": status,
                    })
                else:
                    await websocket.send_json({
                        "type": "status",
                        "data": {"mode": "legacy"},
                    })
            
            # Echo ping for keepalive
            elif data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@app.websocket("/ws/projects/{task_id}")
async def websocket_project(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for project-specific updates.
    
    Automatically subscribes to updates for the given task_id.
    """
    await ws_manager.connect(websocket, task_id)
    try:
        # Send initial state
        agentic_executor = app.state.agentic_executor
        if isinstance(agentic_executor, AgenticGraphExecutor):
            result = agentic_executor.get_updated_state(task_id)
            await websocket.send_json({
                "type": "initial_state",
                "task_id": task_id,
                "state": result.get("state", {}),
            })
        
        while True:
            data = await websocket.receive_json()
            
            # Handle ping
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
            
            # Handle refresh request
            elif data.get("action") == "refresh":
                if isinstance(agentic_executor, AgenticGraphExecutor):
                    result = agentic_executor.get_updated_state(task_id)
                    await websocket.send_json({
                        "type": "state_update",
                        "task_id": task_id,
                        "state": result.get("state", {}),
                    })
                    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        ws_manager.disconnect(websocket, task_id)


# ============ Health Check Endpoint ============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    agentic_executor = getattr(app.state, 'agentic_executor', None)
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "legacy_executor": app.state.graph_executor is not None,
            "agentic_executor": agentic_executor is not None,
            "using_agents": agentic_executor.is_using_agents() if agentic_executor else False,
        }
    }