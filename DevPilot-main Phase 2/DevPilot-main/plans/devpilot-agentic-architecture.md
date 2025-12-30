# DevPilot Dynamic AI Agentic SDLC System Architecture

## Executive Summary

Transform DevPilot from a static LangGraph-based SDLC workflow into a dynamic, enterprise-grade multi-agent system with autonomous collaboration, external integrations, multi-user support, and real-time collaboration features.

---

## Current State Analysis

### Existing Architecture
- **Framework**: LangGraph with StateGraph for workflow management
- **LLM Support**: Groq, Gemini, OpenAI
- **UI**: Streamlit with tab-based navigation
- **State Management**: Redis cache + MemorySaver
- **Workflow**: Linear SDLC phases with human-in-the-loop checkpoints

### Limitations
- Single LLM handles all tasks (no specialization)
- Static workflow - cannot adapt or parallelize
- No agent-to-agent communication
- Manual progression through UI
- No external tool integrations
- Single-user only

---

## Proposed Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DevPilot Platform                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Web UI    │  │  Slack Bot  │  │  Jira Sync  │  │   Linear Webhook    │ │
│  │  Dashboard  │  │ Integration │  │  Connector  │  │     Handler         │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                     │           │
│         └────────────────┴────────────────┴─────────────────────┘           │
│                                   │                                          │
│                          ┌────────┴────────┐                                │
│                          │   API Gateway   │                                │
│                          │  with Auth/RBAC │                                │
│                          └────────┬────────┘                                │
│                                   │                                          │
│  ┌────────────────────────────────┴────────────────────────────────────┐    │
│  │                      Agent Orchestration Layer                       │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │                    Supervisor Agent                           │   │    │
│  │  │  - Workflow Planning    - Agent Coordination                  │   │    │
│  │  │  - Task Delegation      - Conflict Resolution                 │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  │                                │                                     │    │
│  │         ┌──────────────────────┼──────────────────────┐             │    │
│  │         ▼                      ▼                      ▼             │    │
│  │  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐     │    │
│  │  │  Planning   │        │ Development │        │  Operations │     │    │
│  │  │    Team     │        │    Team     │        │    Team     │     │    │
│  │  ├─────────────┤        ├─────────────┤        ├─────────────┤     │    │
│  │  │ BA Agent    │        │ Dev Agent   │        │ DevOps Agent│     │    │
│  │  │ Architect   │        │ Code Review │        │ QA Agent    │     │    │
│  │  │ Agent       │        │ Agent       │        │ Security    │     │    │
│  │  │             │        │             │        │ Agent       │     │    │
│  │  └─────────────┘        └─────────────┘        └─────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│  ┌────────────────────────────────┴────────────────────────────────────┐    │
│  │                        Shared Services Layer                         │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │  Memory  │ │  Event   │ │ Artifact │ │ Notifica │ │   LLM    │   │    │
│  │  │  Store   │ │   Bus    │ │  Store   │ │   tion   │ │  Router  │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│  ┌────────────────────────────────┴────────────────────────────────────┐    │
│  │                         Data Layer                                   │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐   │    │
│  │  │PostgreSQL│ │  Redis   │ │ Vector DB│ │    File Storage      │   │    │
│  │  │  Users   │ │  Cache   │ │ Embeddings│ │    Artifacts        │   │    │
│  │  │ Projects │ │  State   │ │  Memory  │ │                      │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Multi-Agent Architecture

### 1.1 Specialized Agents

#### Supervisor Agent
- **Role**: Orchestrates the entire SDLC workflow
- **Capabilities**:
  - Analyzes project requirements to create execution plan
  - Delegates tasks to specialized agents
  - Monitors progress and handles failures
  - Resolves conflicts between agents
  - Adapts workflow based on project context

#### Business Analyst Agent
- **Role**: Requirements analysis and user story generation
- **Capabilities**:
  - Extracts requirements from various inputs
  - Generates detailed user stories
  - Creates acceptance criteria
  - Prioritizes features using MoSCoW method
  - Syncs with Jira/Linear for issue creation

