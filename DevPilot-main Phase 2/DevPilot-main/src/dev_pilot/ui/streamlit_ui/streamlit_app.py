"""
DevPilot Enhanced Streamlit UI
==============================

This is the main entry point for the DevPilot Streamlit application.
It integrates the enhanced component library for a modern, responsive UI experience.
"""

# =============================================================================
# CRITICAL: Path setup MUST come before any other imports
# This ensures 'src' module is importable regardless of where script is run from
# =============================================================================
import sys
from pathlib import Path

# Get the project root (4 levels up from this file)
# File location: src/dev_pilot/ui/streamlit_ui/streamlit_app.py
# Project root: DevPilot-main/
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# CRITICAL: Streamlit import and set_page_config MUST be first Streamlit calls
# =============================================================================
import streamlit as st

# Set page config IMMEDIATELY - this MUST be the first Streamlit command
st.set_page_config(
    page_title="DevPilot - AI-Powered SDLC",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/DevPilot/help',
        'Report a bug': 'https://github.com/DevPilot/issues',
        'About': '# DevPilot\nAI-Powered SDLC Automation Platform'
    }
)

# =============================================================================
# Now safe to import everything else
# =============================================================================
import os
import io
import contextlib
import json

from src.dev_pilot.LLMS.groqllm import GroqLLM
from src.dev_pilot.LLMS.geminillm import GeminiLLM
from src.dev_pilot.LLMS.openai_llm import OpenAILLM
from src.dev_pilot.graph.graph_builder import GraphBuilder
from src.dev_pilot.ui.uiconfigfile import Config
import src.dev_pilot.utils.constants as const
from src.dev_pilot.graph.graph_executor import GraphExecutor
from src.dev_pilot.graph.agentic_executor import AgenticGraphExecutor
from src.dev_pilot.state.sdlc_state import UserStoryList

# Import enhanced UI components
from src.dev_pilot.ui.streamlit_ui.components import (
    StateManager,
    render_progress_tracker,
    render_agent_dashboard,
    render_integrations_panel,
    render_artifact_viewer,
    render_workflow_graph,
    render_enhanced_sidebar,
    NotificationManager,
    show_toast,
)


