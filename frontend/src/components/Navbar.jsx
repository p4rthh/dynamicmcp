import React from 'react';
import { RefreshCw } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, toolsCount = 0, onRefresh, loading }) {
  return (
    <header className="border-b border-base-800 bg-base-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          {/* Logo / Brand */}
          <div className="flex items-center space-x-3">
            <span className="font-semibold text-sm tracking-tight text-white font-sans">
              Dynamic<span className="text-base-400">MCP</span>
            </span>
            <span className="text-[11px] font-mono text-base-500 border-l border-base-800 pl-3 hidden sm:inline">
              Personal Agent Runtime
            </span>
          </div>

          {/* Minimalist Segmented Control */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center p-0.5 rounded-lg bg-base-850 border border-base-800 text-xs">
              <button
                onClick={() => setActiveTab('playground')}
                className={`px-3 py-1 rounded-md font-medium transition-all ${
                  activeTab === 'playground'
                    ? 'bg-base-700 text-white shadow-sm'
                    : 'text-base-400 hover:text-base-200'
                }`}
              >
                Assemble & Test
              </button>

              <button
                onClick={() => setActiveTab('tools')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
                  activeTab === 'tools'
                    ? 'bg-base-700 text-white shadow-sm'
                    : 'text-base-400 hover:text-base-200'
                }`}
              >
                <span>Installed</span>
                {toolsCount > 0 && (
                  <span className="px-1.5 py-0.2 rounded bg-base-800 text-base-300 font-mono text-[10px]">
                    {toolsCount}
                  </span>
                )}
              </button>
            </div>

            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 rounded-md hover:bg-base-800 text-base-400 hover:text-base-200 transition-colors border border-transparent hover:border-base-700"
              title="Refresh State"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-white' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
