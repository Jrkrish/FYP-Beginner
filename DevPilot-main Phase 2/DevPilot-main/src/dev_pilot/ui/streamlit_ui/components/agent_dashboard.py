"""
Agent Dashboard Component

Real-time monitoring dashboard for AI agents with live status updates,
activity feeds, and performance metrics.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from src.dev_pilot.ui.streamlit_ui.components.state_manager import (
    AGENT_ICONS,
    STATE_COLORS,
    add_activity_log,
    get_activity_log,
)


# Agent type configurations
AGENT_CONFIGS = {
    "supervisor": {
        "name": "Supervisor Agent",
        "description": "Orchestrates workflow and coordinates other agents",
        "icon": "🎯",
        "color": "#6B46C1",
    },
    "business_analyst": {
        "name": "Business Analyst",
        "description": "Analyzes requirements and generates user stories",
        "icon": "📋",
        "color": "#2B6CB0",
    },
    "architect": {
        "name": "Architect Agent",
        "description": "Creates system design and architecture documents",
        "icon": "🏗️",
        "color": "#2C7A7B",
    },
    "developer": {
        "name": "Developer Agent",
        "description": "Generates code based on requirements and design",
        "icon": "💻",
        "color": "#276749",
    },
    "code_review": {
        "name": "Code Review Agent",
        "description": "Reviews code quality and suggests improvements",
        "icon": "🔍",
        "color": "#744210",
    },
    "security": {
        "name": "Security Agent",
        "description": "Analyzes security vulnerabilities and risks",
        "icon": "🔒",
        "color": "#C53030",
    },
    "qa": {
        "name": "QA Agent",
        "description": "Creates test cases and performs quality assurance",
        "icon": "🧪",
        "color": "#553C9A",
    },
    "devops": {
        "name": "DevOps Agent",
        "description": "Handles deployment and CI/CD configuration",
        "icon": "🚀",
        "color": "#2D3748",
    },
}


class AgentDashboard:
    """
    Real-time agent monitoring dashboard.
    
    Provides:
    - System health overview
    - Live agent status cards
    - Activity timeline
    - Performance metrics
    """
    
    def __init__(self, graph_executor: Any = None):
        """
        Initialize the dashboard.
        
        Args:
            graph_executor: Reference to the graph executor
        """
        self.graph_executor = graph_executor
    
    def render(self):
        """Render the complete agent dashboard."""
        st.markdown(self._get_dashboard_css(), unsafe_allow_html=True)
        
        # Check if using agent mode
        if self._is_agent_mode():
            self._render_active_dashboard()
        else:
            self._render_inactive_dashboard()
    
    def _is_agent_mode(self) -> bool:
        """Check if agent mode is active."""
        from src.dev_pilot.graph.agentic_executor import AgenticGraphExecutor
        return (
            isinstance(self.graph_executor, AgenticGraphExecutor) and 
            self.graph_executor.is_using_agents()
        )
    
    def _render_active_dashboard(self):
        """Render dashboard when agent mode is active."""
        # Get agent status
        try:
            agent_status = self.graph_executor.get_agent_status()
        except Exception as e:
            st.error(f"Failed to get agent status: {e}")
            agent_status = {"agents": {}}
        
        # System Overview
        self._render_system_overview(agent_status)
        
        st.divider()
        
        # Agent Cards Grid
        self._render_agent_grid(agent_status.get("agents", {}))
        
        st.divider()
        
        # Activity Feed and Metrics
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_activity_feed()
        
        with col2:
            self._render_quick_metrics(agent_status)
    
    def _render_inactive_dashboard(self):
        """Render dashboard when agent mode is inactive."""
        st.warning("⚠️ Agent mode is not active. Enable 'Use AI Agents' in the sidebar.")
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
                    border-radius: 12px; padding: 24px; margin-top: 16px;">
            <h4 style="margin: 0 0 16px 0; color: #2d3748;">Available Agents</h4>
            <p style="color: #718096; margin-bottom: 16px;">
                When enabled, the following specialized AI agents will handle your SDLC workflow:
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display available agents
        cols = st.columns(4)
        for i, (agent_type, config) in enumerate(AGENT_CONFIGS.items()):
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background: white; border-radius: 10px; padding: 16px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 12px;
                            border-left: 3px solid {config['color']};">
                    <div style="font-size: 24px; margin-bottom: 8px;">{config['icon']}</div>
                    <div style="font-weight: 600; font-size: 13px; color: #2d3748;">
                        {config['name']}
                    </div>
                    <div style="font-size: 11px; color: #718096; margin-top: 4px;">
                        {config['description']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    def _render_system_overview(self, agent_status: Dict[str, Any]):
        """Render system overview metrics."""
        st.subheader("📊 System Overview")
        
        agents = agent_status.get("agents", {})
        registry = agent_status.get("registry", {})
        message_bus = agent_status.get("message_bus", {})
        
        # Count agent states
        active_count = sum(1 for a in agents.values() if a.get("state") == "working")
        idle_count = sum(1 for a in agents.values() if a.get("state") == "idle")
        error_count = sum(1 for a in agents.values() if a.get("state") == "error")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            self._render_metric_card(
                "Total Agents",
                str(len(agents)),
                "🤖",
                "#0062E6"
            )
        
        with col2:
            self._render_metric_card(
                "Active",
                str(active_count),
                "🔵",
                "#3182ce"
            )
        
        with col3:
            self._render_metric_card(
                "Idle",
                str(idle_count),
                "⚪",
                "#a0aec0"
            )
        
        with col4:
            self._render_metric_card(
                "Errors",
                str(error_count),
                "🔴",
                "#e53e3e"
            )
        
        with col5:
            messages = message_bus.get("messages_processed", 0)
            self._render_metric_card(
                "Messages",
                str(messages),
                "📨",
                "#805ad5"
            )
    
    def _render_metric_card(self, label: str, value: str, icon: str, color: str):
        """Render a metric card."""
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {color}15 0%, {color}08 100%);
                    border-radius: 12px; padding: 16px; text-align: center;
                    border: 1px solid {color}30;">
            <div style="font-size: 28px; margin-bottom: 4px;">{icon}</div>
            <div style="font-size: 24px; font-weight: 700; color: {color};">{value}</div>
            <div style="font-size: 12px; color: #718096; margin-top: 4px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_agent_grid(self, agents: Dict[str, Any]):
        """Render grid of agent cards."""
        st.subheader("🤖 Agent Status")
        
        if not agents:
            st.info("No agents currently active. Start a project to activate agents.")
            return
        
        # Create grid
        cols = st.columns(2)
        
        for i, (agent_type, agent_info) in enumerate(agents.items()):
            with cols[i % 2]:
                self._render_agent_card(agent_type, agent_info)
    
    def _render_agent_card(self, agent_type: str, agent_info: Dict[str, Any]):
        """Render a single agent card."""
        config = AGENT_CONFIGS.get(agent_type, {
            "name": agent_type.replace("_", " ").title(),
            "icon": "🤖",
            "color": "#718096",
            "description": "Agent",
        })
        
        state = agent_info.get("state", "unknown")
        state_color = STATE_COLORS.get(state, "#718096")
        metrics = agent_info.get("metrics", {})
        
        # State indicator
        state_indicator = {
            "idle": "⚪",
            "working": "🔵",
            "completed": "🟢",
            "error": "🔴",
            "blocked": "🟡",
        }.get(state, "⚫")
        
        current_task = agent_info.get("current_task", "No active task")
        tasks_completed = metrics.get("tasks_completed", 0)
        tasks_failed = metrics.get("tasks_failed", 0)
        messages_sent = metrics.get("messages_sent", 0)
        
        # Calculate progress
        total_tasks = tasks_completed + tasks_failed
        progress = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
        
        with st.container():
            st.markdown(f"""
            <div class="agent-card" style="border-left-color: {config['color']};">
                <div class="agent-header">
                    <div class="agent-icon-name">
                        <span class="agent-icon">{config['icon']}</span>
                        <span class="agent-name">{config['name']}</span>
                    </div>
                    <div class="agent-status">
                        <span class="status-dot" style="background: {state_color};"></span>
                        <span class="status-text">{state.upper()}</span>
                    </div>
                </div>
                <div class="agent-body">
                    <div class="current-task">
                        <span class="task-label">Current Task:</span>
                        <span class="task-value">{current_task[:50]}{'...' if len(str(current_task)) > 50 else ''}</span>
                    </div>
                    <div class="agent-metrics">
                        <div class="metric">
                            <span class="metric-icon">✓</span>
                            <span class="metric-value">{tasks_completed}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-icon">✗</span>
                            <span class="metric-value">{tasks_failed}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-icon">📨</span>
                            <span class="metric-value">{messages_sent}</span>
                        </div>
                    </div>
                    <div class="agent-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {progress}%; background: {config['color']};"></div>
                        </div>
                        <span class="progress-text">{int(progress)}%</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_activity_feed(self):
        """Render real-time activity feed."""
        st.subheader("📜 Activity Feed")
        
        activities = get_activity_log(limit=10)
        
        if not activities:
            st.info("No recent activity. Activities will appear here as agents work.")
            return
        
        activity_html = '<div class="activity-feed">'
        
        for activity in activities:
            agent = activity.get("agent", "System")
            agent_icon = AGENT_ICONS.get(agent, "📌")
            activity_type = activity.get("type", "info")
            timestamp = activity.get("timestamp", "")
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = ""
            
            type_colors = {
                "info": "#3182ce",
                "success": "#48bb78",
                "warning": "#ed8936",
                "error": "#e53e3e",
            }
            type_color = type_colors.get(activity_type, "#718096")
            
            activity_html += f"""
            <div class="activity-item">
                <div class="activity-icon" style="background: {type_color}20; color: {type_color};">
                    {agent_icon}
                </div>
                <div class="activity-content">
                    <div class="activity-text">{activity.get('activity', '')}</div>
                    <div class="activity-meta">
                        <span class="activity-agent">{agent}</span>
                        <span class="activity-time">{time_str}</span>
                    </div>
                </div>
            </div>
            """
        
        activity_html += '</div>'
        
        st.markdown(activity_html, unsafe_allow_html=True)
    
    def _render_quick_metrics(self, agent_status: Dict[str, Any]):
        """Render quick metrics panel."""
        st.subheader("📈 Metrics")
        
        workflow_engine = agent_status.get("workflow_engine", {})
        message_bus = agent_status.get("message_bus", {})
        
        metrics = [
            ("Projects", str(agent_status.get("projects_count", 0)), "📁"),
            ("Workflows", str(workflow_engine.get("active_workflows", 0)), "🔄"),
            ("Queue Size", str(message_bus.get("queue_size", 0)), "📋"),
            ("Uptime", "Active", "⏱️"),
        ]
        
        for label, value, icon in metrics:
            st.markdown(f"""
            <div style="background: white; border-radius: 8px; padding: 12px;
                        margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                        display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 20px;">{icon}</span>
                <div>
                    <div style="font-size: 16px; font-weight: 600; color: #2d3748;">{value}</div>
                    <div style="font-size: 11px; color: #718096;">{label}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _get_dashboard_css(self) -> str:
        """Get CSS for the dashboard."""
        return """
        <style>
        .agent-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
            border-left: 4px solid #0062E6;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .agent-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .agent-icon-name {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .agent-icon {
            font-size: 24px;
        }
        
        .agent-name {
            font-weight: 600;
            font-size: 14px;
            color: #2d3748;
        }
        
        .agent-status {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: #f7fafc;
            border-radius: 20px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-text {
            font-size: 10px;
            font-weight: 600;
            color: #718096;
        }
        
        .agent-body {
            margin-top: 8px;
        }
        
        .current-task {
            font-size: 12px;
            color: #718096;
            margin-bottom: 12px;
        }
        
        .task-label {
            color: #a0aec0;
        }
        
        .task-value {
            color: #4a5568;
            margin-left: 4px;
        }
        
        .agent-metrics {
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
        }
        
        .metric {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 13px;
        }
        
        .metric-icon {
            opacity: 0.7;
        }
        
        .metric-value {
            font-weight: 600;
            color: #2d3748;
        }
        
        .agent-progress {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .agent-progress .progress-bar {
            flex: 1;
            height: 6px;
            background: #e2e8f0;
            border-radius: 3px;
            overflow: hidden;
        }
        
        .agent-progress .progress-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }
        
        .progress-text {
            font-size: 11px;
            font-weight: 600;
            color: #718096;
            min-width: 32px;
        }
        
        .activity-feed {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .activity-item {
            display: flex;
            gap: 12px;
            padding: 10px;
            background: white;
            border-radius: 8px;
            margin-bottom: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .activity-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        
        .activity-content {
            flex: 1;
        }
        
        .activity-text {
            font-size: 13px;
            color: #2d3748;
            line-height: 1.4;
        }
        
        .activity-meta {
            display: flex;
            gap: 12px;
            margin-top: 4px;
            font-size: 11px;
            color: #a0aec0;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        </style>
        """


def render_agent_dashboard(graph_executor: Any = None):
    """
    Render the agent dashboard component.
    
    Args:
        graph_executor: Reference to the graph executor
    """
    dashboard = AgentDashboard(graph_executor)
    dashboard.render()


def get_agent_summary(graph_executor: Any) -> Dict[str, Any]:
    """
    Get a summary of agent status for display in sidebar.
    
    Args:
        graph_executor: Reference to the graph executor
        
    Returns:
        Summary dictionary with agent counts and states
    """
    try:
        from src.dev_pilot.graph.agentic_executor import AgenticGraphExecutor
        
        if isinstance(graph_executor, AgenticGraphExecutor) and graph_executor.is_using_agents():
            status = graph_executor.get_agent_status()
            agents = status.get("agents", {})
            
            return {
                "total": len(agents),
                "active": sum(1 for a in agents.values() if a.get("state") == "working"),
                "idle": sum(1 for a in agents.values() if a.get("state") == "idle"),
                "error": sum(1 for a in agents.values() if a.get("state") == "error"),
                "agents": agents,
            }
    except Exception as e:
        logger.error(f"Failed to get agent summary: {e}")
    
    return {"total": 0, "active": 0, "idle": 0, "error": 0, "agents": {}}
