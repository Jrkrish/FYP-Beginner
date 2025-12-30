"use client";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const menuItems = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "projects", label: "Projects", icon: "📁" },
    { id: "agents", label: "Agents", icon: "🤖" },
    { id: "workflows", label: "Workflows", icon: "🔄" },
    { id: "artifacts", label: "Artifacts", icon: "📄" },
    { id: "integrations", label: "Integrations", icon: "🔗" },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen">
      <nav className="p-4 space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full text-left px-4 py-3 rounded-lg flex items-center space-x-3 transition-colors ${
              activeTab === item.id
                ? "bg-blue-50 text-blue-600 font-medium"
                : "text-gray-700 hover:bg-gray-50"
            }`}
          >
            <span className="text-xl">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
