import React, { useState } from 'react';
import { Layers, Play, Code, Shield, Trash2, Globe, Clock, CheckCircle, AlertTriangle, XCircle, Search, ExternalLink, RefreshCw } from 'lucide-react';
import CodeViewer from './CodeViewer';

export default function ToolsList({ tools = [], onRefresh, loading }) {
  const [filterState, setFilterState] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTool, setSelectedTool] = useState(null);
  const [toolDetails, setToolDetails] = useState(null);
  const [fetchingDetails, setFetchingDetails] = useState(false);

  // Execution drawer inside tools
  const [executing, setExecuting] = useState(false);
  const [execArgs, setExecArgs] = useState('{}');
  const [execResult, setExecResult] = useState(null);
  const [execError, setExecError] = useState(null);

  const filteredTools = tools.filter((tool) => {
    const matchesFilter = filterState === 'ALL' || tool.state === filterState;
    const matchesSearch =
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.target_domain?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.source_type?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleOpenTool = async (tool) => {
    setSelectedTool(tool);
    setFetchingDetails(true);
    setExecResult(null);
    setExecError(null);

    // Prepare default arguments from spec parameters if available
    let initialArgs = {};
    if (tool.spec?.endpoints?.[0]?.parameters) {
      tool.spec.endpoints[0].parameters.forEach((p) => {
        if (p.default !== null && p.default !== undefined) {
          initialArgs[p.name] = p.default;
        } else if (p.required) {
          initialArgs[p.name] = p.type === 'integer' ? 1 : p.type === 'boolean' ? true : 'value';
        }
      });
    }
    setExecArgs(JSON.stringify(initialArgs, null, 2));

    try {
      const res = await fetch(`/api/tools/${tool.id}`);
      const data = await res.json();
      setToolDetails(data);
    } catch (e) {
      console.error('Failed to load tool details:', e);
    } finally {
      setFetchingDetails(false);
    }
  };

  const handleDeleteTool = async (toolId, toolName) => {
    if (!window.confirm(`Are you sure you want to decommission and delete tool '${toolName}'?`)) return;
    try {
      await fetch(`/api/tools/${toolId}`, { method: 'DELETE' });
      if (selectedTool?.id === toolId) {
        setSelectedTool(null);
        setToolDetails(null);
      }
      onRefresh();
    } catch (e) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  const handleExecute = async () => {
    if (!selectedTool) return;
    setExecuting(true);
    setExecResult(null);
    setExecError(null);

    try {
      let args = {};
      if (execArgs.trim()) args = JSON.parse(execArgs);

      const toolName = selectedTool.registered_mcp_names?.[0] || selectedTool.name;
      const res = await fetch(`/api/tools/${toolName}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arguments: args }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Execution failed');
      }
      setExecResult(data);
      onRefresh();
    } catch (err) {
      setExecError(err.message || 'Execution error');
    } finally {
      setExecuting(false);
    }
  };

  const getStateBadge = (state) => {
    switch (state) {
      case 'REGISTERED':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-medium">
            <CheckCircle className="w-3 h-3" /> REGISTERED
          </span>
        );
      case 'DRIFT_DETECTED':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 text-[10px] font-mono font-medium">
            <AlertTriangle className="w-3 h-3" /> DRIFT DETECTED
          </span>
        );
      case 'QUARANTINED':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/30 text-[10px] font-mono font-medium">
            <XCircle className="w-3 h-3" /> QUARANTINED
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-300 border border-slate-500/30 text-[10px] font-mono font-medium">
            {state}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyber-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Layers className="w-6 h-6 text-nvidia-green" />
            <span>Active FastMCP Tools Registry</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Persisted skills stored in SQLite, isolated with NemoClaw and ready for Hermes Agent hot-reload.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tools or domains..."
              className="pl-8 pr-3 py-1.5 rounded-lg bg-cyber-900 border border-cyber-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-nvidia-green w-48 sm:w-60"
            />
          </div>

          <button
            onClick={onRefresh}
            className="p-2 rounded-lg bg-cyber-900 hover:bg-cyber-800 border border-cyber-800 text-slate-400 hover:text-slate-200"
            title="Refresh list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-nvidia-green' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 text-xs font-mono">
        {['ALL', 'REGISTERED', 'DRIFT_DETECTED', 'QUARANTINED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterState(st)}
            className={`px-3 py-1 rounded-lg transition-all ${
              filterState === st
                ? 'bg-cyber-800 text-nvidia-green border border-nvidia-green/40'
                : 'bg-cyber-950 text-slate-400 hover:text-slate-200 border border-cyber-800'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Tools Grid */}
      {filteredTools.length === 0 ? (
        <div className="text-center py-16 border border-cyber-800 rounded-2xl bg-cyber-900/30 p-8 space-y-3">
          <Layers className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300 font-mono">No FastMCP Tools Found</h3>
          <p className="text-xs text-slate-500 font-mono max-w-md mx-auto">
            Switch to the <strong>Assembly Studio</strong> to ingest and synthesize your first dynamic MCP server tool contract.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTools.map((tool) => (
            <div
              key={tool.id}
              className={`rounded-xl border p-4 bg-cyber-900/70 hover:bg-cyber-850 transition-all shadow-md flex flex-col justify-between cursor-pointer ${
                selectedTool?.id === tool.id ? 'border-nvidia-green/60 glow-nvidia' : 'border-cyber-800'
              }`}
              onClick={() => handleOpenTool(tool)}
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-cyber-950 text-slate-400 border border-cyber-800">
                    {tool.source_type}
                  </span>
                  {getStateBadge(tool.state)}
                </div>

                <h3 className="font-bold text-sm text-white font-mono flex items-center gap-1.5 group-hover:text-nvidia-green">
                  <span>{tool.name}</span>
                </h3>

                <p className="text-xs text-slate-400 font-mono mt-1.5 flex items-center gap-1 truncate">
                  <Globe className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  <span className="truncate">{tool.target_domain || 'api.local'}</span>
                </p>

                {tool.spec?.description && (
                  <p className="text-xs text-slate-400 mt-2 line-clamp-2">
                    {tool.spec.description}
                  </p>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-cyber-800/80 flex items-center justify-between text-xs font-mono">
                <span className="text-[10px] text-slate-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {tool.registered_at ? new Date(tool.registered_at).toLocaleTimeString() : 'Pending'}
                </span>

                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteTool(tool.id, tool.name);
                    }}
                    className="p-1 rounded hover:bg-red-950/40 text-slate-500 hover:text-red-400"
                    title="Delete tool"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <span className="text-nvidia-green text-[11px] font-semibold flex items-center gap-1">
                    <span>Inspect</span> &rarr;
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Selected Tool Detail Drawer / Modal */}
      {selectedTool && (
        <div className="rounded-2xl border border-cyber-700 bg-cyber-900/95 p-6 shadow-2xl space-y-6 mt-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-cyber-800">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-white font-mono">{selectedTool.name}</h2>
                {getStateBadge(selectedTool.state)}
              </div>
              <p className="text-xs text-slate-400 font-mono mt-1">
                Domain: <span className="text-slate-200">{selectedTool.target_domain}</span> • FastMCP Export: <span className="text-nvidia-green">{selectedTool.registered_mcp_names?.join(', ')}</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setSelectedTool(null)}
                className="px-3 py-1.5 rounded-lg bg-cyber-800 hover:bg-cyber-700 text-xs font-mono text-slate-300"
              >
                Close Drawer
              </button>
            </div>
          </div>

          {/* Interactive Test & Execute Section */}
          <div className="rounded-xl border border-cyber-800 bg-cyber-950 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                <Play className="w-3.5 h-3.5 text-nvidia-green fill-nvidia-green" />
                <span>Execute Tool Live</span>
              </span>
              <span className="text-[11px] font-mono text-slate-400">Payload arguments (JSON)</span>
            </div>

            <textarea
              rows={3}
              value={execArgs}
              onChange={(e) => setExecArgs(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-cyber-900 border border-cyber-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-nvidia-green"
              placeholder='{"param": "val"}'
            />

            <div className="flex justify-end">
              <button
                onClick={handleExecute}
                disabled={executing}
                className="px-4 py-2 rounded-lg bg-nvidia-green hover:bg-nvidia-hover text-black font-semibold text-xs font-mono flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
              >
                {executing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Executing inside Sandbox...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-black" />
                    <span>Invoke Tool</span>
                  </>
                )}
              </button>
            </div>

            {execError && (
              <div className="p-3 rounded-lg bg-red-950/30 border border-red-500/40 text-red-300 text-xs font-mono">
                <strong>Error:</strong> {execError}
              </div>
            )}

            {execResult && (
              <div className="space-y-2 mt-4">
                <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                  <span className="text-nvidia-green font-semibold">Response:</span>
                  <span>Duration: <strong className="text-slate-200">{execResult.duration_ms}ms</strong></span>
                </div>
                <CodeViewer
                  code={JSON.stringify(execResult.result, null, 2)}
                  language="json"
                  filename="tool_response.json"
                />
              </div>
            )}
          </div>

          {/* Code & Security Inspection Tabs */}
          {toolDetails && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-1.5">
                  <Code className="w-3.5 h-3.5 text-nvidia-green" />
                  <span>Synthesized FastMCP Server</span>
                </h4>
                <CodeViewer
                  code={toolDetails.generated_code}
                  language="python"
                  filename={`${selectedTool.name}.py`}
                />
              </div>

              <div>
                <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-nvidia-green" />
                  <span>NemoClaw Security Policy</span>
                </h4>
                <CodeViewer
                  code={toolDetails.policy_yaml}
                  language="yaml"
                  filename={`${selectedTool.name}.yaml`}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
