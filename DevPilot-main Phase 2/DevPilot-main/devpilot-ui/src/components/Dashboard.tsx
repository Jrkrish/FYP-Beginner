"use client";

interface DashboardProps {
  activeTab: string;
}

export default function Dashboard({ activeTab }: DashboardProps) {
  const renderContent = () => {
    switch (activeTab) {
      case "overview":
        return <OverviewTab />;
      case "projects":
        return <ProjectsTab />;
      case "agents":
        return <AgentsTab />;
      case "workflows":
        return <WorkflowsTab />;
      case "artifacts":
        return <ArtifactsTab />;
      case "integrations":
        return <IntegrationsTab />;
      default:
        return <OverviewTab />;
    }
  };

  return <div className="space-y-6">{renderContent()}</div>;
}

function OverviewTab() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Dashboard Overview</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Active Projects" value="12" trend="+2" />
        <StatCard title="Running Agents" value="7" trend="+1" />
        <StatCard title="Completed Tasks" value="148" trend="+24" />
        <StatCard title="Success Rate" value="94%" trend="+3%" />
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-4">
          <ActivityItem 
            agent="BA Agent" 
            action="Generated requirements document" 
            time="5 minutes ago"
            status="success"
          />
          <ActivityItem 
            agent="Developer Agent" 
            action="Completed code implementation" 
            time="12 minutes ago"
            status="success"
          />
          <ActivityItem 
            agent="QA Agent" 
            action="Running test suite" 
            time="18 minutes ago"
            status="running"
          />
        </div>
      </div>
    </div>
  );
}

function ProjectsTab() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Projects</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <ProjectCard 
          name="E-Commerce Platform" 
          status="In Progress" 
          progress={65}
          agents={5}
        />
        <ProjectCard 
          name="Analytics Dashboard" 
          status="Testing" 
          progress={85}
          agents={3}
        />
        <ProjectCard 
          name="Mobile App Backend" 
          status="Planning" 
          progress={25}
          agents={2}
        />
      </div>
    </div>
  );
}

function AgentsTab() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">AI Agents</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <AgentCard name="Business Analyst" status="active" tasks={8} />
        <AgentCard name="Architect" status="active" tasks={5} />
        <AgentCard name="Developer" status="active" tasks={12} />
        <AgentCard name="QA Engineer" status="idle" tasks={0} />
        <AgentCard name="DevOps" status="active" tasks={3} />
        <AgentCard name="Security" status="idle" tasks={0} />
      </div>
    </div>
  );
}

function WorkflowsTab() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Workflows</h2>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600">Workflow visualization and management coming soon...</p>
      </div>
    </div>
  );
}

function ArtifactsTab() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Artifacts</h2>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="space-y-4">
          <ArtifactItem name="Requirements_Document.md" type="Markdown" size="24 KB" date="2 hours ago" />
          <ArtifactItem name="System_Architecture.pdf" type="PDF" size="156 KB" date="5 hours ago" />
          <ArtifactItem name="API_Implementation.py" type="Python" size="8 KB" date="1 day ago" />
          <ArtifactItem name="Test_Results.json" type="JSON" size="12 KB" date="2 days ago" />
        </div>
      </div>
    </div>
  );
}

function IntegrationsTab() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Integrations</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <IntegrationCard name="GitHub" status="connected" icon="🐙" />
        <IntegrationCard name="Jira" status="connected" icon="📋" />
        <IntegrationCard name="Slack" status="disconnected" icon="💬" />
      </div>
    </div>
  );
}

function StatCard({ title, value, trend }: { title: string; value: string; trend: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-sm text-gray-600 mb-1">{title}</p>
      <div className="flex items-end justify-between">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        <span className="text-sm text-green-600 font-medium">{trend}</span>
      </div>
    </div>
  );
}

function ActivityItem({ agent, action, time, status }: { agent: string; action: string; time: string; status: string }) {
  const statusColors = {
    success: "bg-green-100 text-green-800",
    running: "bg-blue-100 text-blue-800",
    error: "bg-red-100 text-red-800",
  };

  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1">
        <p className="font-medium text-gray-900">{agent}</p>
        <p className="text-sm text-gray-600">{action}</p>
      </div>
      <div className="flex items-center space-x-4">
        <span className="text-sm text-gray-500">{time}</span>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[status as keyof typeof statusColors]}`}>
          {status}
        </span>
      </div>
    </div>
  );
}

function ProjectCard({ name, status, progress, agents }: { name: string; status: string; progress: number; agents: number }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{name}</h3>
      <p className="text-sm text-gray-600 mb-4">{status}</p>
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">Progress</span>
          <span className="font-medium">{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${progress}%` }}></div>
        </div>
      </div>
      <p className="text-sm text-gray-600">{agents} agents assigned</p>
    </div>
  );
}

function AgentCard({ name, status, tasks }: { name: string; status: string; tasks: number }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
        <span className={`w-3 h-3 rounded-full ${status === "active" ? "bg-green-500" : "bg-gray-400"}`}></span>
      </div>
      <p className="text-sm text-gray-600">Status: {status}</p>
      <p className="text-sm text-gray-600">Active tasks: {tasks}</p>
    </div>
  );
}

function ArtifactItem({ name, type, size, date }: { name: string; type: string; size: string; date: string }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <div className="flex items-center space-x-4">
        <div className="w-10 h-10 bg-blue-100 rounded flex items-center justify-center">
          <span className="text-xl">📄</span>
        </div>
        <div>
          <p className="font-medium text-gray-900">{name}</p>
          <p className="text-sm text-gray-600">{type} • {size}</p>
        </div>
      </div>
      <span className="text-sm text-gray-500">{date}</span>
    </div>
  );
}

function IntegrationCard({ name, status, icon }: { name: string; status: string; icon: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center space-x-4 mb-4">
        <span className="text-4xl">{icon}</span>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
          <span className={`text-sm ${status === "connected" ? "text-green-600" : "text-gray-500"}`}>
            {status}
          </span>
        </div>
      </div>
      <button className="w-full px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">
        Configure
      </button>
    </div>
  );
}
