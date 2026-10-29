import React from 'react';
import { Terminal, Layers, RefreshCw } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, toolsCount = 0, onRefresh, loading }) {
  return (
    <header className="border-b border-cyber-800/80 bg-cyber-950/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded bg-nvidia-green flex items-center justify-center font-mono font-bold text-black text-xs">
              M
            </div>
            <span className="font-bold text-sm tracking-tight text-white font-mono">
              Dynamic<span className="text-nvidia-green">MCP</span>
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyber-900 border border-cyber-800 text-[10px] font-mono text-slate-400">
              <span className="w-1.5 h-1.5 rounded-full bg-nvidia-green animate-pulse"></span>
              Ready
            </span>
          </div>

          {/* Minimal Tabs */}
          <nav className="flex items-center space-x-1">
            <button
              onClick={() => setActiveTab('playground')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-colors ${
                activeTab === 'playground'
                  ? 'bg-cyber-800 text-nvidia-green border border-cyber-700'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Assemble & Test</span>
            </button>

            <button
              onClick={() => setActiveTab('tools')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-colors ${
                activeTab === 'tools'
                  ? 'bg-cyber-800 text-nvidia-green border border-cyber-700'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Active Tools</span>
              {toolsCount > 0 && (
                <span className="px-1.5 py-0.2 rounded bg-cyber-900 text-[10px] text-slate-300 font-mono">
                  {toolsCount}
                </span>
              )}
            </button>

            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 ml-2 rounded-md hover:bg-cyber-800 text-slate-400 hover:text-slate-200 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-nvidia-green' : ''}`} />
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
}
