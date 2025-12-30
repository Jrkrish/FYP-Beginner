# DevPilot UI Implementation - Real-Time Dynamic Features

## Overview

This document provides detailed implementation specifications for real-time, dynamic UI components that will enhance the DevPilot Streamlit application. All components will feature live data updates, dynamic state management, and interactive user experiences.

---

## 1. Real-Time Progress Tracker

### Component: `progress_tracker.py`

**Purpose**: Dynamic visual progress indicator that updates in real-time as SDLC phases complete

**Technical Implementation**:

```python
# Component Structure
class ProgressTracker:
    def __init__:
        - session_state reference for current_stage
        - stages configuration list
        - auto_refresh interval - default 2 seconds
    
    def render:
        - Fetch current state from session/Redis
        - Generate HTML/CSS for stepper
        - Apply dynamic classes based on state
        - Handle click events for navigation
    
    def get_stage_status:
        - Query AgenticGraphExecutor for live state
        - Return: completed, current, pending, error
    
    def on_stage_click:
        - Navigate to corresponding tab
        - Update session state
```

**Live State Sync**:
```python
# Real-time state polling
def poll_state_updates:
    current_state = graph_executor.get_updated_state(task_id)
    if state_changed(current_state, cached_state):
        update_ui_state(current_state)
        trigger_rerun()
```

**HTML Template**:
```html
<div class="progress-tracker" id="sdlc-progress">
    <div class="progress-line">
        <div class="progress-fill" style="width: {completion_percentage}%"></div>
    </div>
    {for each phase}
    <div class="step {status}" data-phase="{phase_id}" onclick="navigateToPhase('{phase_id}')">
        <div class="step-icon">{icon}</div>
        <div class="step-label">{name}</div>
        <div class="step-status">{status_indicator}</div>
    </div>
    {endfor}
</div>
```

---

## 2. Real-Time Agent Dashboard

### Component: `agent_dashboard.py`

**Purpose**: Live monitoring of all AI agents with real-time status updates

**Features**:
1. Live agent state polling every 2 seconds
2. Animated status transitions
3. Real-time task progress
4. Live activity feed
5. Performance metrics graphs

**Technical Implementation**:

```python
class AgentDashboard:
    def __init__:
        - graph_executor reference
        - refresh_interval = 2
        - activity_log_limit = 50
    
    def render:
        - System overview metrics
        - Agent cards grid
        - Activity timeline
        - Live feed
    
    def fetch_live_status:
        - Call graph_executor.get_agent_status()
        - Parse agent states, metrics
        - Calculate system health
        - Return formatted data
    
    def render_agent_card:
        - Agent name and type
        - Live status indicator with animation
        - Current task if any
        - Task metrics
        - Mini progress bar
    
    def render_activity_feed:
        - Fetch recent activities from context_manager
        - Display in reverse chronological order
        - Color-code by event type
        - Auto-scroll to latest
```

**Real-Time Update Pattern**:
```python
# Using streamlit-autorefresh for polling
from streamlit_autorefresh import st_autorefresh

def render_dashboard:
    # Auto-refresh every 2 seconds
    count = st_autorefresh(interval=2000, limit=None, key="agent_refresh")
    
    # Fetch fresh data on each refresh
    agent_status = graph_executor.get_agent_status()
    
    # Render with latest data
    render_metrics(agent_status)
    render_agent_cards(agent_status.get("agents", {}))
    render_activity_feed()
```

**Agent Card HTML**:
```html
<div class="agent-card {state_class}" data-agent="{agent_id}">
    <div class="agent-header">
        <span class="agent-icon">{icon}</span>
        <span class="agent-name">{name}</span>
        <span class="status-indicator {state}">
            <span class="pulse-dot"></span>
        </span>
    </div>
    <div class="agent-body">
        <div class="current-task">{current_task or "Idle"}</div>
        <div class="metrics-row">
            <span class="metric">✓ {tasks_completed}</span>
            <span class="metric">⚠ {tasks_failed}</span>
            <span class="metric">📨 {messages_sent}</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {progress}%"></div>
        </div>
    </div>
</div>
```

**CSS for Animated Status**:
```css
.status-indicator .pulse-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

.status-indicator.active .pulse-dot {
    background: #48bb78;
    animation: pulse 1.5s infinite;
}

.status-indicator.working .pulse-dot {
    background: #3182ce;
    animation: pulse 0.8s infinite;
}

.status-indicator.idle .pulse-dot {
    background: #a0aec0;
}

.status-indicator.error .pulse-dot {
    background: #e53e3e;
    animation: pulse 0.5s infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.3); opacity: 0.7; }
}
```

---

## 3. Live Integrations Tab

