import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Playground from './components/Playground';
import ToolsList from './components/ToolsList';

export default function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [tools, setTools] = useState([]);
  const [presets, setPresets] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchState = async () => {
    setLoading(true);
    try {
      const [toolsRes, presetsRes] = await Promise.all([
        fetch('/api/tools'),
        fetch('/api/presets'),
      ]);

      if (toolsRes.ok) setTools(await toolsRes.json());
      if (presetsRes.ok) setPresets(await presetsRes.json());
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
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        toolsCount={tools.length}
        onRefresh={fetchState}
        loading={loading}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6">
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
      </main>
    </div>
  );
}
