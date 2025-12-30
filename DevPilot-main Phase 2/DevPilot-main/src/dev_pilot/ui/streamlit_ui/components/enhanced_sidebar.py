"""
Enhanced Sidebar Component

Provides improved sidebar with live agent status, integration indicators,
quick actions, and better navigation.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
import os
from loguru import logger

from src.dev_pilot.ui.streamlit_ui.components.state_manager import (
    AGENT_ICONS,
    STATE_COLORS,
    INTEGRATION_ICONS,
    initialize_enhanced_session,
)
from src.dev_pilot.ui.streamlit_ui.components.progress_tracker import render_mini_progress
from src.dev_pilot.ui.streamlit_ui.components.workflow_graph import render_workflow_graph


def render_enhanced_sidebar(config: Any, graph_executor: Any = None) -> Dict[str, Any]:
    """
    Render enhanced sidebar with all components.
    
    Args:
        config: UI configuration object
        graph_executor: Reference to graph executor
        
    Returns:
        Dict of user control values
    """
    user_controls = {}
    
    with st.sidebar:
        # Header
        st.markdown("""
        <div style="text-align: center; padding: 10px 0 20px 0;">
            <h1 style="margin: 0; font-size: 28px;">🚀 DevPilot</h1>
            <p style="margin: 5px 0 0 0; color: #718096; font-size: 12px;">
                AI-Powered SDLC Automation
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Mini Progress Indicator
        if st.session_state.get("task_id"):
            st.markdown(render_mini_progress(), unsafe_allow_html=True)
            st.divider()
        
        # Execution Mode Toggle
        user_controls.update(render_execution_mode_toggle())
        
        st.divider()
        
        # LLM Configuration
        user_controls.update(render_llm_config(config))
        
        st.divider()
        
        # Agent Status Mini Panel
        if user_controls.get("use_agents", True):
            render_agent_mini_status(graph_executor)
            st.divider()
        
        # Integration Status
        render_integration_status()
        
        st.divider()
        
        # Quick Actions
        render_quick_actions()
        
        st.divider()
        
        # Workflow Overview
        with st.expander("📊 Workflow", expanded=False):
            render_workflow_graph(compact=True)
    
    return user_controls


def render_execution_mode_toggle() -> Dict[str, Any]:
    """
    Render execution mode toggle.
    
    Returns:
        Dict with use_agents value
    """
    st.markdown("### ⚙️ Execution Mode")
    
    use_agents = st.toggle(
        "🤖 Use AI Agents",
        value=st.session_state.get("use_agents", True),
        help="Enable multi-agent system for enhanced SDLC automation",
        key="enhanced_sidebar_use_agents_toggle"
    )
    st.session_state.use_agents = use_agents
    
    if use_agents:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #48bb7815 0%, #38a16915 100%);
                    padding: 8px 12px; border-radius: 8px; margin-top: 8px;">
            <span style="color: #48bb78; font-size: 12px;">
                🤖 Agent Mode: Specialized AI agents handle each phase
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #3182ce15 0%, #2b6cb015 100%);
                    padding: 8px 12px; border-radius: 8px; margin-top: 8px;">
            <span style="color: #3182ce; font-size: 12px;">
                📊 Legacy Mode: Traditional graph-based workflow
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    return {"use_agents": use_agents}


def render_llm_config(config: Any) -> Dict[str, Any]:
    """
    Render LLM configuration section.
    
    Args:
        config: UI configuration object
        
    Returns:
        Dict with LLM settings
    """
    user_controls = {}
    
    st.markdown("### 🧠 LLM Settings")
    
    # Get options from config
    llm_options = config.get_llm_options()
    
    # LLM selection
    user_controls["selected_llm"] = st.selectbox(
        "Select LLM",
        llm_options,
        key="llm_selector"
    )
    
    selected_llm = user_controls["selected_llm"]
    
    if selected_llm == 'Groq':
        model_options = config.get_groq_model_options()
        user_controls["selected_groq_model"] = st.selectbox(
            "Model",
            model_options,
            key="groq_model"
        )
        
        api_key = st.text_input(
            "API Key",
            type="password",
            value=os.getenv("GROQ_API_KEY", ""),
            key="groq_api_key"
        )
        os.environ["GROQ_API_KEY"] = api_key
        user_controls["GROQ_API_KEY"] = api_key
        st.session_state["GROQ_API_KEY"] = api_key
        
        if not api_key:
            st.markdown("""
            <div style="background: #fffaf0; padding: 8px 12px; border-radius: 6px;
                        border-left: 3px solid #ed8936; font-size: 11px;">
                ⚠️ <a href="https://console.groq.com/keys" target="_blank">Get GROQ API key</a>
            </div>
            """, unsafe_allow_html=True)
    
    elif selected_llm == 'Gemini':
        model_options = config.get_gemini_model_options()
        user_controls["selected_gemini_model"] = st.selectbox(
            "Model",
            model_options,
            key="gemini_model"
        )
        
        api_key = st.text_input(
            "API Key",
            type="password",
            value=os.getenv("GEMINI_API_KEY", ""),
            key="gemini_api_key"
        )
        os.environ["GEMINI_API_KEY"] = api_key
        user_controls["GEMINI_API_KEY"] = api_key
        st.session_state["GEMINI_API_KEY"] = api_key
        
        if not api_key:
            st.markdown("""
            <div style="background: #fffaf0; padding: 8px 12px; border-radius: 6px;
                        border-left: 3px solid #ed8936; font-size: 11px;">
                ⚠️ <a href="https://ai.google.dev/gemini-api/docs/api-key" target="_blank">Get Gemini API key</a>
            </div>
            """, unsafe_allow_html=True)
    
    elif selected_llm == 'OpenAI':
        model_options = config.get_openai_model_options()
        user_controls["selected_openai_model"] = st.selectbox(
            "Model",
            model_options,
            key="openai_model"
        )
        
        api_key = st.text_input(
            "API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            key="openai_api_key"
        )
        os.environ["OPENAI_API_KEY"] = api_key
        user_controls["OPENAI_API_KEY"] = api_key
        st.session_state["OPENAI_API_KEY"] = api_key
        
        if not api_key:
            st.markdown("""
            <div style="background: #fffaf0; padding: 8px 12px; border-radius: 6px;
                        border-left: 3px solid #ed8936; font-size: 11px;">
                ⚠️ <a href="https://platform.openai.com/api-keys" target="_blank">Get OpenAI API key</a>
            </div>
            """, unsafe_allow_html=True)
    
    return user_controls