### Component: `integrations_panel.py`

**Purpose**: Dynamic integration configuration with live connection testing

**Features**:
1. Real-time connection status checking
2. Live test button with immediate feedback
3. Event log with auto-refresh
4. Configuration validation on input

**Technical Implementation**:

```python
class IntegrationsPanel:
    def __init__:
        - integration_manager reference
        - session_state for configs
    
    def render:
        - Integration cards grid
        - Each card has live status
        - Expandable configuration
        - Test and save buttons
    
    def test_connection:
        - Call integration.health_check()
        - Display result in real-time
        - Update status indicator
        - Show error details if failed
    
    def render_event_log:
        - Fetch from integration_manager.get_metrics()
        - Display recent events
        - Auto-refresh every 5 seconds
    
    def save_config:
        - Validate inputs
        - Update session_state
        - Re-test connection
        - Show success/error toast
```

**Integration Card with Live Testing**:
```python
def render_integration_card(integration_type, config):
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### {INTEGRATION_ICONS[integration_type]} {integration_type.title()}")
        
        with col2:
            status = get_live_status(integration_type)
            st.markdown(f"**{STATUS_INDICATORS[status]}**")
        
        with col3:
            enabled = st.toggle("Enable", value=config.get("enabled", False))
        
        if enabled:
            render_config_form(integration_type, config)
            
            col_test, col_save = st.columns(2)
            with col_test:
                if st.button(f"🧪 Test Connection", key=f"test_{integration_type}"):
                    with st.spinner("Testing connection..."):
                        result = test_connection_live(integration_type, config)
                        if result.success:
                            st.success(f"✅ Connected! {result.message}")
                        else:
                            st.error(f"❌ Failed: {result.error}")
            
            with col_save:
                if st.button(f"💾 Save", key=f"save_{integration_type}"):
                    save_integration_config(integration_type, config)
                    st.success("Configuration saved!")
```

**Live Event Log**:
```python
def render_event_log(integration_type):
    st.subheader("📜 Recent Events")
    
    # Auto-refresh container
    events = fetch_integration_events(integration_type, limit=10)
    
    for event in events:
        event_class = "success" if event.success else "error"
        st.markdown(f"""
        <div class="event-item {event_class}">
            <span class="event-time">{event.timestamp}</span>
            <span class="event-type">{event.event_type}</span>
            <span class="event-status">{STATUS_ICONS[event.status]}</span>
        </div>
        """, unsafe_allow_html=True)
```

---

## 4. Dynamic Artifact Preview

### Component: `artifact_viewer.py`

**Purpose**: Real-time artifact preview with syntax highlighting and live updates

**Features**:
1. Markdown rendering with live preview
2. Code syntax highlighting
3. File tree for multi-file artifacts
4. Diff view for revisions
5. Copy and download buttons

**Technical Implementation**:

```python
class ArtifactViewer:
    def __init__:
        - artifact_path
        - artifact_type: markdown, code, mixed
    
    def render:
        - Detect artifact type
        - Apply appropriate renderer
        - Add action buttons
    
    def render_markdown:
        - Parse markdown content
        - Apply custom CSS
        - Render with st.markdown
    
    def render_code:
        - Detect language
        - Apply syntax highlighting
        - Add line numbers
        - Add copy button
    
    def render_file_tree:
        - Parse multi-file structure
        - Create collapsible tree
        - Handle file selection
```

**Code Preview with Highlighting**:
```python
def render_code_preview(code_content, language="python"):
    # Parse code blocks from markdown
    code_blocks = extract_code_blocks(code_content)
    
    for i, block in enumerate(code_blocks):
        filename = block.get("filename", f"file_{i}")
        code = block.get("code")
        lang = block.get("language", language)
        
        with st.expander(f"📄 {filename}", expanded=i==0):
            # Syntax highlighted code
            st.code(code, language=lang)
            
            # Copy button
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("📋 Copy", key=f"copy_{i}"):
                    st.write(f"<script>navigator.clipboard.writeText(`{code}`)</script>", 
                             unsafe_allow_html=True)
                    st.success("Copied!")
```

**Artifact Diff View**:
```python
def render_diff_view(old_content, new_content):
    import difflib
    
    differ = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        lineterm=""
    )
    
    diff_html = []
    for line in differ:
        if line.startswith("+"):
            diff_html.append(f'<div class="diff-add">{line}</div>')
        elif line.startswith("-"):
            diff_html.append(f'<div class="diff-remove">{line}</div>')
        else:
            diff_html.append(f'<div class="diff-context">{line}</div>')
    
    st.markdown(f'<div class="diff-view">{"".join(diff_html)}</div>', 
                unsafe_allow_html=True)
```

