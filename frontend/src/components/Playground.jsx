import React, { useState } from 'react';
import { Play, Sparkles, AlertCircle, CheckCircle2, Shield, Code2, FileCode, Check, RefreshCw, Terminal, ArrowRight, Server, Globe, Cpu } from 'lucide-react';
import CodeViewer from './CodeViewer';

export default function Playground({ presets = [], onToolCreated }) {
  const [inputVal, setInputVal] = useState(presets[0]?.input || "curl -X GET 'https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true'");
  const [toolName, setToolName] = useState(presets[0]?.suggested_name || "open_meteo_forecast");
  const [offlineMode, setOfflineMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('code'); // 'code' | 'spec' | 'policy' | 'execute'

  // Execution tester state
  const [execArgs, setExecArgs] = useState(JSON.stringify(presets[0]?.sample_args || {}, null, 2));
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [execError, setExecError] = useState(null);

  const handleSelectPreset = (preset) => {
    setInputVal(preset.input);
    setToolName(preset.suggested_name);
    setExecArgs(JSON.stringify(preset.sample_args, null, 2));
    setError(null);
    setResult(null);
    setExecResult(null);
    setExecError(null);
  };

  const handleAssemble = async () => {
    if (!inputVal.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setExecResult(null);
    setExecError(null);

    try {
      const res = await fetch('/api/pipeline/assemble', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: inputVal.trim(),
          name: toolName.trim() || null,
          offline: offlineMode,
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error_message || 'Assembly failed');
      }

      setResult(data);
      if (onToolCreated) onToolCreated();
    } catch (err) {
      setError(err.message || 'An error occurred during tool synthesis.');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!result || !result.registered_tools?.length) return;
    setExecuting(true);
    setExecResult(null);
    setExecError(null);

    try {
      let parsedArgs = {};
      if (execArgs.trim()) {
        parsedArgs = JSON.parse(execArgs);
      }

      const toolToRun = result.registered_tools[0];
      const res = await fetch(`/api/tools/${toolToRun}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arguments: parsedArgs }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Execution failed');
      }

      setExecResult(data);
    } catch (err) {
      setExecError(err.message || 'Execution error');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Title & Subheader */}
      <div className="border-b border-cyber-800 pb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <span>DynamicMCP Assembly Studio</span>
              <span className="px-2.5 py-0.5 text-xs font-mono font-semibold uppercase bg-nvidia-green/10 text-nvidia-green border border-nvidia-green/30 rounded-full">
                Zero-Code FastMCP Factory
              </span>
            </h1>
            <p className="mt-1.5 text-slate-400 text-sm max-w-3xl">
              Feed an unfamiliar cURL command, OpenAPI URL, or CLI help text. DynamicMCP parses the contract via <strong className="text-slate-200">Nemotron Nano</strong>, synthesizes typed Pydantic server code using <strong className="text-slate-200">Nemotron 3 Ultra</strong>, dry-runs unit tests in isolated jobs, generates <strong className="text-slate-200">NemoClaw</strong> container policies, and hot-registers the tool live.
            </p>
          </div>

          <div className="flex items-center gap-3 self-start md:self-auto">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-mono px-3 py-1.5 rounded-lg bg-cyber-900 border border-cyber-800 text-slate-300 hover:border-slate-700">
              <input
                type="checkbox"
                checked={offlineMode}
                onChange={(e) => setOfflineMode(e.target.checked)}
                className="rounded bg-cyber-800 border-cyber-700 text-nvidia-green focus:ring-nvidia-green focus:ring-offset-0"
              />
              <span>Offline / Mock Mode</span>
            </label>
          </div>
        </div>
      </div>

      {/* Preset Quick-Picks */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-nvidia-green" />
            <span>Curated Live Test Scenarios</span>
          </span>
          <span className="text-[11px] text-slate-500 font-mono">1-Click Playground Presets</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handleSelectPreset(preset)}
              className="text-left p-3 rounded-xl bg-cyber-900/90 hover:bg-cyber-850 border border-cyber-800 hover:border-nvidia-green/40 transition-all group shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-cyber-800 text-slate-300 font-medium">
                    {preset.category}
                  </span>
                </div>
                <h3 className="font-semibold text-xs text-slate-200 group-hover:text-nvidia-green transition-colors line-clamp-1">
                  {preset.title}
                </h3>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                  {preset.description}
                </p>
              </div>
              <div className="mt-2 pt-2 border-t border-cyber-800/60 flex items-center text-[10px] text-nvidia-green font-mono">
                <span>Load Scenario</span>
                <ArrowRight className="w-3 h-3 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Assembly Input Card */}
      <div className="rounded-2xl border border-cyber-800 bg-cyber-900/60 p-5 sm:p-6 shadow-2xl backdrop-blur-sm">
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold flex items-center gap-2">
              <Terminal className="w-4 h-4 text-nvidia-green" />
              <span>Input Contract (cURL / OpenAPI / CLI Help / URL)</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">Tool Name:</span>
              <input
                type="text"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                placeholder="auto_generated_name"
                className="px-2.5 py-1 text-xs font-mono rounded bg-cyber-950 border border-cyber-800 text-slate-200 focus:outline-none focus:border-nvidia-green w-48"
              />
            </div>
          </div>

          <div className="relative">
            <textarea
              rows={4}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="Paste raw curl command, remote OpenAPI spec URL (e.g. https://.../openapi.json), or CLI help text..."
              className="w-full px-4 py-3 rounded-xl bg-cyber-950 border border-cyber-800 text-slate-200 font-mono text-xs focus:outline-none focus:border-nvidia-green/60 focus:ring-1 focus:ring-nvidia-green/40 shadow-inner resize-y leading-relaxed"
            />
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Nebius Token Factory Pipeline Ready</span>
            </div>

            <button
              onClick={handleAssemble}
              disabled={loading || !inputVal.trim()}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-nvidia-green to-emerald-600 hover:from-nvidia-hover hover:to-emerald-500 text-black font-semibold text-xs tracking-wide uppercase font-mono shadow-lg shadow-nvidia-green/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-black" />
                  <span>Synthesizing & Sandboxing...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-black" />
                  <span>Assemble FastMCP Server</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Assembly Progress Visualizer during loading */}
      {loading && (
        <div className="rounded-xl border border-nvidia-green/30 bg-cyber-900/90 p-5 shadow-xl animate-pulse-subtle">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-nvidia-green animate-spin" />
              <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">Dynamic Skill Life-Cycle in Progress</span>
            </div>
            <span className="text-[11px] font-mono text-nvidia-green">Running Autonomous Stages...</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2 text-[11px] font-mono">
            <div className="p-2.5 rounded-lg bg-cyber-950 border border-nvidia-green/40 text-slate-200 flex flex-col gap-1">
              <span className="text-nvidia-green font-bold">1. Ingest</span>
              <span className="text-[10px] text-slate-400">cURL / OpenAPI</span>
            </div>
            <div className="p-2.5 rounded-lg bg-cyber-950 border border-nvidia-green/40 text-slate-200 flex flex-col gap-1">
              <span className="text-nvidia-green font-bold">2. Nemotron Nano</span>
              <span className="text-[10px] text-slate-400">Spec Extraction</span>
            </div>
            <div className="p-2.5 rounded-lg bg-cyber-950 border border-nvidia-green/40 text-slate-200 flex flex-col gap-1">
              <span className="text-nvidia-green font-bold">3. Nemotron 3 Ultra</span>
              <span className="text-[10px] text-slate-400">Code Synthesis</span>
            </div>
            <div className="p-2.5 rounded-lg bg-cyber-950 border border-nvidia-green/40 text-slate-200 flex flex-col gap-1">
              <span className="text-nvidia-green font-bold">4. Nebius Jobs</span>
              <span className="text-[10px] text-slate-400">Headless Tests</span>
            </div>
            <div className="p-2.5 rounded-lg bg-cyber-950 border border-nvidia-green/40 text-slate-200 flex flex-col gap-1">
              <span className="text-nvidia-green font-bold">5. NemoClaw</span>
              <span className="text-[10px] text-slate-400">Policy Gen</span>
            </div>
            <div className="p-2.5 rounded-lg bg-cyber-950 border border-nvidia-green/40 text-slate-200 flex flex-col gap-1">
              <span className="text-nvidia-green font-bold">6. OpenShell</span>
              <span className="text-[10px] text-slate-400">Hot-Registration</span>
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="rounded-xl border border-red-500/40 bg-red-950/20 p-4 text-red-300 text-xs font-mono flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="font-bold text-red-200">Assembly Pipeline Failure:</strong>
            <p className="leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Assembly Results Showcase */}
      {result && (
        <div className="rounded-2xl border border-nvidia-green/40 bg-cyber-900/80 p-5 sm:p-6 shadow-2xl space-y-6 glow-nvidia">
          {/* Header Summary */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-cyber-800">
            <div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-nvidia-green" />
                <h2 className="text-lg font-bold text-white font-mono">Tool Assembled & Hot-Registered</h2>
                <span className="px-2 py-0.5 rounded bg-nvidia-green/10 text-nvidia-green border border-nvidia-green/30 text-xs font-mono font-semibold">
                  {result.state}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-1">
                Tool ID: <span className="text-slate-200">{result.tool_id}</span> • Pipeline Duration: <span className="text-nvidia-green font-semibold">{result.duration_ms}ms</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400">MCP Export:</span>
              <span className="px-2.5 py-1 rounded bg-cyber-950 border border-cyber-700 text-slate-200 font-mono text-xs font-semibold">
                {result.registered_tools?.join(', ')}
              </span>
            </div>
          </div>

          {/* Sub-Tabs: Code | NemoClaw Policy | ToolSpec | Live Execution Drawer */}
          <div>
            <div className="flex items-center space-x-2 border-b border-cyber-800 mb-4">
              <button
                onClick={() => setActiveTab('code')}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-mono font-semibold border-b-2 transition-all ${
                  activeTab === 'code'
                    ? 'border-nvidia-green text-nvidia-green'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>FastMCP Python Code</span>
              </button>

              <button
                onClick={() => setActiveTab('policy')}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-mono font-semibold border-b-2 transition-all ${
                  activeTab === 'policy'
                    ? 'border-nvidia-green text-nvidia-green'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Shield className="w-3.5 h-3.5" />
                <span>NemoClaw Security Policy</span>
              </button>

              <button
                onClick={() => setActiveTab('spec')}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-mono font-semibold border-b-2 transition-all ${
                  activeTab === 'spec'
                    ? 'border-nvidia-green text-nvidia-green'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>ToolSpec Schema</span>
              </button>

              <button
                onClick={() => setActiveTab('execute')}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-mono font-semibold border-b-2 transition-all ${
                  activeTab === 'execute'
                    ? 'border-nvidia-green text-nvidia-green'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Play className="w-3.5 h-3.5" />
                <span>Live Test & Execute</span>
              </button>
            </div>

            {/* Tab 1: Python Code */}
            {activeTab === 'code' && (
              <CodeViewer
                code={result.generated_code}
                language="python"
                filename={`${result.tool_name}.py`}
              />
            )}

            {/* Tab 2: Policy YAML */}
            {activeTab === 'policy' && (
              <CodeViewer
                code={result.policy_yaml}
                language="yaml"
                filename={`${result.tool_name}.yaml`}
              />
            )}

            {/* Tab 3: ToolSpec */}
            {activeTab === 'spec' && (
              <CodeViewer
                code={JSON.stringify(result.tool_spec, null, 2)}
                language="json"
                filename={`${result.tool_name}_spec.json`}
              />
            )}

            {/* Tab 4: Direct Execution Console */}
            {activeTab === 'execute' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-cyber-950 border border-cyber-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
                      Tool Arguments (JSON Payload)
                    </label>
                    <span className="text-[11px] text-slate-500 font-mono">Invoking: {result.registered_tools?.[0]}</span>
                  </div>

                  <textarea
                    rows={4}
                    value={execArgs}
                    onChange={(e) => setExecArgs(e.target.value)}
                    placeholder='{"param": "value"}'
                    className="w-full px-3 py-2 rounded-lg bg-cyber-900 border border-cyber-800 text-slate-200 font-mono text-xs focus:outline-none focus:border-nvidia-green"
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
                          <span>Invoking inside OpenShell...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-black" />
                          <span>Run Tool Live</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {execError && (
                  <div className="p-3 rounded-lg bg-red-950/30 border border-red-500/40 text-red-300 text-xs font-mono">
                    <strong>Execution Error:</strong> {execError}
                  </div>
                )}

                {execResult && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                      <span className="flex items-center gap-1.5 text-nvidia-green font-semibold">
                        <Check className="w-4 h-4" /> Response Received
                      </span>
                      <span>Execution Latency: <strong className="text-slate-200">{execResult.duration_ms}ms</strong></span>
                    </div>
                    <CodeViewer
                      code={JSON.stringify(execResult.result, null, 2)}
                      language="json"
                      filename="execution_response.json"
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
