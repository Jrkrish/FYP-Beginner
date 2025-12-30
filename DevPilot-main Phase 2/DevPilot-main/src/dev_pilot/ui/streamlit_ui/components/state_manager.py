"""
State Manager Component

Provides centralized state management utilities for the enhanced UI.
Handles session state, backend synchronization, and real-time updates.
"""

import streamlit as st
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from loguru import logger
import src.dev_pilot.utils.constants as const


# Stage configuration with icons and display names
STAGE_CONFIG = {
    const.PROJECT_INITILIZATION: {
        "name": "Initialize",
        "icon": "🎯",
        "index": 0,
    },
    const.REQUIREMENT_COLLECTION: {
        "name": "Requirements",
        "icon": "📋",
        "index": 1,
    },
    const.GENERATE_USER_STORIES: {
        "name": "User Stories",
        "icon": "📖",
        "index": 2,
    },
    const.CREATE_DESIGN_DOC: {
        "name": "Design",
        "icon": "🏗️",
        "index": 3,
    },
    const.CODE_GENERATION: {
        "name": "Code",
        "icon": "💻",
        "index": 4,
    },
    const.SECURITY_REVIEW: {
        "name": "Security",
        "icon": "🔒",
        "index": 5,
    },
    const.WRITE_TEST_CASES: {
        "name": "Testing",
        "icon": "🧪",
        "index": 6,
    },
    const.QA_TESTING: {
        "name": "QA",
        "icon": "✅",
        "index": 7,
    },
    const.DEPLOYMENT: {
        "name": "Deploy",
        "icon": "🚀",
        "index": 8,
    },
    const.ARTIFACTS: {
        "name": "Complete",
        "icon": "🎉",
        "index": 9,
    },
}

# Agent icons mapping
AGENT_ICONS = {
    "supervisor": "🎯",
    "business_analyst": "📋",
    "architect": "🏗️",
    "developer": "💻",
    "code_review": "🔍",
    "security": "🔒",
    "qa": "🧪",
    "devops": "🚀",
}

# Agent state colors
STATE_COLORS = {
    "idle": "#a0aec0",
    "working": "#3182ce",
    "completed": "#48bb78",
    "error": "#e53e3e",
    "blocked": "#ed8936",
}

# Integration icons
INTEGRATION_ICONS = {
    "slack": "💬",
    "jira": "📋",
    "github": "🐙",
    "webhook": "🔔",
}


class StateManager:
    """
    Manages UI state and synchronization with backend.
    
    Provides:
    - Session state initialization
    - Backend state synchronization
    - Stage status tracking
    - Event notifications
    """
    
    def __init__(self, graph_executor: Any = None):
        """
        Initialize the state manager.
        
        Args:
            graph_executor: Reference to the graph executor
        """
        self.graph_executor = graph_executor
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def initialize(self):
        """Initialize enhanced session state."""
        initialize_enhanced_session()
    
    def sync_state(self) -> bool:
        """
        Synchronize state from backend.
        
        Returns:
            True if state changed
        """
        if self.graph_executor and st.session_state.get("task_id"):
            return sync_state_from_backend(self.graph_executor)
        return False
    
    def get_current_stage(self) -> str:
        """Get current SDLC stage."""
        return get_current_stage()
    
    def get_stage_status(self, stage: str) -> str:
        """Get status for a specific stage."""
        return get_stage_status(stage)
    
    def get_all_stage_statuses(self) -> Dict[str, str]:
        """Get statuses for all stages."""
        current = self.get_current_stage()
        current_index = STAGE_CONFIG.get(current, {}).get("index", 0)
        
        statuses = {}
        for stage, config in STAGE_CONFIG.items():
            stage_index = config.get("index", 0)
            if stage_index < current_index:
                statuses[stage] = "completed"
            elif stage_index == current_index:
                statuses[stage] = "current"
            else:
                statuses[stage] = "pending"
        
        return statuses
    
    def on_stage_change(self, callback: Callable):
        """Register callback for stage changes."""
        if "stage_change" not in self._callbacks:
            self._callbacks["stage_change"] = []
        self._callbacks["stage_change"].append(callback)
    
    def notify_stage_change(self, old_stage: str, new_stage: str, status: str):
        """Notify listeners of stage change."""
        for callback in self._callbacks.get("stage_change", []):
            try:
                callback(old_stage, new_stage, status)
            except Exception as e:
                logger.error(f"Stage change callback failed: {e}")