---

## 5. Live Notification System

### Component: `notifications.py`

**Purpose**: Real-time toast notifications for stage transitions and events

**Features**:
1. Non-blocking toast notifications
2. Different types: success, warning, error, info
3. Auto-dismiss with configurable duration
4. Notification history
5. Sound alerts optional

**Technical Implementation**:

```python
class NotificationManager:
    def __init__:
        - notification_queue in session_state
        - auto_dismiss_seconds = 5
    
    def notify:
        - Add to queue
        - Trigger render
    
    def render_notifications:
        - Display queued notifications
        - Apply animation
        - Handle dismiss
    
    def clear:
        - Clear all notifications
```

**Toast Component**:
```python
def show_toast(message, type="info", duration=5):
    toast_id = f"toast_{uuid.uuid4().hex[:8]}"
    
    toast_html = f"""
    <div id="{toast_id}" class="toast-notification toast-{type}">
        <div class="toast-icon">{TOAST_ICONS[type]}</div>
        <div class="toast-content">
            <div class="toast-message">{message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    </div>
    <script>
        setTimeout(function() {{
            document.getElementById("{toast_id}").remove();
        }}, {duration * 1000});
    </script>
    """
    
    st.markdown(toast_html, unsafe_allow_html=True)
```

**Stage Transition Notifications**:
```python
def notify_stage_change(old_stage, new_stage, status):
    messages = {
        "approved": f"✅ {STAGE_NAMES[old_stage]} approved! Moving to {STAGE_NAMES[new_stage]}",
        "feedback": f"📝 Feedback submitted for {STAGE_NAMES[old_stage]}. Revising...",
        "error": f"❌ Error in {STAGE_NAMES[old_stage]}. Please review.",
    }
    
    toast_type = {
        "approved": "success",
        "feedback": "warning", 
        "error": "error",
    }
    
    show_toast(messages[status], toast_type[status])
```

---

## 6. Interactive Workflow Graph

### Component: `workflow_graph.py`

**Purpose**: Dynamic, clickable workflow visualization with live state

**Features**:
1. SVG-based workflow graph
2. Clickable nodes for navigation
3. Real-time state highlighting
4. Animated current phase
5. Zoom and pan controls

**Technical Implementation**:

```python
class WorkflowGraph:
    def __init__:
        - current_stage
        - stage_statuses dict
    
    def render:
        - Generate Mermaid diagram
        - Apply dynamic styling
        - Inject click handlers
    
    def generate_mermaid:
        - Build graph definition
        - Apply node colors by status
        - Add edge animations
```

**Dynamic Mermaid Graph**:
```python
def render_workflow_graph(current_stage, statuses):
    # Build dynamic mermaid diagram
    mermaid_def = """
    graph LR
        REQ[📋 Requirements]
        US[📖 User Stories]
        DD[🏗️ Design]
        CG[💻 Code]
        SR[🔒 Security]
        TC[🧪 Tests]
        QA[✅ QA]
        DEP[🚀 Deploy]
        
        REQ --> US
        US --> DD
        DD --> CG
        CG --> SR
        SR --> TC
        TC --> QA
        QA --> DEP
    """
    
    # Apply dynamic classes
    style_defs = []
    for stage, status in statuses.items():
        if status == "completed":
            style_defs.append(f"style {STAGE_IDS[stage]} fill:#48bb78,color:#fff")
        elif status == "current":
            style_defs.append(f"style {STAGE_IDS[stage]} fill:#3182ce,color:#fff")
        elif status == "error":
            style_defs.append(f"style {STAGE_IDS[stage]} fill:#e53e3e,color:#fff")
    
    full_mermaid = mermaid_def + "\n" + "\n".join(style_defs)
    
    # Render using streamlit-mermaid
    from streamlit_mermaid import st_mermaid
    st_mermaid(full_mermaid, key="workflow_graph")
```

---

## 7. Enhanced Sidebar Components

### Component: `enhanced_sidebar.py`

**Purpose**: Live status indicators and quick actions in sidebar

**Features**:
1. Real-time agent mini-status
2. Integration connection indicators
3. Quick action buttons
4. Collapsible sections

**Technical Implementation**:

