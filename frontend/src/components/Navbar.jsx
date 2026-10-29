import React from 'react';
import { Cpu, ShieldCheck, Zap, Layers, RefreshCw, Terminal, Activity } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, systemStatus, onRefresh, loading }) {
  return (
    <header className="border-b border-cyber-800 bg-cyber-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('playground')}>
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-nvidia-green to-emerald-700 flex items-center justify-center shadow-lg shadow-nvidia-green/20">
              <Zap className="w-5 h-5 text-black fill-black" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white font-sans">Dynamic<span className="text-nvidia-green">MCP</span></span>
                <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold tracking-wide uppercase bg-nvidia-green/10 text-nvidia-green border border-nvidia-green/30 rounded">
                  Nebius x NVIDIA
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono hidden sm:block">Self-Assembling MCP Server Factory</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={() => setActiveTab('playground')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'playground'
                  ? 'bg-cyber-800 text-nvidia-green border border-nvidia-green/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-cyber-900'
              }`}
            >
              <Terminal className="w-4 h-4" />
              <span>Studio</span>
            </button>

            <button
              onClick={() => setActiveTab('tools')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'tools'
                  ? 'bg-cyber-800 text-nvidia-green border border-nvidia-green/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-cyber-900'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Active Tools</span>
              {systemStatus?.metrics?.total_tools > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full bg-nvidia-green/20 text-nvidia-green text-[10px] font-mono">
                  {systemStatus.metrics.total_tools}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'security'
                  ? 'bg-cyber-800 text-nvidia-green border border-nvidia-green/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-cyber-900'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>NemoClaw Sandbox</span>
            </button>

            <button
              onClick={() => setActiveTab('audit')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'audit'
                  ? 'bg-cyber-800 text-nvidia-green border border-nvidia-green/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-cyber-900'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Audit Trail</span>
            </button>
          </nav>

          {/* System Telemetry Badges */}
          <div className="hidden lg:flex items-center space-x-3 text-xs font-mono">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-cyber-900 border border-cyber-800">
              <span className="w-2 h-2 rounded-full bg-nvidia-green animate-pulse"></span>
              <span className="text-slate-400">Nebius:</span>
              <span className="text-slate-200 font-medium">Nemotron Nano / Ultra</span>
            </div>

            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 rounded-lg bg-cyber-900 hover:bg-cyber-800 text-slate-400 hover:text-slate-200 border border-cyber-800 transition-all disabled:opacity-50"
              title="Refresh tools and state"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-nvidia-green' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
