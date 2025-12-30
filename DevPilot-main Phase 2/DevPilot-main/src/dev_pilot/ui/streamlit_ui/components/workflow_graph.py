"""
Workflow Graph Component

Interactive workflow visualization with real-time state highlighting.
Uses Mermaid diagrams for dynamic workflow rendering.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
import src.dev_pilot.utils.constants as const
from src.dev_pilot.ui.streamlit_ui.components.state_manager import (
    STAGE_CONFIG,
    get_current_stage,
    get_stage_status,
)


# Node IDs for Mermaid diagram
STAGE_NODE_IDS = {
    const.PROJECT_INITILIZATION: "INIT",
    const.REQUIREMENT_COLLECTION: "REQ",
    const.GENERATE_USER_STORIES: "US",
    const.CREATE_DESIGN_DOC: "DD",
    const.CODE_GENERATION: "CG",
    const.SECURITY_REVIEW: "SR",
    const.WRITE_TEST_CASES: "TC",
    const.QA_TESTING: "QA",
    const.DEPLOYMENT: "DEP",
    const.ARTIFACTS: "ART",
}

# Node labels for Mermaid diagram
NODE_LABELS = {
    "INIT": "🎯 Initialize",
    "REQ": "📋 Requirements",
    "US": "📖 User Stories",
    "DD": "🏗️ Design",
    "CG": "💻 Code",
    "SR": "🔒 Security",
    "TC": "🧪 Tests",
    "QA": "✅ QA",
    "DEP": "🚀 Deploy",
    "ART": "📦 Artifacts",
}


class WorkflowGraph:
    """
    Interactive workflow graph component.
    
    Provides:
    - Mermaid-based workflow visualization
    - Real-time state highlighting
    - Clickable nodes for navigation
    - Animated current phase
    """
    
    def __init__(self):
        """Initialize the workflow graph."""
        pass
    
    def render(self, compact: bool = False):
        """
        Render the workflow graph.
        
        Args:
            compact: Whether to render in compact mode for sidebar
        """
        st.markdown(self._get_css(), unsafe_allow_html=True)
        
        current_stage = get_current_stage()
        statuses = self._get_all_statuses()
        
        if compact:
            self._render_compact_graph(current_stage, statuses)
        else:
            self._render_full_graph(current_stage, statuses)
    
    def _get_all_statuses(self) -> Dict[str, str]:
        """Get status for all stages."""
        current = get_current_stage()
        current_index = STAGE_CONFIG.get(current, {}).get("index", 0)
        
        statuses = {}
        for stage, config in STAGE_CONFIG.items():
            stage_index = config.get("index", 0)
            node_id = STAGE_NODE_IDS.get(stage)
            
            if node_id:
                if stage_index < current_index:
                    statuses[node_id] = "completed"
                elif stage_index == current_index:
                    statuses[node_id] = "current"
                else:
                    statuses[node_id] = "pending"
        
        return statuses
    
    def _render_full_graph(self, current_stage: str, statuses: Dict[str, str]):
        """Render full workflow graph."""
        st.subheader("🔄 Workflow Progress")
        
        # Generate Mermaid diagram
        mermaid_code = self._generate_mermaid(statuses)
        
        # Render using custom HTML (Mermaid CDN)
        self._render_mermaid(mermaid_code)
        
        # Render legend
        self._render_legend()
    
    def _render_compact_graph(self, current_stage: str, statuses: Dict[str, str]):
        """Render compact workflow graph for sidebar."""
        # Simple vertical flow
        stages = [
            ("REQ", "Requirements"),
            ("US", "User Stories"),
            ("DD", "Design"),
            ("CG", "Code"),
            ("SR", "Security"),
            ("TC", "Tests"),
            ("QA", "QA"),
            ("DEP", "Deploy"),
        ]
        
        graph_html = '<div class="compact-workflow">'
        
        for i, (node_id, label) in enumerate(stages):
            status = statuses.get(node_id, "pending")
            status_icon = {
                "completed": "✓",
                "current": "●",
                "pending": "○",
            }.get(status, "○")
            
            status_color = {
                "completed": "#48bb78",
                "current": "#0062E6",
                "pending": "#a0aec0",
            }.get(status, "#a0aec0")
            
            is_current = "current" if status == "current" else ""
            
            graph_html += f"""
            <div class="compact-step {is_current}">
                <div class="step-indicator" style="background: {status_color}; color: white;">
                    {status_icon}
                </div>
                <div class="step-name" style="color: {status_color};">
                    {label}
                </div>
            </div>
            """
            
            # Add connector except for last item
            if i < len(stages) - 1:
                connector_color = "#48bb78" if status == "completed" else "#e2e8f0"
                graph_html += f"""
                <div class="step-connector" style="background: {connector_color};"></div>
                """
        
        graph_html += '</div>'
        
        st.markdown(graph_html, unsafe_allow_html=True)
    
    def _generate_mermaid(self, statuses: Dict[str, str]) -> str:
        """Generate Mermaid diagram code."""
        mermaid = """
