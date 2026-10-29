import React, { useState } from 'react';
import { Play, RefreshCw, AlertCircle, Check, Copy, Code, Terminal, Zap } from 'lucide-react';
import CodeViewer from './CodeViewer';

export default function Playground({ presets = [], onToolCreated }) {
  const [inputVal, setInputVal] = useState(presets[0]?.input || "curl -X GET 'https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true'");
  const [toolName, setToolName] = useState(presets[0]?.suggested_name || "open_meteo_forecast");
  const [offlineMode, setOfflineMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

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
    <div className="space-y-6">
      {/* Quick Preset Selector */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-mono text-slate-500 mr-1">Presets:</span>
        {presets.map((p) => (
          <button
            key={p.id}
            onClick={() => handleSelectPreset(p)}
            className="px-2.5 py-1 rounded bg-cyber-900 hover:bg-cyber-800 border border-cyber-800 hover:border-slate-700 text-xs font-mono text-slate-300 transition-colors"
          >
            {p.title}
          </button>
        ))}
      </div>

      {/* Assembly Input Box */}
      <div className="rounded-xl border border-cyber-800 bg-cyber-900/60 p-4 space-y-3">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-nvidia-green" />
            <span>Target API Contract</span>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={offlineMode}
                onChange={(e) => setOfflineMode(e.target.checked)}
                className="rounded bg-cyber-950 border-cyber-700 text-nvidia-green focus:ring-0 w-3 h-3"
              />
              <span>Offline / Mock</span>
            </label>
            <div className="flex items-center gap-1.5">
              <span>Name:</span>
              <input
                type="text"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                placeholder="tool_name"
                className="px-2 py-0.5 rounded bg-cyber-950 border border-cyber-800 text-slate-200 text-xs font-mono w-40 focus:outline-none focus:border-nvidia-green"
              />
            </div>
          </div>
        </div>

        <textarea
          rows={3}
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Paste raw curl command, remote OpenAPI spec URL, or CLI syntax..."
          className="w-full px-3 py-2 rounded-lg bg-cyber-950 border border-cyber-800 text-slate-200 font-mono text-xs focus:outline-none focus:border-nvidia-green"
        />

        <div className="flex justify-end">
          <button
            onClick={handleAssemble}
            disabled={loading || !inputVal.trim()}
            className="px-4 py-1.5 rounded-lg bg-nvidia-green hover:bg-nvidia-hover text-black font-semibold font-mono text-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Assembling FastMCP Server...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-black" />
                <span>Assemble Tool</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3 rounded-lg bg-red-950/30 border border-red-500/40 text-red-300 text-xs font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Result Section: Code & Interactive Execution */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Left Column: FastMCP Generated Code */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1.5 font-semibold text-slate-200">
                <Code className="w-3.5 h-3.5 text-nvidia-green" />
                <span>Synthesized FastMCP Code</span>
              </span>
              <span className="text-[11px] text-nvidia-green">{result.duration_ms}ms</span>
            </div>
            <CodeViewer
              code={result.generated_code}
              language="python"
              filename={`${result.tool_name}.py`}
            />
          </div>

          {/* Right Column: Execution Console */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1.5 font-semibold text-slate-200">
                <Zap className="w-3.5 h-3.5 text-nvidia-green" />
                <span>Test Execution ({result.registered_tools?.[0]})</span>
              </span>
            </div>

            <div className="rounded-lg border border-cyber-800 bg-cyber-900/60 p-3 space-y-2">
              <label className="text-[11px] font-mono text-slate-400">Arguments (JSON):</label>
              <textarea
                rows={3}
                value={execArgs}
                onChange={(e) => setExecArgs(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded bg-cyber-950 border border-cyber-800 text-slate-200 font-mono text-xs focus:outline-none focus:border-nvidia-green"
              />
              <div className="flex justify-end">
                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="px-3 py-1 rounded bg-nvidia-green hover:bg-nvidia-hover text-black font-semibold font-mono text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {executing ? (
                    <>
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      <span>Running...</span>
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
              <div className="p-3 rounded-lg bg-red-950/30 border border-red-500/40 text-red-300 text-xs font-mono">
                {execError}
              </div>
            )}

            {execResult && (
              <div className="space-y-1.5">
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
        </div>
      )}
    </div>
  );
}
