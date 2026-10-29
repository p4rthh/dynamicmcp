import React, { useState, useEffect } from 'react';
import { Activity, Clock, CheckCircle2, XCircle, Wrench, Shield, ArrowRight, RefreshCw } from 'lucide-react';

export default function AuditView({ tools = [], onRefresh, loading }) {
  const [selectedToolId, setSelectedToolId] = useState(tools[0]?.id || null);
  const [history, setHistory] = useState(null);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (selectedToolId) {
      loadHistory(selectedToolId);
    }
  }, [selectedToolId]);

  const loadHistory = async (toolId) => {
    setFetching(true);
    try {
      const res = await fetch(`/api/tools/${toolId}`);
      const data = await res.json();
      setHistory(data);
    } catch (e) {
      console.error('Failed to load history:', e);
    } finally {
      setFetching(false);
    }
  };

  const currentTool = tools.find((t) => t.id === selectedToolId) || tools[0];

  return (
    <div className="space-y-8">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyber-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-nvidia-green" />
            <span>Dynamic Skill Lifecycle & Execution Audit Trail</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Deterministic state-transition machine logs, execution latency, and self-healing patches.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedToolId || ''}
            onChange={(e) => setSelectedToolId(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-cyber-900 border border-cyber-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-nvidia-green"
          >
            {tools.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.state})
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              onRefresh();
              if (selectedToolId) loadHistory(selectedToolId);
            }}
            className="p-2 rounded-lg bg-cyber-900 hover:bg-cyber-800 border border-cyber-800 text-slate-400 hover:text-slate-200"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading || fetching ? 'animate-spin text-nvidia-green' : ''}`} />
          </button>
        </div>
      </div>

      {/* State Machine Overview Banner */}
      <div className="p-4 rounded-xl bg-cyber-900/60 border border-cyber-800 space-y-3">
        <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
          State Machine Flow: Autonomous Lifecycle
        </h3>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono text-slate-300">
          <span className="px-2 py-0.5 rounded bg-cyber-950 border border-cyber-800">UNRECOGNIZED_TOOL</span>
          <ArrowRight className="w-3 h-3 text-slate-500" />
          <span className="px-2 py-0.5 rounded bg-cyber-950 border border-cyber-800">SPEC_PARSING</span>
          <ArrowRight className="w-3 h-3 text-slate-500" />
          <span className="px-2 py-0.5 rounded bg-cyber-950 border border-cyber-800">CODE_SYNTHESIS</span>
          <ArrowRight className="w-3 h-3 text-slate-500" />
          <span className="px-2 py-0.5 rounded bg-cyber-950 border border-cyber-800">DRY_RUN_VERIFICATION</span>
          <ArrowRight className="w-3 h-3 text-slate-500" />
          <span className="px-2 py-0.5 rounded bg-cyber-950 border border-nvidia-green/40 text-nvidia-green font-semibold">REGISTERED</span>
          <ArrowRight className="w-3 h-3 text-slate-500" />
          <span className="px-2 py-0.5 rounded bg-cyber-950 border border-cyber-800">EXECUTING</span>
        </div>
      </div>

      {/* Recent Execution Logs */}
      <div className="space-y-4">
        <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
          <Clock className="w-4 h-4 text-nvidia-green" />
          <span>Execution Telemetry ({history?.executions?.length || 0} events)</span>
        </h2>

        <div className="overflow-x-auto rounded-xl border border-cyber-800 bg-cyber-900/70">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-cyber-800 text-slate-400">
                <th className="py-2.5 px-3">Execution ID</th>
                <th className="py-2.5 px-3">Input Hash</th>
                <th className="py-2.5 px-3">Latency</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Output Summary</th>
                <th className="py-2.5 px-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-800/60 text-slate-300">
              {history?.executions?.map((ex) => (
                <tr key={ex.id} className="hover:bg-cyber-850/50">
                  <td className="py-2.5 px-3 font-semibold text-white">{ex.execution_id}</td>
                  <td className="py-2.5 px-3 text-slate-500 truncate max-w-[100px]">{ex.input_hash}</td>
                  <td className="py-2.5 px-3 text-nvidia-green font-medium">{ex.duration_ms}ms</td>
                  <td className="py-2.5 px-3">
                    {ex.success ? (
                      <span className="inline-flex items-center gap-1 text-emerald-400">
                        <CheckCircle2 className="w-3 h-3" /> SUCCESS
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-red-400">
                        <XCircle className="w-3 h-3" /> FAILED
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-slate-400 truncate max-w-[200px]">
                    {ex.output_summary || ex.error_message || 'N/A'}
                  </td>
                  <td className="py-2.5 px-3 text-slate-500">
                    {new Date(ex.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
              {(!history?.executions || history.executions.length === 0) && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No executions recorded for this tool yet. Run the tool from the Studio or Active Tools drawer.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lifecycle Transition History */}
      <div className="space-y-4">
        <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
          <Activity className="w-4 h-4 text-nvidia-green" />
          <span>State Transitions & Lifecycle Events</span>
        </h2>

        <div className="space-y-2">
          {history?.lifecycle_events?.map((ev) => (
            <div
              key={ev.id}
              className="p-3 rounded-lg bg-cyber-900/60 border border-cyber-800 flex items-center justify-between text-xs font-mono"
            >
              <div className="flex items-center gap-2">
                <span className="text-slate-400">{ev.from_state}</span>
                <ArrowRight className="w-3 h-3 text-nvidia-green" />
                <span className="text-white font-semibold">{ev.to_state}</span>
                <span className="text-slate-500 ml-2">[{ev.trigger}]</span>
              </div>
              <span className="text-slate-500 text-[11px]">
                {new Date(ev.created_at).toLocaleTimeString()}
              </span>
            </div>
          ))}
          {(!history?.lifecycle_events || history.lifecycle_events.length === 0) && (
            <div className="p-6 text-center text-slate-500 font-mono text-xs border border-cyber-800 rounded-lg">
              No lifecycle events found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