def render_agent_mini_status(graph_executor: Any = None):
    """
    Render mini agent status panel.
    
    Args:
        graph_executor: Reference to graph executor
    """
    st.markdown("### 🤖 Agents")
    
    # Try to get agent status
    agents = {}
    
    if graph_executor:
        try:
            from src.dev_pilot.graph.agentic_executor import AgenticGraphExecutor
            
            if isinstance(graph_executor, AgenticGraphExecutor) and graph_executor.is_using_agents():
                status = graph_executor.get_agent_status()
                agents = status.get("agents", {})
        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
    
    if agents:
        # Render agent list
        for agent_type, info in list(agents.items())[:6]:  # Show max 6 agents
            state = info.get("state", "unknown")
            name = info.get("name", agent_type.replace("_", " ").title())
            icon = AGENT_ICONS.get(agent_type, "🤖")
            color = STATE_COLORS.get(state, "#a0aec0")
            
            st.markdown(f"""
            <div style="display: flex; align-items: center; padding: 6px 0;
                        border-bottom: 1px solid #edf2f7;">
                <span style="font-size: 16px; margin-right: 10px;">{icon}</span>
                <span style="flex: 1; font-size: 12px; color: #4a5568;">{name}</span>
                <span style="width: 10px; height: 10px; border-radius: 50%;
                             background: {color}; display: inline-block;"></span>
            </div>
            """, unsafe_allow_html=True)
        
        # Legend
        st.markdown("""
        <div style="font-size: 10px; color: #a0aec0; margin-top: 8px; text-align: center;">
            🟢 Active  🔵 Working  ⚪ Idle  🔴 Error
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: #f7fafc; padding: 12px; border-radius: 8px;
                    text-align: center; font-size: 12px; color: #718096;">
            Start a project to see agent status
        </div>
        """, unsafe_allow_html=True)


def render_integration_status():
    """Render integration status indicators."""
    st.markdown("### 🔗 Integrations")
    
    integrations = st.session_state.get("integrations", {})
    
    if not integrations:
        integrations = {
            "slack": {"enabled": False, "status": "disconnected"},
            "jira": {"enabled": False, "status": "disconnected"},
            "github": {"enabled": False, "status": "disconnected"},
            "webhook": {"enabled": False, "status": "disconnected"},
        }
    
    # Count connected
    connected_count = sum(
        1 for i in integrations.values() 
        if i.get("status") == "connected" or i.get("enabled", False)
    )
    
    # Render integration indicators
    cols = st.columns(4)
    
    for i, (name, state) in enumerate(integrations.items()):
        with cols[i]:
            icon = INTEGRATION_ICONS.get(name, "🔗")
            enabled = state.get("enabled", False)
            status = state.get("status", "disconnected")
            
            status_indicator = {
                "connected": "🟢",
                "disconnected": "🔴",
                "error": "🟡",
            }.get(status, "🔴" if not enabled else "🟢")
            
            st.markdown(f"""
            <div style="text-align: center; padding: 8px 4px;">
                <div style="font-size: 20px;">{icon}</div>
                <div style="font-size: 10px; color: #718096; margin-top: 4px;">
                    {status_indicator}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Summary
    st.markdown(f"""
    <div style="text-align: center; font-size: 11px; color: #a0aec0; margin-top: 4px;">
        {connected_count} of {len(integrations)} connected
    </div>
    """, unsafe_allow_html=True)


def render_quick_actions():
    """Render quick action buttons."""
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Reset", use_container_width=True, key="sidebar_reset"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            initialize_enhanced_session()
            st.rerun()
    
    with col2:
        if st.button("📥 Export", use_container_width=True, key="sidebar_export"):
            # Export artifacts
            st.session_state["show_export_modal"] = True
    
    # Help button
    if st.button("❓ Help", use_container_width=True, key="sidebar_help"):
        st.session_state["show_help_modal"] = True


def render_session_info():
    """Render current session information."""
    task_id = st.session_state.get("task_id", "")
    project_name = st.session_state.get("project_name", "")
    
    if task_id or project_name:
        st.markdown("### 📋 Session")
        
        if project_name:
            st.markdown(f"""
            <div style="font-size: 12px; color: #4a5568; margin-bottom: 4px;">
                <strong>Project:</strong> {project_name}
            </div>
            """, unsafe_allow_html=True)
        
        if task_id:
            st.markdown(f"""
            <div style="font-size: 10px; color: #a0aec0;">
                <strong>ID:</strong> {task_id[:20]}...
            </div>
            """, unsafe_allow_html=True)
