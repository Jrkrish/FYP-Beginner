"""
Integrations Panel Component

Dynamic integration configuration panel with live connection testing,
event logging, and status indicators.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import os
from loguru import logger

from src.dev_pilot.ui.streamlit_ui.components.state_manager import (
    INTEGRATION_ICONS,
    add_activity_log,
)


# Integration configurations
INTEGRATION_CONFIGS = {
    "slack": {
        "name": "Slack",
        "description": "Send notifications and approval requests to Slack channels",
        "icon": "💬",
        "color": "#4A154B",
        "fields": [
            {"name": "bot_token", "label": "Bot Token", "type": "password", "placeholder": "xoxb-..."},
            {"name": "channel", "label": "Default Channel", "type": "text", "placeholder": "#devpilot"},
        ],
        "options": [
            {"name": "notify_stages", "label": "Send stage notifications", "default": True},
            {"name": "request_approvals", "label": "Request approvals via Slack", "default": False},
        ],
    },
    "jira": {
        "name": "Jira",
        "description": "Create epics and stories from generated artifacts",
        "icon": "📋",
        "color": "#0052CC",
        "fields": [
            {"name": "base_url", "label": "Jira URL", "type": "text", "placeholder": "https://your-domain.atlassian.net"},
            {"name": "email", "label": "Email", "type": "text", "placeholder": "your@email.com"},
            {"name": "api_token", "label": "API Token", "type": "password", "placeholder": ""},
            {"name": "project_key", "label": "Project Key", "type": "text", "placeholder": "PROJ"},
        ],
        "options": [
            {"name": "auto_create_epic", "label": "Auto-create epic for projects", "default": True},
            {"name": "create_stories", "label": "Create stories from user stories", "default": True},
        ],
    },
    "github": {
        "name": "GitHub",
        "description": "Commit code, create branches, and open pull requests",
        "icon": "🐙",
        "color": "#24292E",
        "fields": [
            {"name": "token", "label": "Personal Access Token", "type": "password", "placeholder": "ghp_..."},
            {"name": "owner", "label": "Repository Owner", "type": "text", "placeholder": "username"},
            {"name": "repository", "label": "Repository Name", "type": "text", "placeholder": "my-repo"},
            {"name": "default_branch", "label": "Default Branch", "type": "text", "placeholder": "main"},
        ],
        "options": [
            {"name": "auto_create_pr", "label": "Auto-create PR on code generation", "default": True},
            {"name": "auto_commit", "label": "Auto-commit changes", "default": False},
        ],
    },
    "webhook": {
        "name": "Webhooks",
        "description": "Send events to custom endpoints for other integrations",
        "icon": "🔔",
        "color": "#F59E0B",
        "fields": [
            {"name": "url", "label": "Webhook URL", "type": "text", "placeholder": "https://your-endpoint.com/webhook"},
            {"name": "secret", "label": "Secret (for HMAC)", "type": "password", "placeholder": "optional"},
        ],
        "options": [],
        "events": [
            "project_created",
            "user_stories_generated",
            "design_completed",
            "code_generated",
            "tests_generated",
            "stage_completed",
            "approval_required",
        ],
    },
}


class IntegrationsPanel:
    """
    Dynamic integrations configuration panel.
    
    Provides:
    - Integration cards with status
    - Configuration forms
    - Live connection testing
    - Event logging
    """
    
    def __init__(self):
        """Initialize the integrations panel."""
        self._ensure_session_state()
    
    def _ensure_session_state(self):
        """Ensure integrations session state exists."""
        if "integrations" not in st.session_state:
            st.session_state.integrations = {
                "slack": {"enabled": False, "config": {}, "status": "disconnected"},
                "jira": {"enabled": False, "config": {}, "status": "disconnected"},
                "github": {"enabled": False, "config": {}, "status": "disconnected"},
                "webhook": {"enabled": False, "config": {}, "status": "disconnected"},
            }
        
        if "integration_events" not in st.session_state:
            st.session_state.integration_events = []
    
    def render(self):
        """Render the integrations panel."""
        st.markdown(self._get_css(), unsafe_allow_html=True)
        
        # Status Overview
        self._render_status_overview()
        
        st.divider()
        
        # Integration Cards
        self._render_integration_cards()
        
        st.divider()
        
        # Help Section
        with st.expander("ℹ️ Integration Setup Help", expanded=False):
            self._render_help_section()
    
    def _render_status_overview(self):
        """Render integration status overview."""
        st.subheader("📊 Integration Status")
        
        cols = st.columns(4)
        
        for i, (int_type, config) in enumerate(INTEGRATION_CONFIGS.items()):
            with cols[i]:
                int_state = st.session_state.integrations.get(int_type, {})
                enabled = int_state.get("enabled", False)
                status = int_state.get("status", "disconnected")
                
                status_icon = {
                    "connected": "🟢",
                    "disconnected": "🔴",
                    "error": "🟡",
                    "testing": "🔵",
                }.get(status, "⚪")
                
                st.markdown(f"""
                <div class="integration-status-card" style="border-color: {config['color']}30;">
                    <div class="status-icon">{config['icon']}</div>
                    <div class="status-name">{config['name']}</div>
                    <div class="status-indicator">{status_icon} {status.title()}</div>
                </div>
                """, unsafe_allow_html=True)
    
    def _render_integration_cards(self):
        """Render integration configuration cards."""
        for int_type, config in INTEGRATION_CONFIGS.items():
            self._render_integration_card(int_type, config)
    
    def _render_integration_card(self, int_type: str, config: Dict[str, Any]):
        """Render a single integration card."""
        int_state = st.session_state.integrations.get(int_type, {})
        enabled = int_state.get("enabled", False)
        saved_config = int_state.get("config", {})
        status = int_state.get("status", "disconnected")
        
        with st.expander(
            f"{config['icon']} {config['name']} - {'🟢 Connected' if status == 'connected' else '🔴 Not Connected'}",
            expanded=False
        ):
            st.markdown(f"*{config['description']}*")
            
            # Enable toggle
            col1, col2 = st.columns([1, 4])
            with col1:
                new_enabled = st.toggle(
                    "Enable",
                    value=enabled,
                    key=f"toggle_{int_type}"
                )
            
            if new_enabled != enabled:
                st.session_state.integrations[int_type]["enabled"] = new_enabled
                if not new_enabled:
                    st.session_state.integrations[int_type]["status"] = "disconnected"
            
            if new_enabled:
                st.markdown("---")
                
                # Configuration form
                form_values = {}
                
                # Render fields
                for field in config.get("fields", []):
                    field_key = f"{int_type}_{field['name']}"
                    default_value = saved_config.get(field['name'], "")
                    
                    # Check for environment variable
                    env_key = f"{int_type.upper()}_{field['name'].upper()}"
                    env_value = os.getenv(env_key, "")
                    if env_value and not default_value:
                        default_value = env_value
                    
                    if field["type"] == "password":
                        form_values[field['name']] = st.text_input(
                            field["label"],
                            value=default_value,
                            type="password",
                            placeholder=field.get("placeholder", ""),
                            key=field_key
                        )
                    else:
                        form_values[field['name']] = st.text_input(
                            field["label"],
                            value=default_value,
                            placeholder=field.get("placeholder", ""),
                            key=field_key
                        )
                
                # Render options
                if config.get("options"):
                    st.markdown("**Options:**")
                    cols = st.columns(2)
                    for i, option in enumerate(config["options"]):
                        with cols[i % 2]:
                            option_key = f"{int_type}_{option['name']}"
                            default = saved_config.get(option['name'], option.get('default', False))
                            form_values[option['name']] = st.checkbox(
                                option["label"],
                                value=default,
                                key=option_key
                            )
                
                # Render events selector for webhooks
                if int_type == "webhook" and config.get("events"):
                    st.markdown("**Events to Send:**")
                    selected_events = st.multiselect(
                        "Select events",
                        options=config["events"],
                        default=saved_config.get("events", ["stage_completed"]),
                        key=f"{int_type}_events"
                    )
                    form_values["events"] = selected_events
                
                # Custom headers for webhooks
                if int_type == "webhook":
                    headers_str = st.text_area(
                        "Custom Headers (JSON)",
                        value=json.dumps(saved_config.get("headers", {}), indent=2),
                        height=100,
                        key=f"{int_type}_headers"
                    )
                    try:
                        form_values["headers"] = json.loads(headers_str) if headers_str else {}
                    except json.JSONDecodeError:
                        form_values["headers"] = {}
                        st.warning("Invalid JSON for headers")
                
                st.markdown("---")
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"💾 Save", key=f"save_{int_type}", use_container_width=True):
                        st.session_state.integrations[int_type]["config"] = form_values
                        st.success("✅ Configuration saved!")
                        add_activity_log(
                            f"Saved {config['name']} integration configuration",
                            type="success"
                        )
                
                with col2:
                    if st.button(f"🧪 Test Connection", key=f"test_{int_type}", use_container_width=True):
                        self._test_connection(int_type, form_values)
                
                with col3:
                    if st.button(f"📜 View Events", key=f"events_{int_type}", use_container_width=True):
                        self._show_events(int_type)
    
    def _test_connection(self, int_type: str, config: Dict[str, Any]):
        """Test integration connection."""
        st.session_state.integrations[int_type]["status"] = "testing"
        
        with st.spinner(f"Testing {INTEGRATION_CONFIGS[int_type]['name']} connection..."):
            try:
                # Import and test integration
                result = self._perform_connection_test(int_type, config)
                
                if result.get("success"):
                    st.session_state.integrations[int_type]["status"] = "connected"
                    st.success(f"✅ Connection successful! {result.get('message', '')}")
                    
                    # Log event
                    self._add_integration_event(int_type, "connection_test", True, result.get("message"))
                    add_activity_log(
                        f"Successfully connected to {INTEGRATION_CONFIGS[int_type]['name']}",
                        type="success"
                    )
                else:
                    st.session_state.integrations[int_type]["status"] = "error"
                    st.error(f"❌ Connection failed: {result.get('error', 'Unknown error')}")
                    
                    self._add_integration_event(int_type, "connection_test", False, result.get("error"))
                    
            except Exception as e:
                st.session_state.integrations[int_type]["status"] = "error"
                st.error(f"❌ Connection error: {str(e)}")
                self._add_integration_event(int_type, "connection_test", False, str(e))
    
    def _perform_connection_test(self, int_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform actual connection test."""
        try:
            from src.dev_pilot.integrations import create_integration, IntegrationConfig
            
            # Create integration config
            int_config = IntegrationConfig(
                integration_id=f"test_{int_type}",
                integration_type=int_type,
                name=f"Test {int_type}",
                enabled=True,
                credentials=config,
                settings=config,
            )
            
            # Create and test integration
            integration = create_integration(int_type, int_config)
            
            # Simple validation based on type
            if int_type == "slack":
                if not config.get("bot_token", "").startswith("xoxb-"):
                    return {"success": False, "error": "Invalid bot token format (should start with xoxb-)"}
            elif int_type == "jira":
                if not config.get("base_url") or not config.get("email") or not config.get("api_token"):
                    return {"success": False, "error": "Missing required fields"}
            elif int_type == "github":
                if not config.get("token") or not config.get("owner") or not config.get("repository"):
                    return {"success": False, "error": "Missing required fields"}
            elif int_type == "webhook":
                if not config.get("url"):
                    return {"success": False, "error": "Webhook URL is required"}
            
            return {"success": True, "message": "Configuration validated successfully"}
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _add_integration_event(self, int_type: str, event_type: str, success: bool, message: str = ""):
        """Add an integration event to the log."""
        event = {
            "integration": int_type,
            "event_type": event_type,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        
        if "integration_events" not in st.session_state:
            st.session_state.integration_events = []
        
        st.session_state.integration_events.insert(0, event)
        st.session_state.integration_events = st.session_state.integration_events[:100]
    
    def _show_events(self, int_type: str):
        """Show events for an integration."""
        events = [
            e for e in st.session_state.get("integration_events", [])
            if e.get("integration") == int_type
        ]
        
        if not events:
            st.info("No events recorded yet.")
            return
        
        st.markdown("**Recent Events:**")
        for event in events[:5]:
            status_icon = "✅" if event.get("success") else "❌"
            timestamp = event.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = timestamp
            
            st.markdown(f"""
            <div style="padding: 8px; background: #f7fafc; border-radius: 6px; margin: 4px 0;
                        font-size: 12px; display: flex; justify-content: space-between;">
                <span>{status_icon} {event.get('event_type', 'unknown')}</span>
                <span style="color: #718096;">{time_str}</span>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_help_section(self):
        """Render help section."""
        st.markdown("""
        ### Setting Up Integrations
        
        #### 💬 Slack
        1. Create a Slack App at [api.slack.com/apps](https://api.slack.com/apps)
        2. Add the `chat:write` and `chat:write.public` OAuth scopes
        3. Install the app to your workspace
        4. Copy the Bot Token (starts with `xoxb-`)
        
        #### 📋 Jira
        1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
        2. Create an API token
        3. Use your email and the token for authentication
        4. Find your project key in your Jira project settings
        
        #### 🐙 GitHub
        1. Go to Settings → Developer Settings → Personal Access Tokens
        2. Generate a new token with `repo` scope
        3. Enter the token along with your repository details
        
        #### 🔔 Webhooks
        - Webhooks send JSON payloads with event data to your endpoint
        - Use the secret for HMAC-SHA256 signature verification
        - Events include `X-DevPilot-Signature` and `X-DevPilot-Event` headers
        """)
    
    def _get_css(self) -> str:
        """Get CSS for the integrations panel."""
        return """
        <style>
        .integration-status-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 2px solid;
            transition: transform 0.2s ease;
        }
        
        .integration-status-card:hover {
            transform: translateY(-2px);
        }
        
        .status-icon {
            font-size: 32px;
            margin-bottom: 8px;
        }
        
        .status-name {
            font-weight: 600;
            font-size: 14px;
            color: #2d3748;
            margin-bottom: 4px;
        }
        
        .status-indicator {
            font-size: 12px;
            color: #718096;
        }
        </style>
        """


def render_integrations_panel():
    """Render the integrations panel."""
    panel = IntegrationsPanel()
    panel.render()


def get_integration_summary() -> Dict[str, Any]:
    """Get summary of integration status for sidebar display."""
    if "integrations" not in st.session_state:
        return {"total": 0, "connected": 0, "integrations": {}}
    
    integrations = st.session_state.integrations
    connected = sum(1 for i in integrations.values() if i.get("status") == "connected")
    
    return {
        "total": len(integrations),
        "connected": connected,
        "integrations": {
            name: {
                "enabled": state.get("enabled", False),
                "status": state.get("status", "disconnected"),
            }
            for name, state in integrations.items()
        },
    }