def initialize_enhanced_session():
    """
    Initialize enhanced session state structure.
    
    This sets up all necessary state variables for the enhanced UI.
    """
    # Core SDLC state
    if "stage" not in st.session_state:
        st.session_state.stage = const.PROJECT_INITILIZATION
    
    if "project_name" not in st.session_state:
        st.session_state.project_name = ""
    
    if "requirements" not in st.session_state:
        st.session_state.requirements = []
    
    if "task_id" not in st.session_state:
        st.session_state.task_id = ""
    
    if "state" not in st.session_state:
        st.session_state.state = {}
    
    if "use_agents" not in st.session_state:
        st.session_state.use_agents = True
    
    # Enhanced UI state
    if "ui_state" not in st.session_state:
        st.session_state.ui_state = {
            "last_refresh": datetime.now(),
            "pending_notifications": [],
            "agent_cache": {},
            "integration_cache": {},
            "artifact_versions": {},
            "activity_log": [],
            "theme": "light",
            "sidebar_expanded": True,
        }
    
    # Refresh triggers for auto-update
    if "refresh_triggers" not in st.session_state:
        st.session_state.refresh_triggers = {
            "agent_dashboard": 0,
            "integrations": 0,
            "artifacts": 0,
            "workflow": 0,
        }
    
    # Integration configurations
    if "integrations" not in st.session_state:
        st.session_state.integrations = {
            "slack": {"enabled": False, "config": {}},
            "jira": {"enabled": False, "config": {}},
            "github": {"enabled": False, "config": {}},
            "webhook": {"enabled": False, "config": {}},
        }
    
    # Notification queue
    if "notifications" not in st.session_state:
        st.session_state.notifications = []
    
    # Stage history for tracking transitions
    if "stage_history" not in st.session_state:
        st.session_state.stage_history = []


def sync_state_from_backend(graph_executor: Any) -> bool:
    """
    Synchronize state from backend.
    
    Args:
        graph_executor: Reference to the graph executor
        
    Returns:
        True if state changed, False otherwise
    """
    task_id = st.session_state.get("task_id")
    if not task_id:
        return False
    
    try:
        response = graph_executor.get_updated_state(task_id)
        new_state = response.get("state", {})
        
        # Check if state changed
        old_state = st.session_state.get("state", {})
        state_changed = new_state != old_state
        
        if state_changed:
            st.session_state.state = new_state
            st.session_state.ui_state["last_refresh"] = datetime.now()
            
            # Track stage transitions
            old_stage = st.session_state.get("stage")
            new_stage = detect_stage_from_state(new_state)
            
            if new_stage and new_stage != old_stage:
                st.session_state.stage_history.append({
                    "from": old_stage,
                    "to": new_stage,
                    "timestamp": datetime.now().isoformat(),
                })
                st.session_state.stage = new_stage
        
        return state_changed
        
    except Exception as e:
        logger.error(f"State sync failed: {e}")
        return False


def detect_stage_from_state(state: Dict[str, Any]) -> Optional[str]:
    """
    Detect current stage from state dictionary.
    
    Args:
        state: Current state dictionary
        
    Returns:
        Detected stage constant or None
    """
    next_node = state.get("next_node", "")
    
    # Map next_node to stage
    node_to_stage = {
        const.REVIEW_USER_STORIES: const.GENERATE_USER_STORIES,
        const.REVIEW_DESIGN_DOCUMENTS: const.CREATE_DESIGN_DOC,
        const.REVIEW_CODE: const.CODE_GENERATION,
        const.REVIEW_SECURITY_RECOMMENDATIONS: const.SECURITY_REVIEW,
        const.REVIEW_TEST_CASES: const.WRITE_TEST_CASES,
        const.REVIEW_QA_TESTING: const.QA_TESTING,
        const.END_NODE: const.DEPLOYMENT,
    }
    
    return node_to_stage.get(next_node)


