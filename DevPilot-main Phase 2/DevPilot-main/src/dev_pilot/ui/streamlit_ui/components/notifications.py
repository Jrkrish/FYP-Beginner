"""
Notifications Component

Real-time toast notification system for stage transitions and events.
Provides non-blocking notifications with auto-dismiss functionality.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
from loguru import logger

from src.dev_pilot.ui.streamlit_ui.components.state_manager import (
    add_notification,
    get_unread_notifications,
    mark_notification_read,
    STAGE_CONFIG,
)


# Toast type configurations
TOAST_TYPES = {
    "success": {
        "icon": "✅",
        "color": "#48bb78",
        "bg_color": "#f0fff4",
        "border_color": "#9ae6b4",
    },
    "error": {
        "icon": "❌",
        "color": "#e53e3e",
        "bg_color": "#fff5f5",
        "border_color": "#feb2b2",
    },
    "warning": {
        "icon": "⚠️",
        "color": "#ed8936",
        "bg_color": "#fffaf0",
        "border_color": "#fbd38d",
    },
    "info": {
        "icon": "ℹ️",
        "color": "#3182ce",
        "bg_color": "#ebf8ff",
        "border_color": "#90cdf4",
    },
}

# Stage transition messages
STAGE_MESSAGES = {
    "approved": {
        "type": "success",
        "template": "✅ {stage} approved! Moving to next phase.",
    },
    "feedback": {
        "type": "warning",
        "template": "📝 Feedback submitted for {stage}. Revising...",
    },
    "completed": {
        "type": "success",
        "template": "🎉 {stage} completed successfully!",
    },
    "error": {
        "type": "error",
        "template": "❌ Error in {stage}. Please review.",
    },
    "started": {
        "type": "info",
        "template": "🚀 Starting {stage}...",
    },
}


class NotificationManager:
    """
    Toast notification manager.
    
    Provides:
    - Toast notifications
    - Notification center
    - Stage transition alerts
    - Custom notifications
    """
    
    def __init__(self):
        """Initialize the notification manager."""
        self._ensure_session_state()
    
    def _ensure_session_state(self):
        """Ensure notification session state exists."""
        if "toast_queue" not in st.session_state:
            st.session_state.toast_queue = []
        
        if "notifications" not in st.session_state:
            st.session_state.notifications = []
    
    def show_toast(
        self,
        message: str,
        type: str = "info",
        duration: int = 5,
        dismissible: bool = True,
    ):
        """
        Show a toast notification.
        
        Args:
            message: Notification message
            type: Notification type (success, error, warning, info)
            duration: Auto-dismiss duration in seconds
            dismissible: Whether user can dismiss
        """
        toast = {
            "id": f"toast_{uuid.uuid4().hex[:8]}",
            "message": message,
            "type": type,
            "duration": duration,
            "dismissible": dismissible,
            "timestamp": datetime.now().isoformat(),
        }
        
        st.session_state.toast_queue.append(toast)
        add_notification(message, type)
    
    def notify_stage_change(
        self,
        old_stage: str,
        new_stage: str,
        status: str,
    ):
        """
        Show notification for stage transition.
        
        Args:
            old_stage: Previous stage
            new_stage: New stage
            status: Transition status (approved, feedback, error)
        """
        stage_config = STAGE_CONFIG.get(old_stage, {})
        stage_name = stage_config.get("name", old_stage)
        
        msg_config = STAGE_MESSAGES.get(status, STAGE_MESSAGES["info"])
        message = msg_config["template"].format(stage=stage_name)
        
        self.show_toast(message, msg_config["type"])
    
    def render_notifications(self):
        """Render all pending toast notifications."""
        if not st.session_state.get("toast_queue"):
            return
        
        # Render CSS
        st.markdown(self._get_css(), unsafe_allow_html=True)
        
        # Render toasts
        toasts_html = '<div class="toast-container">'
        
        for toast in st.session_state.toast_queue[:5]:  # Show max 5 toasts
            toasts_html += self._generate_toast_html(toast)
        
        toasts_html += '</div>'
        
        # Add auto-dismiss script
        toasts_html += self._get_dismiss_script()
        
        st.markdown(toasts_html, unsafe_allow_html=True)
        
        # Clear processed toasts
        st.session_state.toast_queue = []
    
    def render_notification_center(self):
        """Render the notification center bell icon and dropdown."""
        unread = get_unread_notifications()
        unread_count = len(unread)
        
        # Bell icon with count
        bell_html = f"""
        <div class="notification-bell">
            <span class="bell-icon">🔔</span>
            {f'<span class="unread-badge">{unread_count}</span>' if unread_count > 0 else ''}
        </div>
        """
        
        st.markdown(bell_html, unsafe_allow_html=True)
        
        if unread_count > 0:
            with st.expander("📬 Notifications", expanded=False):
                for notification in unread[:10]:
                    self._render_notification_item(notification)
    
    def _render_notification_item(self, notification: Dict[str, Any]):
        """Render a single notification item."""
        notif_type = notification.get("type", "info")
        type_config = TOAST_TYPES.get(notif_type, TOAST_TYPES["info"])
        
        timestamp = notification.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M")
        except:
            time_str = ""
        
        st.markdown(f"""
        <div style="padding: 10px; background: {type_config['bg_color']}; 
                    border-left: 3px solid {type_config['color']};
                    border-radius: 6px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <span>{type_config['icon']}</span>
                    <span style="margin-left: 8px; color: #2d3748; font-size: 13px;">
                        {notification.get('message', '')}
                    </span>
                </div>
                <span style="font-size: 11px; color: #a0aec0;">{time_str}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def _generate_toast_html(self, toast: Dict[str, Any]) -> str:
        """Generate HTML for a toast notification."""
        toast_type = toast.get("type", "info")
        type_config = TOAST_TYPES.get(toast_type, TOAST_TYPES["info"])
        
        return f"""
        <div id="{toast['id']}" class="toast-notification toast-{toast_type}"
             style="background: {type_config['bg_color']}; 
                    border-color: {type_config['border_color']};">
            <div class="toast-icon" style="color: {type_config['color']};">
                {type_config['icon']}
            </div>
            <div class="toast-content">
                <div class="toast-message">{toast['message']}</div>
            </div>
            {f'<button class="toast-close" onclick="dismissToast(\\\'{toast["id"]}\\\')">×</button>' 
             if toast.get('dismissible', True) else ''}
        </div>
        """
    
    def _get_dismiss_script(self) -> str:
        """Get JavaScript for auto-dismiss functionality."""
        return """
        <script>
        function dismissToast(id) {
            var toast = document.getElementById(id);
            if (toast) {
                toast.classList.add('toast-hiding');
                setTimeout(function() {
                    toast.remove();
                }, 300);
            }
        }
        
        // Auto-dismiss toasts after 5 seconds
        document.querySelectorAll('.toast-notification').forEach(function(toast) {
            setTimeout(function() {
                dismissToast(toast.id);
            }, 5000);
        });
        </script>
        """
    
    def _get_css(self) -> str:
        """Get CSS for notifications."""
        return """
        <style>
        .toast-container {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        }
        
        .toast-notification {
            display: flex;
            align-items: center;
            padding: 14px 16px;
            border-radius: 10px;
            border: 1px solid;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            animation: slideInRight 0.3s ease-out;
            transition: all 0.3s ease;
        }
        
        .toast-notification.toast-hiding {
            opacity: 0;
            transform: translateX(100px);
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(100px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .toast-icon {
            font-size: 20px;
            margin-right: 12px;
            flex-shrink: 0;
        }
        
        .toast-content {
            flex: 1;
        }
        
        .toast-message {
            font-size: 14px;
            color: #2d3748;
            line-height: 1.4;
        }
        
        .toast-close {
            background: none;
            border: none;
            font-size: 20px;
            color: #a0aec0;
            cursor: pointer;
            padding: 0;
            margin-left: 12px;
            opacity: 0.6;
            transition: opacity 0.2s;
        }
        
        .toast-close:hover {
            opacity: 1;
        }
        
        .notification-bell {
            position: relative;
            display: inline-flex;
            align-items: center;
            cursor: pointer;
        }
        
        .bell-icon {
            font-size: 20px;
        }
        
        .unread-badge {
            position: absolute;
            top: -6px;
            right: -6px;
            background: #e53e3e;
            color: white;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 10px;
            min-width: 18px;
            text-align: center;
        }
        </style>
        """


