"""
DevPilot UI Components Library

Provides reusable, real-time UI components for the Streamlit application.
"""

from src.dev_pilot.ui.streamlit_ui.components.state_manager import (
    StateManager,
    initialize_enhanced_session,
    sync_state_from_backend,
    get_current_stage,
    get_stage_status,
)
from src.dev_pilot.ui.streamlit_ui.components.progress_tracker import (
    ProgressTracker,
    render_progress_tracker,
)
from src.dev_pilot.ui.streamlit_ui.components.agent_dashboard import (
    AgentDashboard,
    render_agent_dashboard,
)
from src.dev_pilot.ui.streamlit_ui.components.integrations_panel import (
    IntegrationsPanel,
    render_integrations_panel,
)
from src.dev_pilot.ui.streamlit_ui.components.artifact_viewer import (
    ArtifactViewer,
    render_artifact_viewer,
)
from src.dev_pilot.ui.streamlit_ui.components.notifications import (
    NotificationManager,
    show_toast,
    notify_stage_change,
)
from src.dev_pilot.ui.streamlit_ui.components.workflow_graph import (
    WorkflowGraph,
    render_workflow_graph,
)
from src.dev_pilot.ui.streamlit_ui.components.enhanced_sidebar import (
    render_enhanced_sidebar,
    render_agent_mini_status,
    render_integration_status,
)

__all__ = [
    # State Management
    "StateManager",
    "initialize_enhanced_session",
    "sync_state_from_backend",
    "get_current_stage",
    "get_stage_status",
    # Progress Tracker
    "ProgressTracker",
    "render_progress_tracker",
    # Agent Dashboard
    "AgentDashboard",
    "render_agent_dashboard",
    # Integrations
    "IntegrationsPanel",
    "render_integrations_panel",
    # Artifacts
    "ArtifactViewer",
    "render_artifact_viewer",
    # Notifications
    "NotificationManager",
    "show_toast",
    "notify_stage_change",
    # Workflow Graph
    "WorkflowGraph",
    "render_workflow_graph",
    # Sidebar
    "render_enhanced_sidebar",
    "render_agent_mini_status",
    "render_integration_status",
]