def load_custom_css():
    """Load custom CSS styles for enhanced UI."""
    css_dir = Path(__file__).parent
    
    # Load advanced styles
    advanced_css_path = css_dir / "advanced_style.css"
    if advanced_css_path.exists():
        with open(advanced_css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Load custom styles
    custom_css_path = css_dir / "custom.css"
    if custom_css_path.exists():
        with open(custom_css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def initialize_session():
    """Initialize session state with default values."""
    st.session_state.stage = const.PROJECT_INITILIZATION
    st.session_state.project_name = ""
    st.session_state.requirements = ""
    st.session_state.task_id = ""
    st.session_state.state = {}
    st.session_state.use_agents = True  # Default to agent mode
    
    # Initialize state manager
    if "state_manager" not in st.session_state:
        st.session_state.state_manager = StateManager()
    
    # Initialize notification manager
    if "notification_manager" not in st.session_state:
        st.session_state.notification_manager = NotificationManager()


def get_current_stage_index():
    """Get the current stage index for progress tracking."""
    stage_order = [
        const.PROJECT_INITILIZATION,
        const.REQUIREMENT_COLLECTION,
        const.GENERATE_USER_STORIES,
        const.CREATE_DESIGN_DOC,
        const.CODE_GENERATION,
        const.SECURITY_REVIEW,
        const.WRITE_TEST_CASES,
        const.QA_TESTING,
        const.DEPLOYMENT,
        const.ARTIFACTS,
    ]
    current = st.session_state.get("stage", const.PROJECT_INITILIZATION)
    try:
        return stage_order.index(current)
    except ValueError:
        return 0


def load_sidebar_ui(config):
    """Load the sidebar UI with enhanced components."""
    user_controls = {}
    
    with st.sidebar:
        # Enhanced header
        st.markdown("""
        <div class="sidebar-header">
            <div class="sidebar-logo">🚀</div>
            <div class="sidebar-title">DevPilot</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Execution Mode Toggle
        st.subheader("⚙️ Execution Mode")
        use_agents = st.toggle(
            "🤖 Use AI Agents",
            value=st.session_state.get("use_agents", True),
            help="Enable multi-agent system for enhanced SDLC automation",
            key="sidebar_use_agents_toggle"
        )
        st.session_state.use_agents = use_agents
        user_controls["use_agents"] = use_agents
        
        if use_agents:
            st.success("🤖 Agent Mode: Specialized AI agents handle each phase")
        else:
            st.info("📊 Legacy Mode: Traditional graph-based workflow")
        
        st.divider()
        
        # Get options from config
        llm_options = config.get_llm_options()

        # LLM selection
        user_controls["selected_llm"] = st.selectbox("Select LLM", llm_options)

        if user_controls["selected_llm"] == 'Groq':
            # Model selection
            model_options = config.get_groq_model_options()
            user_controls["selected_groq_model"] = st.selectbox("Select Model", model_options)
            # API key input
            os.environ["GROQ_API_KEY"] = user_controls["GROQ_API_KEY"] = st.session_state["GROQ_API_KEY"] = st.text_input(
                "API Key",
                type="password",
                value=os.getenv("GROQ_API_KEY", "")
            )
            # Validate API key
            if not user_controls["GROQ_API_KEY"]:
                st.warning("⚠️ Please enter your GROQ API key to proceed. Don't have? refer : [https://console.groq.com/keys](https://console.groq.com/keys)")
                
        if user_controls["selected_llm"] == 'Gemini':
            # Model selection
            model_options = config.get_gemini_model_options()
            user_controls["selected_gemini_model"] = st.selectbox("Select Model", model_options)
            # API key input
            os.environ["GEMINI_API_KEY"] = user_controls["GEMINI_API_KEY"] = st.session_state["GEMINI_API_KEY"] = st.text_input(
                "API Key",
                type="password",
                value=os.getenv("GEMINI_API_KEY", "")
            )
            # Validate API key
            if not user_controls["GEMINI_API_KEY"]:
                st.warning("⚠️ Please enter your GEMINI API key to proceed. Don't have? refer : [https://ai.google.dev/gemini-api/docs/api-key](https://ai.google.dev/gemini-api/docs/api-key)")
                
                
        if user_controls["selected_llm"] == 'OpenAI':
            # Model selection
            model_options = config.get_openai_model_options()
            user_controls["selected_openai_model"] = st.selectbox("Select Model", model_options)
            # API key input
            os.environ["OPENAI_API_KEY"] = user_controls["OPENAI_API_KEY"] = st.session_state["OPENAI_API_KEY"] = st.text_input(
                "API Key",
                type="password",
                value=os.getenv("OPENAI_API_KEY", "")
            )
            # Validate API key
            if not user_controls["OPENAI_API_KEY"]:
                st.warning("⚠️ Please enter your OPENAI API key to proceed. Don't have? refer : [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)")
        
        st.divider()
        
        # Mini Agent Status (when in agent mode)
        if use_agents and st.session_state.get("task_id"):
            st.subheader("🤖 Agent Status")
            render_enhanced_sidebar(config)
        
        st.divider()
        
        # Reset button
        if st.button("🔄 Reset Session", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            initialize_session()
            st.rerun()
        
        # Workflow Overview
        st.subheader("Workflow Overview")
        if os.path.exists("workflow_graph.png"):
            st.image("workflow_graph.png")
        else:
            st.info("Workflow graph will be displayed here")
            
    return user_controls


def load_streamlit_ui(config):
    """Load the main Streamlit UI with enhanced styling.
    
    Note: st.set_page_config() is called at module level (top of file)
    to ensure it's the first Streamlit command executed.
    """
    # Load custom CSS
    load_custom_css()
    
    # Enhanced header
    st.markdown("""
    <div class="main-header">
        <div class="main-header-logo">🚀</div>
        <div>
            <h1 class="main-header-title" style="margin: 0; font-size: 2rem;">DevPilot</h1>
            <p class="main-header-subtitle" style="margin: 0; opacity: 0.7;">AI-Powered SDLC Automation Platform</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    user_controls = load_sidebar_ui(config)
    return user_controls


def render_user_stories_display(user_story_list):
    """Render user stories with enhanced styling."""
    if isinstance(user_story_list, UserStoryList):
        for story in user_story_list.user_stories:
            unique_id = f"US-{story.id:03}"

            # Handle priority - convert to readable format
            priority_value = story.priority
            if isinstance(priority_value, int):
                if priority_value <= 2:
                    priority_text = "High"
                    priority_class = "success"
                elif priority_value == 3:
                    priority_text = "Medium"
                    priority_class = "warning"
                else:
                    priority_text = "Low"
                    priority_class = "neutral"
            else:
                # Handle string priorities
                priority_str = str(priority_value).lower()
                if 'high' in priority_str:
                    priority_text = "High"
                    priority_class = "success"
                elif 'medium' in priority_str:
                    priority_text = "Medium"
                    priority_class = "warning"
                else:
                    priority_text = "Low"
                    priority_class = "neutral"

            with st.container():
                st.markdown(f"""
                <div class="custom-card fade-in">
                    <div class="custom-card-header">
                        <h4 class="custom-card-title">{story.title}</h4>
                        <span class="status-badge status-badge--info">{unique_id}</span>
                    </div>
                    <div class="custom-card-body">
                        <p><strong>Priority:</strong> <span class="status-badge status-badge--{priority_class}">{priority_text}</span></p>
                        <p><strong>Description:</strong> {story.description}</p>
                        <p><strong>Acceptance Criteria:</strong></p>
                        <div style="padding-left: 1rem;">{story.acceptance_criteria}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.divider()


def render_review_buttons(tab_key: str, approve_callback, feedback_callback, feedback_placeholder: str = "Provide feedback (optional):"):
    """Render standardized review buttons with feedback input."""
    feedback_text = st.text_area(feedback_placeholder, key=f"feedback_{tab_key}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"✅ Approve", key=f"approve_{tab_key}", use_container_width=True):
            approve_callback()
    
    with col2:
        if st.button(f"✍️ Give Feedback", key=f"feedback_btn_{tab_key}", use_container_width=True):
            if feedback_text.strip():
                feedback_callback(feedback_text.strip())
            else:
                st.warning("⚠️ Please enter feedback before submitting.")
    
    return feedback_text


## Main Entry Point
def load_app():
    """
    Main entry point for the Streamlit app using tab-based UI with enhanced components.
    """
    st.write("Loading config...")
    config = Config()
    st.write("Config loaded, initializing session...")

    if 'stage' not in st.session_state:
        initialize_session()
    st.write("Session initialized, loading UI...")

    user_input = load_streamlit_ui(config)
    st.write("UI loaded, checking user input...")
    if not user_input:
        st.error("Error: Failed to load user input from the UI.")
        return

    try:
        # Configure LLM
        selectedLLM = user_input.get("selected_llm")
        model = None
        if selectedLLM == "Gemini":
            obj_llm_config = GeminiLLM(user_controls_input=user_input)
            model = obj_llm_config.get_llm_model()
        elif selectedLLM == "Groq":
            obj_llm_config = GroqLLM(user_controls_input=user_input)
            model = obj_llm_config.get_llm_model()
        elif selectedLLM == "OpenAI":
            obj_llm_config = OpenAILLM(user_controls_input=user_input)
            model = obj_llm_config.get_llm_model()
        if not model:
            st.error("Error: LLM model could not be initialized.")
            return

        # Determine execution mode
        use_agents = user_input.get("use_agents", True)
        
        ## Graph Builder (for fallback)
        graph_builder = GraphBuilder(model)
        try:
            graph = graph_builder.setup_graph()
            legacy_executor = GraphExecutor(graph)
        except Exception as e:
            st.error(f"Error: Graph setup failed - {e}")
            legacy_executor = None
        
        # Create the executor based on mode
        if use_agents:
            try:
                graph_executor = AgenticGraphExecutor(
                    llm=model,
                    use_agents=True,
                    fallback_graph=graph if legacy_executor else None,
                )
                st.sidebar.success("🤖 Using Multi-Agent System")
            except Exception as e:
                st.sidebar.warning(f"⚠️ Agent mode failed, using legacy: {e}")
                graph_executor = legacy_executor
        else:
            graph_executor = legacy_executor
            st.sidebar.info("📊 Using Legacy Graph Mode")

        # ============== Progress Tracker ==============
        st.markdown("### 📈 Workflow Progress")
        current_stage_idx = get_current_stage_index()
        render_progress_tracker(current_stage_idx)
        
        st.divider()

        # Create tabs for different stages (added Agent Dashboard, Integrations, and Workflow Graph tabs)
        tabs = st.tabs([
            "📋 Project Requirement",
            "📝 User Stories",
            "🏗️ Design Documents",
            "💻 Code Generation",
            "🧪 Test Cases",
            "✅ QA Testing",
            "🚀 Deployment",
            "📦 Artifacts",
            "🤖 Agent Dashboard",
            "🔗 Integrations",
            "📊 Workflow Graph",
            "⚡ Live Sandbox"
        ])

        # ---------------- Tab 1: Project Requirement ----------------
        with tabs[0]:
            st.header("📋 Project Requirement")
            
            project_name = st.text_input(
                "Enter the project name:",
                value=st.session_state.get("project_name", ""),
                placeholder="e.g., E-Commerce Platform"
            )
            st.session_state.project_name = project_name

            if st.session_state.stage == const.PROJECT_INITILIZATION:
                if st.button("🚀 Let's Start", use_container_width=True, type="primary"):
                    if not project_name.strip():
                        st.error("Please enter a valid project name (cannot be empty or just spaces).")
                        show_toast("Error", "Please enter a valid project name", "error")
                    else:
                        try:
                            with st.spinner("Initializing project..."):
                                graph_response = graph_executor.start_workflow(project_name.strip())
                                st.session_state.task_id = graph_response["task_id"]
                                st.session_state.state = graph_response["state"]
                                st.session_state.stage = const.REQUIREMENT_COLLECTION
                                show_toast("Success", f"Project '{project_name}' initialized!", "success")
                            st.rerun()
                        except Exception as workflow_error:
                            st.error(f"Workflow start failed: {str(workflow_error)}")
                            show_toast("Error", "Failed to start workflow", "error")

            # If stage has progressed beyond initialization, show requirements input
            if st.session_state.stage in [const.REQUIREMENT_COLLECTION, const.GENERATE_USER_STORIES]:
                st.markdown("---")
                st.subheader("📝 Project Requirements")
                
                requirements_input = st.text_area(
                    "Enter the requirements. Write each requirement on a new line:",
                    value="\n".join(st.session_state.get("requirements", [])),
                    height=200,
                    placeholder="1. User authentication with OAuth2\n2. Product catalog with search\n3. Shopping cart functionality\n..."
                )
                
                if st.button("Submit Requirements", use_container_width=True, type="primary"):
                    requirements = [req.strip() for req in requirements_input.split("\n") if req.strip()]
                    st.session_state.requirements = requirements
                    if not requirements:
                        st.error("Please enter at least one requirement.")
                    else:
                        st.success("Project details saved successfully!")
                        
                        # Display project summary
                        with st.expander("📄 Project Summary", expanded=True):
                            st.write(f"**Project Name:** {st.session_state.get('project_name', 'Unnamed Project')}")
                            st.write("**Requirements:**")
                            for i, req in enumerate(requirements, 1):
                                st.write(f"{i}. {req}")
                        
                        try:
                            with st.spinner("Generating user stories..."):
                                graph_response = graph_executor.generate_stories(st.session_state.task_id, requirements)
                                st.session_state.state = graph_response["state"]
                                st.session_state.stage = const.GENERATE_USER_STORIES
                                show_toast("Success", "User stories generated!", "success")
                            st.rerun()
                        except Exception as stories_error:
                            st.error(f"Story generation failed: {str(stories_error)}")
                            with st.expander("🔍 Error Details"):
                                import traceback
                                st.code(traceback.format_exc())

        # ---------------- Tab 2: User Stories ----------------
        with tabs[1]:
            st.header("📝 User Stories")

            # Debug: Show current state
            with st.expander("🔍 Debug Info", expanded=False):
                st.write("Current Stage:", st.session_state.stage)
                st.write("State keys:", list(st.session_state.state.keys()) if st.session_state.state else "No state")
                if "user_stories" in st.session_state.state:
                    st.write("User Stories Type:", type(st.session_state.state["user_stories"]))
                    st.write("User Stories Content:", st.session_state.state["user_stories"])

            if "user_stories" in st.session_state.state:
                user_story_list = st.session_state.state["user_stories"]
                st.divider()
                st.subheader("Generated User Stories")
                render_user_stories_display(user_story_list)

            # User Story Review Stage
            if st.session_state.stage == const.GENERATE_USER_STORIES:
                st.subheader("Review User Stories")
                feedback_text = st.text_area("Provide feedback for improving the user stories (optional):", key="us_feedback")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve User Stories", use_container_width=True):
                        try:
                            with st.spinner("Approving user stories..."):
                                graph_response = graph_executor.graph_review_flow(
                                    st.session_state.task_id, status="approved", feedback=None, review_type=const.REVIEW_USER_STORIES
                                )
                                st.session_state.state = graph_response["state"]
                                st.session_state.stage = const.CREATE_DESIGN_DOC
                                show_toast("Success", "User stories approved!", "success")
                            st.rerun()
                        except Exception as approve_error:
                            st.error(f"Approval failed: {str(approve_error)}")
                            import traceback
                            st.code(traceback.format_exc())
                        
                with col2:
                    if st.button("✍️ Give User Stories Feedback", use_container_width=True):
                        if not feedback_text.strip():
                            st.warning("⚠️ Please enter feedback before submitting.")
                        else:
                            try:
                                st.info("🔄 Sending feedback to revise user stories.")
                                graph_response = graph_executor.graph_review_flow(
                                    st.session_state.task_id, status="feedback", feedback=feedback_text.strip(), review_type=const.REVIEW_USER_STORIES
                                )
                                st.session_state.state = graph_response["state"]
                                st.session_state.stage = const.GENERATE_USER_STORIES
                                st.rerun()
                            except Exception as feedback_error:
                                st.error(f"Feedback submission failed: {str(feedback_error)}")
            else:
                st.info("User stories generation pending or not reached yet.")

        # ---------------- Tab 3: Design Documents ----------------
        with tabs[2]:
            st.header("🏗️ Design Documents")
            if st.session_state.stage == const.CREATE_DESIGN_DOC:
                
                try:
                    graph_response = graph_executor.get_updated_state(st.session_state.task_id)
                    st.session_state.state = graph_response["state"]
                except Exception as state_error:
                    st.error(f"State update failed: {str(state_error)}")
                
                if "design_documents" in st.session_state.state:
                    design_doc = st.session_state.state["design_documents"]

                    if design_doc is not None:
                        design_tabs = st.tabs(["📋 Functional Design", "⚙️ Technical Design"])

                        with design_tabs[0]:
                            st.subheader("Functional Design Document")
                            st.markdown(design_doc.get("functional", "No functional design document available."))

                        with design_tabs[1]:
                            st.subheader("Technical Design Document")
                            st.markdown(design_doc.get("technical", "No technical design document available."))
                    else:
                        st.info("Design documents are being generated. Please approve the user stories first.")
                
                # Design Document Review Stage
                st.divider()
                st.subheader("Review Design Documents")
                feedback_text = st.text_area("Provide feedback for improving the design documents (optional):", key="dd_feedback")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve Design Documents", use_container_width=True):
                        try:
                            st.success("✅ Design documents approved.")
                            graph_response = graph_executor.graph_review_flow(
                                st.session_state.task_id, status="approved", feedback=None, review_type=const.REVIEW_DESIGN_DOCUMENTS
                            )
                            st.session_state.state = graph_response["state"]
                            st.session_state.stage = const.CODE_GENERATION
                            show_toast("Success", "Design documents approved!", "success")
                            st.rerun()
                        except Exception as approve_error:
                            st.error(f"Approval failed: {str(approve_error)}")
                        
                with col2:
                    if st.button("✍️ Give Design Documents Feedback", use_container_width=True):
                        if not feedback_text.strip():
                            st.warning("⚠️ Please enter feedback before submitting.")
                        else:
                            try:
                                st.info("🔄 Sending feedback to revise design documents.")
                                graph_response = graph_executor.graph_review_flow(
                                    st.session_state.task_id, status="feedback", feedback=feedback_text.strip(), review_type=const.REVIEW_DESIGN_DOCUMENTS
                                )
                                st.session_state.state = graph_response["state"]
                                st.session_state.stage = const.CREATE_DESIGN_DOC
                                st.rerun()
                            except Exception as feedback_error:
                                st.error(f"Feedback submission failed: {str(feedback_error)}")
                    
            else:
                st.info("Design document generation pending or not reached yet.")

        # ---------------- Tab 4: Coding ----------------
        with tabs[3]:
            st.header("💻 Code Generation")
            if st.session_state.stage in [const.CODE_GENERATION, const.SECURITY_REVIEW]:
                
                try:
                    graph_response = graph_executor.get_updated_state(st.session_state.task_id)
                    st.session_state.state = graph_response["state"]
                except Exception as state_error:
                    st.error(f"State update failed: {str(state_error)}")
                        
                if "code_generated" in st.session_state.state:
                    code_generated = st.session_state.state["code_generated"]
                    st.subheader("📁 Code Files")
                    
                    # Use enhanced code display
                    st.markdown(f"""
                    <div class="code-block">
                        <div class="code-block-header">
                            <span class="code-block-language">Generated Code</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.code(code_generated if isinstance(code_generated, str) else str(code_generated))
                    st.divider()
                    
                if st.session_state.stage == const.CODE_GENERATION:
                    review_type = const.REVIEW_CODE
                elif st.session_state.stage == const.SECURITY_REVIEW:
                    if "security_recommendations" in st.session_state.state:
                        security_recommendations = st.session_state.state["security_recommendations"]
                        st.subheader("🔒 Security Recommendations")
                        st.warning("Please review the security recommendations below:")
                        st.markdown(security_recommendations)
                        review_type = const.REVIEW_SECURITY_RECOMMENDATIONS
                
                # Code Review Stage
                st.divider()
                st.subheader("Review Details")
                
                if st.session_state.stage == const.CODE_GENERATION:
                    feedback_text = st.text_area("Provide feedback (optional):", key="code_feedback")
                    
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve Code", use_container_width=True):
                        try:
                            graph_response = graph_executor.graph_review_flow(
                                st.session_state.task_id, status="approved", feedback=None, review_type=review_type
                            )
                            st.session_state.state = graph_response["state"]
                            if st.session_state.stage == const.CODE_GENERATION:
                                st.session_state.stage = const.SECURITY_REVIEW
                                show_toast("Success", "Code approved! Moving to security review.", "success")
                                st.rerun()
                            elif st.session_state.stage == const.SECURITY_REVIEW:
                                st.session_state.stage = const.WRITE_TEST_CASES
                                show_toast("Success", "Security review passed!", "success")
                            st.rerun()
                        except Exception as approve_error:
                            st.error(f"Approval failed: {str(approve_error)}")
                            
                with col2:
                    if st.session_state.stage == const.SECURITY_REVIEW:
                        if st.button("✍️ Implement Security Recommendations", use_container_width=True):
                            try:
                                st.info("🔄 Sending feedback to revise code generation.")
                                graph_response = graph_executor.graph_review_flow(
                                    st.session_state.task_id, status="feedback", feedback=None, review_type=review_type
                                )
                                st.session_state.state = graph_response["state"]
                                st.session_state.stage = const.CODE_GENERATION
                                st.rerun()
                            except Exception as impl_error:
                                st.error(f"Implementation failed: {str(impl_error)}")
                    else:
                        if st.button("✍️ Give Feedback", use_container_width=True):
                            if not feedback_text.strip():
                                st.warning("⚠️ Please enter feedback before submitting.")
                            else:
                                try:
                                    st.info("🔄 Sending feedback to revise code generation.")
                                    graph_response = graph_executor.graph_review_flow(
                                        st.session_state.task_id, status="feedback", feedback=feedback_text.strip(), review_type=review_type
                                    )
                                    st.session_state.state = graph_response["state"]
                                    st.session_state.stage = const.CODE_GENERATION
                                    st.rerun()
                                except Exception as feedback_error:
                                    st.error(f"Feedback submission failed: {str(feedback_error)}")
                    
            else:
                st.info("Code generation pending or not reached yet.")
                
        # ---------------- Tab 5: Test Cases ----------------
        with tabs[4]:
            st.header("🧪 Test Cases")
            if st.session_state.stage == const.WRITE_TEST_CASES:
                
                try:
                    graph_response = graph_executor.get_updated_state(st.session_state.task_id)
                    st.session_state.state = graph_response["state"]
                except Exception as state_error:
                    st.error(f"State update failed: {str(state_error)}")
                
                if "test_cases" in st.session_state.state:
                    test_cases = st.session_state.state["test_cases"]
                    st.markdown(test_cases)
                
                # Test Cases Review Stage
                st.divider()
                st.subheader("Review Test Cases")
                feedback_text = st.text_area("Provide feedback for improving the test cases (optional):", key="tc_feedback")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve Test Cases", use_container_width=True):
                        try:
                            st.success("✅ Test cases approved.")
                            graph_response = graph_executor.graph_review_flow(
                                st.session_state.task_id, status="approved", feedback=None, review_type=const.REVIEW_TEST_CASES
                            )
                            st.session_state.state = graph_response["state"]
                            st.session_state.stage = const.QA_TESTING
                            show_toast("Success", "Test cases approved!", "success")
                            st.rerun()
                        except Exception as approve_error:
                            st.error(f"Approval failed: {str(approve_error)}")
                        
                with col2:
                    if st.button("✍️ Give Test Cases Feedback", use_container_width=True):
                        if not feedback_text.strip():
                            st.warning("⚠️ Please enter feedback before submitting.")
                        else:
                            try:
                                st.info("🔄 Sending feedback to revise test cases.")
                                graph_response = graph_executor.graph_review_flow(
                                    st.session_state.task_id, status="feedback", feedback=feedback_text.strip(), review_type=const.REVIEW_TEST_CASES
                                )
                                st.session_state.state = graph_response["state"]
                                st.session_state.stage = const.WRITE_TEST_CASES
                                st.rerun()
                            except Exception as feedback_error:
                                st.error(f"Feedback submission failed: {str(feedback_error)}")
                    
            else:
                st.info("Test Cases generation pending or not reached yet.")
                
        # ---------------- Tab 6: QA Testing ----------------
        with tabs[5]:
            st.header("✅ QA Testing")
            if st.session_state.stage == const.QA_TESTING:
                
                try:
                    graph_response = graph_executor.get_updated_state(st.session_state.task_id)
                    st.session_state.state = graph_response["state"]
                except Exception as state_error:
                    st.error(f"State update failed: {str(state_error)}")
                
                if "qa_testing_comments" in st.session_state.state:
                    qa_testing = st.session_state.state["qa_testing_comments"]
                    st.markdown(qa_testing)
                
                # QA Testing Review Stage
                st.divider()
                st.subheader("Review QA Testing Comments")
                feedback_text = st.text_area("Provide feedback for improving the QA testing comments (optional):", key="qa_feedback")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve Testing", use_container_width=True):
                        try:
                            st.success("✅ QA Testing approved.")
                            graph_response = graph_executor.graph_review_flow(
                                st.session_state.task_id, status="approved", feedback=None, review_type=const.REVIEW_QA_TESTING
                            )
                            st.session_state.state = graph_response["state"]
                            st.session_state.stage = const.DEPLOYMENT
                            show_toast("Success", "QA testing approved!", "success")
                            st.rerun()
                        except Exception as approve_error:
                            st.error(f"Approval failed: {str(approve_error)}")
                        
                with col2:
                    if st.button("✍️ Fix testing issues", use_container_width=True):
                        try:
                            st.info("🔄 Sending feedback to revise code.")
                            graph_response = graph_executor.graph_review_flow(
                                st.session_state.task_id, status="feedback", feedback=feedback_text.strip(), review_type=const.REVIEW_QA_TESTING
                            )
                            st.session_state.state = graph_response["state"]
                            st.session_state.stage = const.CODE_GENERATION
                            st.rerun()
                        except Exception as fix_error:
                            st.error(f"Fix failed: {str(fix_error)}")
                    
            else:
                st.info("QA Testing Report generation pending or not reached yet.")
                
        # ---------------- Tab 7: Deployment ----------------
        with tabs[6]:
            st.header("🚀 Deployment")
            if st.session_state.stage == const.DEPLOYMENT:
                
                try:
                    graph_response = graph_executor.get_updated_state(st.session_state.task_id)
                    st.session_state.state = graph_response["state"]
                except Exception as state_error:
                    st.error(f"State update failed: {str(state_error)}")
                
                if "deployment_feedback" in st.session_state.state:
                    deployment_feedback = st.session_state.state["deployment_feedback"]
                    
                    st.success("🎉 Deployment configuration generated!")
                    st.markdown(deployment_feedback)
                    
                    if st.button("📦 Proceed to Artifacts", use_container_width=True, type="primary"):
                        st.session_state.stage = const.ARTIFACTS
                        show_toast("Success", "Workflow complete! View your artifacts.", "success")
                        st.rerun()
                                
            else:
                st.info("Deployment verification pending or not reached yet.")
                
        # ---------------- Tab 8: Artifacts ----------------
        with tabs[7]:
            st.header("📦 Artifacts")
            
            # Use the enhanced artifact viewer component
            artifacts = st.session_state.state.get("artifacts", {})
            if artifacts:
                render_artifact_viewer(artifacts)
            else:
                # Check for artifact files in the artifacts directory
                artifacts_dir = Path("artifacts")
                if artifacts_dir.exists():
                    artifact_files = list(artifacts_dir.glob("*.md"))
                    if artifact_files:
                        file_artifacts = {}
                        for f in artifact_files:
                            file_artifacts[f.stem] = str(f)
                        render_artifact_viewer(file_artifacts)
                    else:
                        st.info("No artifacts generated yet. Complete the SDLC workflow to generate artifacts.")
                else:
                    st.info("No artifacts generated yet. Complete the SDLC workflow to generate artifacts.")

        # ---------------- Tab 9: Agent Dashboard ----------------
        with tabs[8]:
            st.header("🤖 Agent Dashboard")
            
            # Use the enhanced agent dashboard component
            if isinstance(graph_executor, AgenticGraphExecutor) and graph_executor.is_using_agents():
                try:
                    agent_status = graph_executor.get_agent_status()
                    session_info = None
                    if st.session_state.task_id:
                        session_info = graph_executor.get_session_info(st.session_state.task_id)
                    
                    render_agent_dashboard(
                        agent_status=agent_status,
                        current_stage=st.session_state.stage,
                        session_info=session_info
                    )
                except Exception as e:
                    st.error(f"Failed to load agent dashboard: {e}")
            else:
                st.warning("⚠️ Agent mode is not active. Enable 'Use AI Agents' in the sidebar to use the multi-agent system.")
                st.info("In Legacy mode, the system uses the traditional LangGraph-based workflow without specialized agents.")
                
                # Show what agents would be available
                st.subheader("Available Agents (when enabled)")
                agent_descriptions = {
                    "🎯 Supervisor Agent": "Orchestrates all other agents, plans execution, monitors progress",
                    "📋 Business Analyst Agent": "Analyzes requirements, generates user stories",
                    "🏗️ Architect Agent": "Creates system design and architecture documents",
                    "💻 Developer Agent": "Generates code based on requirements and design",
                    "🔍 Code Review Agent": "Reviews code quality, suggests improvements",
                    "🔒 Security Agent": "Performs security analysis, identifies vulnerabilities",
                    "🧪 QA Agent": "Creates test cases, performs testing, reports issues",
                    "🚀 DevOps Agent": "Handles deployment, CI/CD configuration",
                }
                
                for agent, description in agent_descriptions.items():
                    st.markdown(f"**{agent}**: {description}")

        # ---------------- Tab 10: Integrations ----------------
        with tabs[9]:
            st.header("🔗 External Integrations")
            
            # Use the enhanced integrations panel component
            render_integrations_panel()

        # ---------------- Tab 11: Workflow Graph ----------------
        with tabs[10]:
            st.header("📊 Workflow Graph")
            st.write("Interactive visualization of the SDLC workflow.")
            
            # Prepare workflow state for visualization
            workflow_state = {
                "current_stage": st.session_state.stage,
                "completed_stages": [],
                "project_name": st.session_state.get("project_name", ""),
            }
            
            # Determine completed stages
            stage_order = [
                const.PROJECT_INITILIZATION,
                const.REQUIREMENT_COLLECTION,
                const.GENERATE_USER_STORIES,
                const.CREATE_DESIGN_DOC,
                const.CODE_GENERATION,
                const.SECURITY_REVIEW,
                const.WRITE_TEST_CASES,
                const.QA_TESTING,
                const.DEPLOYMENT,
                const.ARTIFACTS,
            ]
            current_idx = get_current_stage_index()
            workflow_state["completed_stages"] = stage_order[:current_idx]
            
            # Render workflow graph
            render_workflow_graph(workflow_state)
            
            # Show legend
            with st.expander("ℹ️ Legend"):
                st.markdown("""
                - 🟢 **Green nodes**: Completed stages
                - 🔵 **Blue node**: Current active stage
                - ⚪ **White nodes**: Pending stages
                - ➡️ **Arrows**: Workflow direction
                """)

        # ---------------- Tab 12: Live Execution Sandbox ----------------
        with tabs[11]:
            st.header("⚡ Live Execution Sandbox")
            st.write("Enter Python code below to execute it in a safe, isolated environment.")
            st.warning("⚠️ This is a basic sandbox with limited functionality. Avoid sensitive operations.")
            
            code_input = st.text_area(
                "Enter Python code:",
                height=200,
                placeholder="# Example:\nfor i in range(5):\n    print(f'Hello {i}')"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                run_button = st.button("▶️ Run Code", use_container_width=True, type="primary")
            with col2:
                st.markdown("")  # Spacer
            
            if run_button:
                if code_input.strip():
                    output = io.StringIO()
                    error_output = io.StringIO()
                    try:
                        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error_output):
                            restricted_globals = {
                                "__builtins__": {
                                    k: v for k, v in __builtins__.__dict__.items()
                                    if k in ['print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'tuple', 'set', 'sum', 'min', 'max', 'abs', 'round', 'sorted', 'enumerate', 'zip', 'map', 'filter']
                                }
                            }
                            exec(code_input, restricted_globals)
                        
                        st.success("✅ Execution successful!")
                        
                        if output.getvalue():
                            st.subheader("📤 Output:")
                            st.code(output.getvalue())
                        
                        if error_output.getvalue():
                            st.subheader("⚠️ Warnings:")
                            st.code(error_output.getvalue())
                            
                    except Exception as exec_error:
                        st.error(f"❌ Execution failed: {str(exec_error)}")
                else:
                    st.warning("Please enter some code to run.")

    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        import traceback
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())


# Entry point when running directly
if __name__ == "__main__":
    load_app()