#### Architect Agent
- **Role**: System design and technical planning
- **Capabilities**:
  - Creates system architecture diagrams
  - Defines technology stack
  - Designs database schemas
  - Specifies API contracts
  - Reviews architectural decisions

#### Developer Agent
- **Role**: Code generation and implementation
- **Capabilities**:
  - Generates production-ready code
  - Follows design documents
  - Creates modular, testable code
  - Handles multiple programming languages
  - Implements design patterns

#### Code Review Agent
- **Role**: Code quality assurance
- **Capabilities**:
  - Reviews code for best practices
  - Identifies bugs and anti-patterns
  - Suggests improvements
  - Ensures coding standards compliance
  - Provides actionable feedback

#### Security Agent
- **Role**: Security analysis and recommendations
- **Capabilities**:
  - Performs SAST analysis
  - Identifies vulnerabilities (OWASP Top 10)
  - Recommends security fixes
  - Reviews authentication/authorization
  - Validates input sanitization

#### QA Agent
- **Role**: Testing and quality assurance
- **Capabilities**:
  - Generates comprehensive test cases
  - Creates unit, integration, and E2E tests
  - Simulates test execution
  - Reports test coverage
  - Identifies edge cases

#### DevOps Agent
- **Role**: Deployment and operations
- **Capabilities**:
  - Creates deployment configurations
  - Generates CI/CD pipelines
  - Defines infrastructure as code
  - Plans deployment strategies
  - Monitors deployment readiness

### 1.2 Agent Communication Protocol

```python
class AgentMessage:
    sender: str           # Agent ID
    recipient: str        # Agent ID or BROADCAST
    message_type: str     # REQUEST, RESPONSE, NOTIFY, DELEGATE
    priority: int         # 1-5 (1 = highest)
    payload: dict         # Message content
    context: dict         # Shared context
    correlation_id: str   # For request-response tracking
    timestamp: datetime
```

### 1.3 Agent State Machine

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  IDLE   │────▶│ WORKING │────▶│REVIEWING│────▶│COMPLETED│
└─────────┘     └─────────┘     └─────────┘     └─────────┘
     ▲               │               │               │
     │               ▼               ▼               │
     │          ┌─────────┐     ┌─────────┐         │
     └──────────│ BLOCKED │◀────│  ERROR  │◀────────┘
                └─────────┘     └─────────┘
