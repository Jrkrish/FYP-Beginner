"use client";

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-blue-600">DevPilot</h1>
          <span className="text-sm text-gray-500">AI-Powered SDLC Platform</span>
        </div>
        <div className="flex items-center space-x-4">
          <button className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900">
            Settings
          </button>
          <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">
            New Project
          </button>
        </div>
      </div>
    </header>
  );
}