graph LR
    REQ[📋 Requirements] --> US[📖 User Stories]
    US --> DD[🏗️ Design]
    DD --> CG[💻 Code]
    CG --> SR[🔒 Security]
    SR --> TC[🧪 Tests]
    TC --> QA[✅ QA]
    QA --> DEP[🚀 Deploy]
"""
        
        # Add style definitions based on status
        for node_id, status in statuses.items():
            if status == "completed":
                mermaid += f"\n    style {node_id} fill:#48bb78,stroke:#38a169,color:#fff"
            elif status == "current":
                mermaid += f"\n    style {node_id} fill:#0062E6,stroke:#0052cc,color:#fff"
            else:
                mermaid += f"\n    style {node_id} fill:#e2e8f0,stroke:#cbd5e0,color:#4a5568"
        
        return mermaid
    
    def _render_mermaid(self, mermaid_code: str):
        """Render Mermaid diagram using HTML."""
        mermaid_html = f"""
        <div class="mermaid-container">
            <div class="mermaid">
{mermaid_code}
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{ 
                startOnLoad: true,
                theme: 'base',
                themeVariables: {{
                    primaryColor: '#0062E6',
                    primaryTextColor: '#fff',
                    primaryBorderColor: '#0052cc',
                    lineColor: '#a0aec0',
                    secondaryColor: '#f7fafc',
                    tertiaryColor: '#edf2f7'
                }}
            }});
        </script>
        """
        
        st.markdown(mermaid_html, unsafe_allow_html=True)
    
    def _render_legend(self):
        """Render status legend."""
        st.markdown("""
        <div class="workflow-legend">
            <div class="legend-item">
                <span class="legend-dot completed"></span>
                <span>Completed</span>
            </div>
            <div class="legend-item">
                <span class="legend-dot current"></span>
                <span>Current</span>
            </div>
            <div class="legend-item">
                <span class="legend-dot pending"></span>
                <span>Pending</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def _get_css(self) -> str:
        """Get CSS for workflow graph."""
        return """
        <style>
        .mermaid-container {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            margin-bottom: 16px;
            overflow-x: auto;
        }
        
        .mermaid {
            display: flex;
            justify-content: center;
        }
        
        .workflow-legend {
            display: flex;
            justify-content: center;
            gap: 24px;
            padding: 12px;
            background: #f7fafc;
            border-radius: 8px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #4a5568;
        }
        
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .legend-dot.completed {
            background: #48bb78;
        }
        
        .legend-dot.current {
            background: #0062E6;
            animation: pulse 2s infinite;
        }
        
        .legend-dot.pending {
            background: #e2e8f0;
        }
        
        /* Compact workflow styles */
        .compact-workflow {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            padding: 10px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .compact-step {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 0;
        }
        
        .compact-step.current {
            font-weight: 600;
        }
        
        .step-indicator {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
        }
        
        .compact-step.current .step-indicator {
            animation: pulse 2s infinite;
        }
        
        .step-name {
            font-size: 12px;
        }
        
        .step-connector {
            width: 2px;
            height: 16px;
            margin-left: 11px;
            border-radius: 1px;
        }
        
        @keyframes pulse {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(0, 98, 230, 0.4);
            }
            50% {
                box-shadow: 0 0 0 8px rgba(0, 98, 230, 0);
            }
        }
        </style>
        """


def render_workflow_graph(compact: bool = False):
    """
    Render the workflow graph component.
    
    Args:
        compact: Whether to render in compact mode
    """
    graph = WorkflowGraph()
    graph.render(compact)


def render_simple_workflow_indicator() -> str:
    """
    Get HTML for a simple inline workflow indicator.
    
    Returns:
        HTML string for inline workflow display
    """
    current_stage = get_current_stage()
    current_index = STAGE_CONFIG.get(current_stage, {}).get("index", 0)
    
    stages = ["REQ", "US", "DD", "CG", "SR", "TC", "QA", "DEP"]
    total = len(stages)
    
    indicators = []
    for i, stage in enumerate(stages):
        if i < current_index:
            indicators.append("●")  # Completed
        elif i == current_index:
            indicators.append("◉")  # Current
        else:
            indicators.append("○")  # Pending
    
    return " → ".join(indicators)