```python
def render_enhanced_sidebar(graph_executor, config):
    with st.sidebar:
        # Header
        st.markdown("# 🚀 DevPilot")
        st.caption("AI-Powered SDLC Automation")
        
        st.divider()
        
        # Execution Mode
        render_execution_mode_toggle()
        
        st.divider()
        
        # LLM Configuration
        render_llm_config(config)
        
        st.divider()
        
        # Live Agent Status Mini-Panel
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
            st.image("workflow_graph.png", use_column_width=True)


def render_agent_mini_status(graph_executor):
    st.markdown("### 🤖 Agents")
    
    if isinstance(graph_executor, AgenticGraphExecutor) and graph_executor.is_using_agents():
        try:
            status = graph_executor.get_agent_status()
            agents = status.get("agents", {})
            
            for agent_type, info in agents.items():
                state = info.get("state", "unknown")
                icon = AGENT_ICONS.get(agent_type, "🤖")
                status_color = STATE_COLORS.get(state, "gray")
                
                st.markdown(f"""
                <div style="display:flex;align-items:center;margin:4px 0;">
                    <span style="font-size:1.2em;margin-right:8px;">{icon}</span>
                    <span style="flex:1;">{info.get("name", agent_type)}</span>
                    <span style="color:{status_color};font-size:1.5em;">●</span>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Failed to get status: {e}")
    else:
        st.info("Enable Agent Mode")


def render_integration_status():
    st.markdown("### 🔗 Integrations")
    
    integrations = st.session_state.get("integrations", {})
    
    for name, config in integrations.items():
        enabled = config.get("enabled", False)
        icon = INTEGRATION_ICONS.get(name, "🔗")
        status = "🟢" if enabled else "🔴"
        
        st.markdown(f"{icon} {name.title()} {status}")
```

---

## 8. State Management for Real-Time Updates

### Enhanced Session State Structure

```python
# Initialize enhanced session state
def initialize_enhanced_session():
    if "ui_state" not in st.session_state:
        st.session_state.ui_state = {
            "last_refresh": datetime.now(),
            "pending_notifications": [],
            "agent_cache": {},
            "integration_cache": {},
            "artifact_versions": {},
            "activity_log": [],
        }
    
    if "refresh_triggers" not in st.session_state:
        st.session_state.refresh_triggers = {
            "agent_dashboard": 0,
            "integrations": 0,
            "artifacts": 0,
        }


# State sync helper
def sync_state_from_backend():
    if st.session_state.task_id:
        try:
            response = graph_executor.get_updated_state(st.session_state.task_id)
            st.session_state.state = response.get("state", {})
            st.session_state.ui_state["last_refresh"] = datetime.now()
        except Exception as e:
            logger.error(f"State sync failed: {e}")


# Trigger UI refresh when state changes
def check_for_updates():
    current_state = fetch_current_state()
    cached_state = st.session_state.get("state", {})
    
    if state_has_changed(current_state, cached_state):
        st.session_state.state = current_state
        return True
    return False
```

---

## 9. Component File Structure

```
src/dev_pilot/ui/
├── streamlit_ui/
│   ├── streamlit_app.py              # Main app - updated
│   ├── advanced_style.css            # Enhanced CSS
│   ├── custom.css                    # Custom styles
│   │
│   └── components/
│       ├── __init__.py               # Component exports
│       ├── progress_tracker.py       # Real-time progress
│       ├── agent_dashboard.py        # Live agent status
│       ├── integrations_panel.py     # Dynamic integrations
│       ├── artifact_viewer.py        # Live artifact preview
│       ├── notifications.py          # Toast system
│       ├── workflow_graph.py         # Interactive graph
│       ├── enhanced_sidebar.py       # Sidebar components
│       ├── state_manager.py          # State utilities
│       └── styles/
│           ├── progress.css
│           ├── agents.css
│           ├── integrations.css
│           ├── artifacts.css
│           └── notifications.css
```

---

## 10. Dependencies

```txt
# requirements.txt additions
streamlit>=1.29.0
streamlit-autorefresh>=1.0.0
streamlit-mermaid>=0.0.2
streamlit-extras>=0.3.0
streamlit-option-menu>=0.3.6
plotly>=5.18.0
```

---

## Implementation Order

1. **Phase 1 - Foundation**
   - Create component directory structure
   - Implement state_manager.py
   - Add enhanced CSS files
   - Update main streamlit_app.py to use components

2. **Phase 2 - Progress Tracker**
   - Implement progress_tracker.py
   - Integrate with main app header
   - Test real-time updates

3. **Phase 3 - Agent Dashboard**
   - Implement agent_dashboard.py
   - Add auto-refresh functionality
   - Create agent cards with animations

4. **Phase 4 - Integrations**
   - Implement integrations_panel.py
   - Add live connection testing
   - Create event log component

5. **Phase 5 - Artifacts & Notifications**
   - Implement artifact_viewer.py
   - Implement notifications.py
   - Add code syntax highlighting

6. **Phase 6 - Workflow & Sidebar**
   - Implement workflow_graph.py
   - Implement enhanced_sidebar.py
   - Final integration and testing

---

*Implementation Details Document*
*Created: December 20, 2024*