# Global notification manager instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def show_toast(
    message: str,
    type: str = "info",
    duration: int = 5,
):
    """
    Show a toast notification.
    
    Args:
        message: Notification message
        type: Notification type (success, error, warning, info)
        duration: Auto-dismiss duration in seconds
    """
    # Use Streamlit's native toast for simplicity and reliability
    st.toast(message, icon=TOAST_TYPES.get(type, {}).get("icon", "ℹ️"))
    
    # Also log to notification history
    add_notification(message, type)


def notify_stage_change(
    old_stage: str,
    new_stage: str,
    status: str,
):
    """
    Show notification for stage transition.
    
    Args:
        old_stage: Previous stage
        new_stage: New stage
        status: Transition status (approved, feedback, error)
    """
    stage_config = STAGE_CONFIG.get(old_stage, {})
    stage_name = stage_config.get("name", old_stage)
    
    msg_config = STAGE_MESSAGES.get(status, STAGE_MESSAGES["info"])
    message = msg_config["template"].format(stage=stage_name)
    
    show_toast(message, msg_config["type"])


def render_notifications():
    """Render pending notifications."""
    manager = get_notification_manager()
    manager.render_notifications()


def render_notification_center():
    """Render the notification center."""
    manager = get_notification_manager()
    manager.render_notification_center()