```

---

## 2. External Integrations

### 2.1 Slack Integration

```
┌─────────────────────────────────────────────────────┐
│                  Slack Integration                   │
├─────────────────────────────────────────────────────┤
│  Commands:                                           │
│  /devpilot start [project-name] - Start new project │
│  /devpilot status - Get current status              │
│  /devpilot approve [stage] - Approve current stage  │
│  /devpilot feedback [text] - Provide feedback       │
│                                                      │
│  Notifications:                                      │
│  - Stage completion alerts                          │
│  - Review requests                                  │
│  - Error notifications                              │
│  - Daily progress summaries                         │
│                                                      │
│  Interactive:                                        │
│  - Approve/Reject buttons                           │
│  - Feedback modals                                  │
│  - Agent conversation threads                       │
└─────────────────────────────────────────────────────┘
```

### 2.2 Jira Integration

```
┌─────────────────────────────────────────────────────┐
│                   Jira Integration                   │
├─────────────────────────────────────────────────────┤
│  Sync Features:                                      │
│  - Auto-create Epics from requirements              │
│  - Create Stories from user stories                 │
│  - Create Sub-tasks for implementation              │
│  - Link test cases to stories                       │
│  - Update status based on SDLC progress             │
│                                                      │
│  Bidirectional:                                      │
│  - Import existing Jira issues as requirements      │
│  - Sync comments and feedback                       │
│  - Update story points/estimates                    │
│                                                      │
│  Webhooks:                                           │
│  - Issue status changes                             │
│  - Comment additions                                │
│  - Sprint updates                                   │
└─────────────────────────────────────────────────────┘
```

### 2.3 Linear Integration

```
┌─────────────────────────────────────────────────────┐
│                  Linear Integration                  │
├─────────────────────────────────────────────────────┤
│  Features:                                           │
│  - Create issues from user stories                  │
│  - Sync project/team structure                      │
│  - Auto-assign based on agent recommendations       │
│  - Link to cycles/projects                          │
│  - Real-time status sync                            │
│                                                      │
│  API Operations:                                     │
│  - GraphQL mutations for issue CRUD                 │
│  - Webhook subscriptions                            │
│  - Batch operations for bulk sync                   │
└─────────────────────────────────────────────────────┘
```

---

## 3. Multi-User & RBAC System

### 3.1 User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **Admin** | System administrator | Full access, user management, settings |
| **Project Owner** | Project lead | Create projects, approve stages, manage team |
| **Developer** | Team member | View projects, provide feedback, review code |
| **Viewer** | Read-only access | View projects and artifacts |
| **API User** | External integrations | API access with scoped permissions |

### 3.2 Permission Matrix

```
┌────────────────────┬───────┬─────────┬───────────┬────────┬──────────┐
│ Action             │ Admin │ Owner   │ Developer │ Viewer │ API User │
├────────────────────┼───────┼─────────┼───────────┼────────┼──────────┤
│ Create Project     │   ✓   │    ✓    │     ✗     │   ✗    │    ✗     │
│ Delete Project     │   ✓   │    ✓    │     ✗     │   ✗    │    ✗     │
│ View Project       │   ✓   │    ✓    │     ✓     │   ✓    │    ✓     │
│ Approve Stages     │   ✓   │    ✓    │     ✗     │   ✗    │    ✗     │
│ Provide Feedback   │   ✓   │    ✓    │     ✓     │   ✗    │    ✗     │
│ Download Artifacts │   ✓   │    ✓    │     ✓     │   ✓    │    ✓     │
│ Manage Users       │   ✓   │    ✗    │     ✗     │   ✗    │    ✗     │
│ Configure Agents   │   ✓   │    ✓    │     ✗     │   ✗    │    ✗     │
│ View Audit Logs    │   ✓   │    ✓    │     ✗     │   ✗    │    ✗     │
│ API Access         │   ✓   │    ✓    │     ✓     │   ✗    │    ✓     │
└────────────────────┴───────┴─────────┴───────────┴────────┴──────────┘
```

### 3.3 Authentication Flow

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  Client  │─────▶│  Auth    │─────▶│  Token   │─────▶│   API    │
│          │      │ Provider │      │ Validate │      │ Gateway  │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
        ┌──────────┐      ┌──────────┐
        │  OAuth2  │      │  API Key │
        │  SSO     │      │  Auth    │
        └──────────┘      └──────────┘
```

---

## 4. Collaboration Features

### 4.1 Conversation Sharing

- **Project Conversations**: All team members can view agent interactions
- **Threaded Discussions**: Comment on specific artifacts or decisions
- **@Mentions**: Tag team members for review or input
- **Conversation Export**: Export conversations for documentation

### 4.2 Real-time Collaboration

```
┌─────────────────────────────────────────────────────┐
│              WebSocket Event System                  │
├─────────────────────────────────────────────────────┤
│  Events:                                             │
│  - agent.started        - Stage transitions         │
│  - agent.completed      - Artifact updates          │
│  - agent.error          - User actions              │
│  - feedback.submitted   - Team notifications        │
│                                                      │
│  Channels:                                           │
│  - project:{id}         - Project-specific events   │
│  - user:{id}            - User notifications        │
│  - team:{id}            - Team broadcasts           │
│  - global               - System announcements      │
└─────────────────────────────────────────────────────┘
```

### 4.3 Activity Feed

- Live stream of all project activities
- Filterable by agent, stage, or user
- Actionable notifications
- Historical audit trail

---

## 5. Enhanced UI Design