def get_current_stage() -> str:
    """
    Get the current SDLC stage.
    
    Returns:
        Current stage constant
    """
    return st.session_state.get("stage", const.PROJECT_INITILIZATION)


def get_stage_status(stage: str) -> str:
    """
    Get status for a specific stage.
    
    Args:
        stage: Stage constant
        
    Returns:
        Status string: "completed", "current", "pending", "error"
    """
    current = get_current_stage()
    current_index = STAGE_CONFIG.get(current, {}).get("index", 0)
    stage_index = STAGE_CONFIG.get(stage, {}).get("index", 0)
    
    if stage_index < current_index:
        return "completed"
    elif stage_index == current_index:
        return "current"
    else:
        return "pending"


def get_stage_config(stage: str) -> Dict[str, Any]:
    """
    Get configuration for a stage.
    
    Args:
        stage: Stage constant
        
    Returns:
        Stage configuration dictionary
    """
    return STAGE_CONFIG.get(stage, {
        "name": stage,
        "icon": "📄",
        "index": -1,
    })


def get_progress_percentage() -> int:
    """
    Calculate overall progress percentage.
    
    Returns:
        Progress as percentage (0-100)
    """
    current = get_current_stage()
    current_index = STAGE_CONFIG.get(current, {}).get("index", 0)
    total_stages = len(STAGE_CONFIG) - 1  # Exclude initialization
    
    if total_stages <= 0:
        return 0
    
    return min(100, int((current_index / total_stages) * 100))


def add_notification(message: str, type: str = "info"):
    """
    Add a notification to the queue.
    
    Args:
        message: Notification message
        type: Notification type (success, warning, error, info)
    """
    notification = {
        "id": f"notif_{datetime.now().timestamp()}",
        "message": message,
        "type": type,
        "timestamp": datetime.now().isoformat(),
        "read": False,
    }
    
    if "notifications" not in st.session_state:
        st.session_state.notifications = []
    
    st.session_state.notifications.insert(0, notification)
    
    # Keep only last 50 notifications
    st.session_state.notifications = st.session_state.notifications[:50]


def get_unread_notifications() -> List[Dict[str, Any]]:
    """
    Get unread notifications.
    
    Returns:
        List of unread notifications
    """
    return [
        n for n in st.session_state.get("notifications", [])
        if not n.get("read", False)
    ]


def mark_notification_read(notification_id: str):
    """
    Mark a notification as read.
    
    Args:
        notification_id: ID of the notification
    """
    for notification in st.session_state.get("notifications", []):
        if notification.get("id") == notification_id:
            notification["read"] = True
            break


def add_activity_log(activity: str, agent: str = None, type: str = "info"):
    """
    Add an activity to the log.
    
    Args:
        activity: Activity description
        agent: Agent that performed the activity
        type: Activity type
    """
    log_entry = {
        "activity": activity,
        "agent": agent,
        "type": type,
        "timestamp": datetime.now().isoformat(),
    }
    
    if "ui_state" not in st.session_state:
        st.session_state.ui_state = {"activity_log": []}
    
    if "activity_log" not in st.session_state.ui_state:
        st.session_state.ui_state["activity_log"] = []
    
    st.session_state.ui_state["activity_log"].insert(0, log_entry)
    
    # Keep only last 100 activities
    st.session_state.ui_state["activity_log"] = \
        st.session_state.ui_state["activity_log"][:100]


def get_activity_log(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent activity log entries.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of activity log entries
    """
    return st.session_state.get("ui_state", {}).get("activity_log", [])[:limit]


def trigger_refresh(component: str):
    """
    Trigger a refresh for a specific component.
    
    Args:
        component: Component name to refresh
    """
    if "refresh_triggers" not in st.session_state:
        st.session_state.refresh_triggers = {}
    
    current = st.session_state.refresh_triggers.get(component, 0)
    st.session_state.refresh_triggers[component] = current + 1
