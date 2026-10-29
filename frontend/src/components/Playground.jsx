import React, { useState } from 'react';
import { Play, RefreshCw, AlertCircle, Check } from 'lucide-react';
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
      {/* Sleek Preset Selectors */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-mono text-base-500 mr-1">Templates:</span>
        {presets.map((p) => (
          <button
            key={p.id}
            onClick={() => handleSelectPreset(p)}
            className="px-2.5 py-1 rounded-md bg-base-850 hover:bg-base-800 border border-base-800 hover:border-base-700 text-xs text-base-300 hover:text-white transition-colors"
          >
            {p.title.replace(' Forecast', '').replace(' Real-Time', '')}
          </button>
        ))}
      </div>

      {/* Assembly Input Container */}
      <div className="rounded-xl border border-base-800 bg-base-950 p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <span className="font-mono text-base-400 font-medium text-[11px] uppercase tracking-wider">
            API Specification or Command
          </span>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-[11px] text-base-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={offlineMode}
                onChange={(e) => setOfflineMode(e.target.checked)}
                className="rounded bg-base-900 border-base-700 text-white focus:ring-0 w-3 h-3 cursor-pointer"
              />
              <span>Offline / Mock</span>
            </label>
            <div className="flex items-center gap-1.5">
              <span className="text-base-500 font-mono text-[11px]">Name:</span>
              <input
                type="text"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                placeholder="optional_name"
                className="px-2 py-0.5 rounded bg-base-900 border border-base-800 text-base-200 text-xs font-mono w-36 focus:outline-none focus:border-base-600"
              />
            </div>
          </div>
        </div>

        <textarea
          rows={3}
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="curl -X GET 'https://...' or OpenAPI spec URL..."
          className="w-full px-3 py-2.5 rounded-lg bg-base-900 border border-base-800 text-base-200 font-mono text-xs focus:outline-none focus:border-base-600 leading-relaxed"
        />

        <div className="flex items-center justify-between pt-1">
          <span className="text-[11px] font-mono text-base-500">
            Auto-synthesizes Pydantic models, sandbox policy, and FastMCP server.
          </span>
          <button
            onClick={handleAssemble}
            disabled={loading || !inputVal.trim()}
            className="px-4 py-1.5 rounded-md bg-white hover:bg-base-200 text-black font-medium text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {loading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Assembling...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-black" />
                <span>Assemble Tool</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Card */}
      {error && (
        <div className="p-3.5 rounded-lg bg-red-950/20 border border-red-900/50 text-red-300 text-xs font-mono flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Assembly Output & Live Test Split */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-1">
          {/* FastMCP Python Script */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-base-400">
              <span className="font-medium text-white font-mono text-[11px] uppercase tracking-wider">
                FastMCP Server Code
              </span>
              <span className="text-[11px] font-mono text-base-500">{result.duration_ms}ms</span>
            </div>
            <CodeViewer
              code={result.generated_code}
              language="python"
              filename={`${result.tool_name}.py`}
            />
          </div>

          {/* Test Execution Console */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-base-400">
              <span className="font-medium text-white font-mono text-[11px] uppercase tracking-wider">
                Interactive Test Console
              </span>
              <span className="text-[11px] font-mono text-base-400">{result.registered_tools?.[0]}</span>
            </div>

            <div className="rounded-xl border border-base-800 bg-base-950 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-mono text-base-400">Arguments (JSON):</label>
              </div>
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
                  className="px-3.5 py-1.5 rounded-md bg-base-800 hover:bg-base-700 text-white font-medium text-xs flex items-center gap-1.5 transition-colors border border-base-700 disabled:opacity-40"
                >
                  {executing ? (
                    <>
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      <span>Invoking...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 fill-white" />
                      <span>Run Tool</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {execError && (
              <div className="p-3 rounded-lg bg-red-950/20 border border-red-900/40 text-red-300 text-xs font-mono">
                {execError}
              </div>
            )}

            {execResult && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[11px] font-mono text-base-400">
                  <span className="text-white font-medium flex items-center gap-1">
                    <Check className="w-3 h-3 text-emerald-400" /> Output Payload
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
        </div>
      )}
    </div>
  );
}