### 5.1 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  DevPilot                              🔔 Notifications  👤 User    │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐                                                        │
│  │ Projects│  ┌─────────────────────────────────────────────────┐  │
│  │ ─────── │  │                 Project: E-Commerce              │  │
│  │ E-Comm  │  │                                                  │  │
│  │ CRM App │  │  ┌──────────────────────────────────────────┐   │  │
│  │ API Srv │  │  │         Agent Activity Timeline           │   │  │
│  │         │  │  │  ▓▓▓▓ BA Agent ───────────────────────   │   │  │
│  │ + New   │  │  │  ░░░░ Architect Agent ─────────────       │   │  │
│  │         │  │  │       Dev Agent ───────                   │   │  │
│  ├─────────┤  │  └──────────────────────────────────────────┘   │  │
│  │ Integr. │  │                                                  │  │
│  │ ─────── │  │  ┌─────────────┐  ┌─────────────────────────┐   │  │
│  │ Slack ✓ │  │  │ Current     │  │ Agent Chat              │   │  │
│  │ Jira  ✓ │  │  │ Stage:      │  │ ───────────────────────│   │  │
│  │ Linear  │  │  │ Code Review │  │ Dev: Code ready        │   │  │
│  │         │  │  │             │  │ Review: Analyzing...   │   │  │
│  ├─────────┤  │  │ Progress:   │  │ Security: Queued       │   │  │
│  │ Team    │  │  │ [████░░░░]  │  │                        │   │  │
│  │ ─────── │  │  │ 45%         │  │ [Type message...]      │   │  │
│  │ 👤 John │  │  └─────────────┘  └─────────────────────────┘   │  │
│  │ 👤 Jane │  │                                                  │  │
│  │ 👤 Bob  │  │  ┌─────────────────────────────────────────┐    │  │
│  └─────────┘  │  │ Artifacts                                │    │  │
│               │  │ ├─ 📄 User Stories.md                   │    │  │
│               │  │ ├─ 📄 Design Document.md                │    │  │
│               │  │ ├─ 📁 Generated Code                    │    │  │
│               │  │ └─ 📄 Test Cases.md                     │    │  │
│               │  └─────────────────────────────────────────┘    │  │
│               └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Key UI Components

1. **Agent Visualization Panel**
   - Live status of each agent
   - Current task indicator
   - Communication flow visualization

2. **Interactive Chat Interface**
   - Chat with specific agents
   - View agent reasoning
   - Inject manual instructions

3. **Workflow Graph**
   - Visual representation of SDLC flow
   - Clickable nodes for details
   - Real-time progress highlighting

4. **Artifact Viewer**
   - Syntax-highlighted code preview
   - Markdown rendering
   - Diff view for revisions

---

## 6. Technical Implementation

### 6.1 New Directory Structure

```
src/dev_pilot/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── supervisor_agent.py
│   ├── ba_agent.py
│   ├── architect_agent.py
│   ├── developer_agent.py
│   ├── code_review_agent.py
│   ├── security_agent.py
│   ├── qa_agent.py
│   └── devops_agent.py
├── orchestration/
│   ├── __init__.py
│   ├── agent_registry.py
│   ├── message_bus.py
│   ├── workflow_engine.py
│   └── task_queue.py
├── integrations/
│   ├── __init__.py
│   ├── slack/
│   │   ├── bot.py
│   │   ├── commands.py
│   │   └── notifications.py
│   ├── jira/
│   │   ├── client.py
│   │   ├── sync.py
│   │   └── webhooks.py
│   └── linear/
│       ├── client.py
│       ├── sync.py
│       └── webhooks.py
├── auth/
│   ├── __init__.py
│   ├── models.py
│   ├── rbac.py
│   ├── oauth.py
│   └── middleware.py
├── collaboration/
│   ├── __init__.py
│   ├── conversations.py
│   ├── notifications.py
│   └── activity.py
├── memory/
│   ├── __init__.py
│   ├── vector_store.py
│   ├── context_manager.py
│   └── embeddings.py
├── ui/
│   ├── __init__.py
│   ├── streamlit_ui/  (existing, enhanced)
│   └── api/
│       ├── routes/
│       ├── websocket.py
│       └── events.py
└── ...
```

### 6.2 Database Schema

