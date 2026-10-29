import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Playground from './components/Playground';
import ToolsList from './components/ToolsList';
import SecurityView from './components/SecurityView';
import AuditView from './components/AuditView';

export default function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [tools, setTools] = useState([]);
  const [presets, setPresets] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchState = async () => {
    setLoading(true);
    try {
      const [toolsRes, presetsRes, sysRes] = await Promise.all([
        fetch('/api/tools'),
        fetch('/api/presets'),
        fetch('/api/system'),
      ]);

      if (toolsRes.ok) setTools(await toolsRes.json());
      if (presetsRes.ok) setPresets(await presetsRes.json());
      if (sysRes.ok) setSystemStatus(await sysRes.json());
    } catch (err) {
      console.error('Failed to sync backend state:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchState();
  }, []);

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 flex flex-col font-sans selection:bg-nvidia-green selection:text-black">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        onRefresh={fetchState}
        loading={loading}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'playground' && (
          <Playground
            presets={presets}
            onToolCreated={fetchState}
          />
        )}

        {activeTab === 'tools' && (
          <ToolsList
            tools={tools}
            onRefresh={fetchState}
            loading={loading}
          />
        )}

        {activeTab === 'security' && (
          <SecurityView
            systemStatus={systemStatus}
            tools={tools}
          />
        )}

        {activeTab === 'audit' && (
          <AuditView
            tools={tools}
            onRefresh={fetchState}
            loading={loading}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-cyber-800/80 bg-cyber-950/60 py-6 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-nvidia-green"></span>
            <span>DynamicMCP • Personal AI Track</span>
          </div>
          <div>
            Built with NVIDIA Nemotron (Nano & Ultra) on Nebius Token Factory & Serverless Infrastructure
          </div>
          <div className="text-slate-400">
            Apache-2.0 License
          </div>
        </div>
      </footer>
    </div>
  );
}
