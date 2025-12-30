"""
Progress Tracker Component

Real-time visual progress tracker showing SDLC phase progression.
Features animated status indicators and clickable navigation.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
import src.dev_pilot.utils.constants as const
from src.dev_pilot.ui.streamlit_ui.components.state_manager import (
    STAGE_CONFIG,
    get_current_stage,
    get_stage_status,
    get_progress_percentage,
)


# Main SDLC phases for the tracker (excluding init and artifacts)
TRACKER_PHASES = [
    {
        "id": const.REQUIREMENT_COLLECTION,
        "name": "Requirements",
        "icon": "📋",
        "tab_index": 0,
    },
    {
        "id": const.GENERATE_USER_STORIES,
        "name": "User Stories",
        "icon": "📖",
        "tab_index": 1,
    },
    {
        "id": const.CREATE_DESIGN_DOC,
        "name": "Design",
        "icon": "🏗️",
        "tab_index": 2,
    },
    {
        "id": const.CODE_GENERATION,
        "name": "Code",
        "icon": "💻",
        "tab_index": 3,
    },
    {
        "id": const.SECURITY_REVIEW,
        "name": "Security",
        "icon": "🔒",
        "tab_index": 3,  # Same tab as code
    },
    {
        "id": const.WRITE_TEST_CASES,
        "name": "Testing",
        "icon": "🧪",
        "tab_index": 4,
    },
    {
        "id": const.QA_TESTING,
        "name": "QA",
        "icon": "✅",
        "tab_index": 5,
    },
    {
        "id": const.DEPLOYMENT,
        "name": "Deploy",
        "icon": "🚀",
        "tab_index": 6,
    },
]


class ProgressTracker:
    """
    Real-time progress tracker component.
    
    Displays SDLC phase progression with:
    - Visual step indicators
    - Animated current phase
    - Progress line
    - Clickable navigation
    """
    
    def __init__(self, phases: List[Dict] = None):
        """
        Initialize the progress tracker.
        
        Args:
            phases: List of phase configurations (default: TRACKER_PHASES)
        """
        self.phases = phases or TRACKER_PHASES
    
    def render(self):
        """Render the progress tracker component."""
        current_stage = get_current_stage()
        progress = get_progress_percentage()
        
        # Generate HTML for the tracker
        tracker_html = self._generate_tracker_html(current_stage, progress)
        
        # Render with Streamlit
        import streamlit.components.v1 as components
        wrapped_html = f'<div style="overflow:auto; max-width:100%;">{tracker_html}</div>'
        components.html(wrapped_html, height=400, scrolling=True)
        
        # Add CSS
        st.markdown(self._get_css(), unsafe_allow_html=True)
    
    def _generate_tracker_html(self, current_stage: str, progress: int) -> str:
        """Generate HTML for the progress tracker."""
        steps_html = []
        
        for i, phase in enumerate(self.phases):
            status = self._get_phase_status(phase["id"], current_stage)
            step_html = self._generate_step_html(phase, status, i)
            steps_html.append(step_html)
        
        return f"""
        <div class="progress-tracker-container">
            <div class="progress-tracker">
                <div class="progress-line">
                    <div class="progress-fill" style="width: {progress}%"></div>
                </div>
                <div class="steps-container">
                    {''.join(steps_html)}
                </div>
            </div>
            <div class="progress-percentage">
                <span class="percentage-value">{progress}%</span>
                <span class="percentage-label">Complete</span>
            </div>
        </div>
        """
    
    def _generate_step_html(self, phase: Dict, status: str, index: int) -> str:
        """Generate HTML for a single step."""
        status_class = f"step-{status}"
        icon = self._get_status_icon(status, phase["icon"])
        
        return f"""
        <div class="progress-step {status_class}" data-phase="{phase['id']}" data-index="{index}">
            <div class="step-icon-container">
                <div class="step-icon">{icon}</div>
                {self._get_pulse_indicator(status)}
            </div>
            <div class="step-label">{phase['name']}</div>
        </div>
        """
    
    def _get_phase_status(self, phase_id: str, current_stage: str) -> str:
        """Get status for a phase."""
        return get_stage_status(phase_id)
    
    def _get_status_icon(self, status: str, default_icon: str) -> str:
        """Get icon based on status."""
        if status == "completed":
            return "✓"
        elif status == "error":
            return "✗"
        else:
            return default_icon
    
    def _get_pulse_indicator(self, status: str) -> str:
        """Get pulse indicator HTML for current step."""
        if status == "current":
            return '<div class="pulse-ring"></div>'
        return ""
    
    def _get_css(self) -> str:
        """Get CSS for the progress tracker."""
        return """
        <style>
        .progress-tracker-container {
            display: flex;
            align-items: center;
            gap: 20px;
            padding: 20px;
            background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(247,250,252,0.95) 100%);
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            margin-bottom: 24px;
            border: 1px solid rgba(0, 98, 230, 0.1);
        }
        
        .progress-tracker {
            flex: 1;
            position: relative;
            padding: 10px 0;
        }
        
        .progress-line {
            position: absolute;
            top: 50%;
            left: 40px;
            right: 40px;
            height: 4px;
            background: #e2e8f0;
            border-radius: 2px;
            transform: translateY(-50%);
            z-index: 1;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #0062E6 0%, #33A9FF 100%);
            border-radius: 2px;
            transition: width 0.5s ease-out;
        }
        
        .steps-container {
            display: flex;
            justify-content: space-between;
            position: relative;
            z-index: 2;
        }
        
        .progress-step {
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        
        .progress-step:hover {
            transform: translateY(-2px);
        }
        
        .step-icon-container {
            position: relative;
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .step-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            background: #e2e8f0;
            color: #718096;
            border: 3px solid #e2e8f0;
        }
        
        .step-completed .step-icon {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            border-color: #48bb78;
        }
        
        .step-current .step-icon {
            background: linear-gradient(135deg, #0062E6 0%, #33A9FF 100%);
            color: white;
            border-color: #0062E6;
            box-shadow: 0 4px 15px rgba(0, 98, 230, 0.4);
        }
        
        .step-pending .step-icon {
            background: #f7fafc;
            color: #a0aec0;
            border-color: #e2e8f0;
        }
        
        .step-error .step-icon {
            background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);
            color: white;
            border-color: #e53e3e;
        }
        
        .pulse-ring {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 2px solid #0062E6;
            animation: pulse-ring 1.5s ease-out infinite;
        }
        
        @keyframes pulse-ring {
            0% {
                transform: translate(-50%, -50%) scale(1);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.4);
                opacity: 0;
            }
        }
        
        .step-label {
            margin-top: 8px;
            font-size: 12px;
            font-weight: 500;
            color: #4a5568;
            text-align: center;
            white-space: nowrap;
        }
        
        .step-current .step-label {
            color: #0062E6;
            font-weight: 600;
        }
        
        .step-completed .step-label {
            color: #48bb78;
        }
        
        .progress-percentage {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 10px 20px;
            background: linear-gradient(135deg, #0062E6 0%, #33A9FF 100%);
            border-radius: 12px;
            color: white;
            min-width: 80px;
        }
        
        .percentage-value {
            font-size: 24px;
            font-weight: 700;
            line-height: 1;
        }
        
        .percentage-label {
            font-size: 11px;
            opacity: 0.9;
            margin-top: 4px;
        }
        
        @media (max-width: 768px) {
            .step-label {
                display: none;
            }
            
            .step-icon {
                width: 32px;
                height: 32px;
                font-size: 14px;
            }
            
            .step-icon-container {
                width: 40px;
                height: 40px;
            }
        }
        </style>
        """



def render_progress_tracker(current_stage_idx=None):
    """
    Render the progress tracker component.
    Optionally accepts the current stage index for compatibility.
    """
    tracker = ProgressTracker()
    tracker.render()


def render_mini_progress() -> str:
    """
    Render a mini version of the progress tracker for sidebar.
    
    Returns:
        HTML string for mini progress indicator
    """
    current_stage = get_current_stage()
    progress = get_progress_percentage()
    
    # Get current phase info
    current_phase = None
    for phase in TRACKER_PHASES:
        if phase["id"] == current_stage:
            current_phase = phase
            break
    
    if not current_phase:
        current_phase = {"name": "Initializing", "icon": "🎯"}
    
    html = f"""
    <div style="background: linear-gradient(135deg, rgba(0,98,230,0.1) 0%, rgba(51,169,255,0.1) 100%); 
                border-radius: 10px; padding: 12px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 14px; font-weight: 600; color: #2d3748;">
                {current_phase['icon']} {current_phase['name']}
            </span>
            <span style="font-size: 12px; color: #0062E6; font-weight: 600;">{progress}%</span>
        </div>
        <div style="background: #e2e8f0; border-radius: 4px; height: 6px; overflow: hidden;">
            <div style="width: {progress}%; height: 100%; 
                        background: linear-gradient(90deg, #0062E6 0%, #33A9FF 100%);
                        border-radius: 4px; transition: width 0.5s ease;"></div>
        </div>
    </div>
    """
    
    return html
