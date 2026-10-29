import React, { useState } from 'react';
import { Play, Trash2, RefreshCw, Check, Code, Globe, AlertCircle } from 'lucide-react';
import CodeViewer from './CodeViewer';

export default function ToolsList({ tools = [], onRefresh, loading }) {
  const [selectedTool, setSelectedTool] = useState(null);
  const [execArgs, setExecArgs] = useState('{}');
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [execError, setExecError] = useState(null);

  const handleSelectTool = (tool) => {
    setSelectedTool(tool);
    setExecResult(null);
    setExecError(null);

    // Auto-generate sample arguments from tool endpoints if available
    let args = {};
    if (tool.spec?.endpoints?.[0]?.parameters) {
      tool.spec.endpoints[0].parameters.forEach((p) => {
        if (p.default !== null && p.default !== undefined) {
          args[p.name] = p.default;
        } else if (p.required) {
          args[p.name] = p.type === 'integer' ? 1 : p.type === 'boolean' ? true : 'value';
        }
      });
    }
    setExecArgs(JSON.stringify(args, null, 2));
  };

  const handleDelete = async (toolId, toolName) => {
    if (!window.confirm(`Delete tool '${toolName}'?`)) return;
    try {
      await fetch(`/api/tools/${toolId}`, { method: 'DELETE' });
      if (selectedTool?.id === toolId) setSelectedTool(null);
      onRefresh();
    } catch (e) {
      alert(`Failed to delete: ${e.message}`);
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

      const target = selectedTool.registered_mcp_names?.[0] || selectedTool.name;
      const res = await fetch(`/api/tools/${target}/execute`, {
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

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Tools List (1 col) */}
        <div className="lg:col-span-1 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 pb-2 border-b border-cyber-800">
            <span>Installed Tools ({tools.length})</span>
            <button
              onClick={onRefresh}
              className="text-slate-400 hover:text-white"
              title="Refresh"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin text-nvidia-green' : ''}`} />
            </button>
          </div>

          <div className="space-y-1.5 max-h-[600px] overflow-y-auto">
            {tools.map((t) => (
              <div
                key={t.id}
                onClick={() => handleSelectTool(t)}
                className={`p-3 rounded-lg border text-xs font-mono cursor-pointer transition-colors flex items-center justify-between ${
                  selectedTool?.id === t.id
                    ? 'border-nvidia-green/60 bg-cyber-800 text-white'
                    : 'border-cyber-800 bg-cyber-900/60 text-slate-300 hover:bg-cyber-850'
                }`}
              >
                <div className="truncate mr-2">
                  <div className="font-semibold truncate">{t.name}</div>
                  <div className="text-[10px] text-slate-500 truncate flex items-center gap-1 mt-0.5">
                    <Globe className="w-2.5 h-2.5 shrink-0" />
                    <span>{t.target_domain || 'api.local'}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(t.id, t.name);
                    }}
                    className="p-1 rounded hover:bg-red-950/40 text-slate-500 hover:text-red-400"
                    title="Delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}

            {tools.length === 0 && (
              <div className="p-8 text-center text-xs font-mono text-slate-500 border border-cyber-800 rounded-lg">
                No tools assembled yet.
              </div>
            )}
          </div>
        </div>

        {/* Right: Active Tool Runner & Output (2 cols) */}
        <div className="lg:col-span-2">
          {selectedTool ? (
            <div className="rounded-xl border border-cyber-800 bg-cyber-900/60 p-4 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-cyber-800">
                <div>
                  <h3 className="text-sm font-bold font-mono text-white">{selectedTool.name}</h3>
                  <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                    Target: <span className="text-nvidia-green">{selectedTool.registered_mcp_names?.join(', ')}</span>
                  </div>
                </div>
              </div>

              {/* Execution Form */}
              <div className="space-y-2">
                <label className="text-[11px] font-mono text-slate-400">Arguments (JSON):</label>
                <textarea
                  rows={3}
                  value={execArgs}
                  onChange={(e) => setExecArgs(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-cyber-950 border border-cyber-800 text-slate-200 font-mono text-xs focus:outline-none focus:border-nvidia-green"
                />

                <div className="flex justify-end">
                  <button
                    onClick={handleExecute}
                    disabled={executing}
                    className="px-4 py-1.5 rounded-lg bg-nvidia-green hover:bg-nvidia-hover text-black font-semibold font-mono text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    {executing ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Running...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-black" />
                        <span>Run Tool</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {execError && (
                <div className="p-3 rounded-lg bg-red-950/30 border border-red-500/40 text-red-300 text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                  <span>{execError}</span>
                </div>
              )}

              {execResult && (
                <div className="space-y-1.5 pt-2 border-t border-cyber-800">
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span className="text-emerald-400 font-semibold flex items-center gap-1">
                      <Check className="w-3 h-3" /> Output:
                    </span>
                    <span>⚡ {execResult.duration_ms}ms</span>
                  </div>
                  <CodeViewer
                    code={JSON.stringify(execResult.result, null, 2)}
                    language="json"
                    filename="output.json"
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center border border-cyber-800 rounded-xl bg-cyber-900/30 text-xs font-mono text-slate-500">
              Select a tool on the left to test and run it.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