```sql
-- Users and Teams
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    role VARCHAR(50),
    created_at TIMESTAMP
);

CREATE TABLE teams (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP
);

CREATE TABLE team_members (
    team_id UUID REFERENCES teams(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(50),
    PRIMARY KEY (team_id, user_id)
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    team_id UUID REFERENCES teams(id),
    owner_id UUID REFERENCES users(id),
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE project_state (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    state_data JSONB,
    version INT,
    created_at TIMESTAMP
);

-- Agent Activity
CREATE TABLE agent_activities (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    agent_type VARCHAR(50),
    action VARCHAR(100),
    input_data JSONB,
    output_data JSONB,
    duration_ms INT,
    created_at TIMESTAMP
);

-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    user_id UUID REFERENCES users(id),
    message TEXT,
    agent_response TEXT,
    created_at TIMESTAMP
);

-- Integrations
CREATE TABLE integration_configs (
    id UUID PRIMARY KEY,
    team_id UUID REFERENCES teams(id),
    type VARCHAR(50),
    config JSONB,
    enabled BOOLEAN,
    created_at TIMESTAMP
);
```

### 6.3 Technology Stack Additions

| Component | Technology | Purpose |
|-----------|------------|---------|
| Database | PostgreSQL | Primary data store |
| Vector DB | ChromaDB/Pinecone | Agent memory & embeddings |
| Message Queue | Redis Pub/Sub | Agent communication |
| WebSocket | FastAPI WebSocket | Real-time updates |
| Auth | OAuth2 + JWT | Authentication |
| Task Queue | Celery | Background processing |
| Monitoring | OpenTelemetry | Observability |

---

## 7. Implementation Phases

### Phase 1: Core Multi-Agent System
- Implement base agent architecture
- Create specialized agents
- Build agent communication protocol
- Integrate supervisor orchestration
- Migrate existing nodes to agent pattern

### Phase 2: Enhanced Backend
- PostgreSQL integration
- Vector store for memory
- WebSocket server
- Event bus implementation
- API restructuring

### Phase 3: External Integrations
- Slack bot implementation
- Jira connector
- Linear integration
- Webhook handlers

### Phase 4: Multi-User & Security
- User authentication
- RBAC implementation
- Team management
- API key system

### Phase 5: UI Enhancement
- New dashboard design
- Agent visualization
- Real-time updates
- Collaboration features

### Phase 6: Advanced Features
- Conversation sharing
- Activity feed
- Audit logging
- Analytics dashboard

---

## 8. Agent Workflow Example

```
User Request: "Build an e-commerce platform"
                    │
                    ▼
            ┌───────────────┐
            │   Supervisor  │ ─── Analyzes request
            │     Agent     │     Creates execution plan
            └───────┬───────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│ BA Agent  │ │ (waits)   │ │ (waits)   │
│ Generates │ │ Architect │ │ Developer │
│  Stories  │ │           │ │           │
└─────┬─────┘ └───────────┘ └───────────┘
      │
      ▼ (Stories ready, notifies Supervisor)
┌───────────────┐
│   Supervisor  │ ─── Triggers next agents
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   Architect   │ ─── Creates design docs
│     Agent     │     Can ask BA for clarification
└───────┬───────┘
        │
        ▼ (Design ready)
┌───────────────┐
│   Developer   │ ─── Generates code
│     Agent     │     Follows architecture
└───────┬───────┘
        │
        ├────────────────┐
        ▼                ▼
┌───────────────┐ ┌───────────────┐
│ Code Review   │ │   Security    │ ─── Parallel review
│    Agent      │ │    Agent      │
└───────┬───────┘ └───────┬───────┘
        │                 │
        └────────┬────────┘
                 ▼
         ┌───────────────┐
         │   Developer   │ ─── Fixes based on reviews
         │     Agent     │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │   QA Agent    │ ─── Generates tests
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │ DevOps Agent  │ ─── Deployment config
         └───────────────┘
```

---

## Next Steps

After approval of this architecture, I will:

1. Create detailed implementation plan for Phase 1
2. Design the base agent class and communication protocol
3. Implement the supervisor agent
4. Migrate existing functionality to new agent-based architecture
5. Add real-time communication infrastructure

Would you like me to proceed with this architecture or make any modifications?
