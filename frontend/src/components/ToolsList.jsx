import React, { useState } from 'react';
import { Play, Trash2, RefreshCw, Check, AlertCircle } from 'lucide-react';
import CodeViewer from './CodeViewer';

export default function ToolsList({ tools = [], onRefresh, loading }) {
  const [selectedTool, setSelectedTool] = useState(tools[0] || null);
  const [execArgs, setExecArgs] = useState('{}');
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [execError, setExecError] = useState(null);

  const handleSelectTool = (tool) => {
    setSelectedTool(tool);
    setExecResult(null);
    setExecError(null);

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
        {/* Left Column: Installed Tools List */}
        <div className="lg:col-span-1 space-y-2">
          <div className="flex items-center justify-between text-xs pb-2 border-b border-base-800">
            <span className="font-mono text-base-400 font-medium text-[11px] uppercase tracking-wider">
              Installed Tools ({tools.length})
            </span>
            <button
              onClick={onRefresh}
              className="text-base-400 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin text-white' : ''}`} />
            </button>
          </div>

          <div className="space-y-1 max-h-[600px] overflow-y-auto">
            {tools.map((t) => (
              <div
                key={t.id}
                onClick={() => handleSelectTool(t)}
                className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-colors flex items-center justify-between ${
                  selectedTool?.id === t.id
                    ? 'border-base-600 bg-base-800 text-white font-medium'
                    : 'border-base-850 bg-base-950 text-base-300 hover:bg-base-900 hover:border-base-800'
                }`}
              >
                <div className="truncate mr-2">
                  <div className="font-mono text-xs truncate">{t.name}</div>
                  <div className="text-[10px] text-base-500 font-mono truncate">
                    {t.target_domain || 'api.local'}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(t.id, t.name);
                    }}
                    className="p-1 rounded hover:bg-base-700 text-base-500 hover:text-red-400"
                    title="Delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}

            {tools.length === 0 && (
              <div className="p-6 text-center text-xs font-mono text-base-500 border border-base-800 rounded-lg">
                No tools installed.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Active Tool Execution Pane */}
        <div className="lg:col-span-2">
          {selectedTool ? (
            <div className="rounded-xl border border-base-800 bg-base-950 p-4 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-base-850">
                <div>
                  <h3 className="text-sm font-semibold font-mono text-white">{selectedTool.name}</h3>
                  <div className="text-[11px] font-mono text-base-500 mt-0.5">
                    Function: <span className="text-base-300">{selectedTool.registered_mcp_names?.join(', ')}</span>
                  </div>
                </div>
              </div>

              {/* Execution Form */}
              <div className="space-y-2">
                <label className="text-[11px] font-mono text-base-400">Arguments (JSON):</label>
                <textarea
                  rows={3}
                  value={execArgs}
                  onChange={(e) => setExecArgs(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-base-900 border border-base-800 text-base-200 font-mono text-xs focus:outline-none focus:border-base-600"
                />

                <div className="flex justify-end">
                  <button
                    onClick={handleExecute}
                    disabled={executing}
                    className="px-4 py-1.5 rounded-md bg-white hover:bg-base-200 text-black font-medium text-xs flex items-center gap-1.5 transition-colors disabled:opacity-40"
                  >
                    {executing ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        <span>Invoking...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3 fill-black" />
                        <span>Run Tool</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {execError && (
                <div className="p-3 rounded-lg bg-red-950/20 border border-red-900/40 text-red-300 text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                  <span>{execError}</span>
                </div>
              )}

              {execResult && (
                <div className="space-y-1.5 pt-2 border-t border-base-850">
                  <div className="flex items-center justify-between text-[11px] font-mono text-base-400">
                    <span className="text-white font-medium flex items-center gap-1">
                      <Check className="w-3 h-3 text-emerald-400" /> Output:
                    </span>
                    <span className="text-brand-accent">⚡ {execResult.duration_ms}ms</span>
                  </div>
                  <CodeViewer
                    code={JSON.stringify(execResult.result, null, 2)}
                    language="json"
                    filename="response.json"
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center border border-base-800 rounded-xl bg-base-950 text-xs font-mono text-base-500">
              Select an installed tool on the left to execute.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
