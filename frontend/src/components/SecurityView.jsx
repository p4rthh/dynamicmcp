import React from 'react';
import { ShieldCheck, Lock, Network, HardDrive, Key, AlertOctagon, Cpu, CheckCircle } from 'lucide-react';

export default function SecurityView({ systemStatus, tools = [] }) {
  const sandboxesCount = systemStatus?.sandbox?.active_sandboxes_count || tools.filter(t => t.state === 'REGISTERED').length;

  return (
    <div className="space-y-8">
      {/* Title */}
      <div className="border-b border-cyber-800 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <ShieldCheck className="w-6 h-6 text-nvidia-green" />
          <span>NVIDIA OpenShell & NemoClaw Security Boundaries</span>
        </h1>
        <p className="text-xs text-slate-400 font-mono mt-1">
          Zero-leakage, domain-scoped network egress, and kernel namespace isolation for autonomously synthesized tools.
        </p>
      </div>

      {/* Security Architecture Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Landlock LSM */}
        <div className="p-4 rounded-xl bg-cyber-900/80 border border-cyber-800 space-y-3">
          <div className="flex items-center gap-2 text-nvidia-green font-mono text-xs font-bold">
            <HardDrive className="w-4 h-4" />
            <span>Landlock LSM (FS)</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Read-only root filesystem. Blocked access to <code className="text-slate-300">~/.ssh/</code>, <code className="text-slate-300">.env</code>, and host credentials. Only <code className="text-slate-300">/tmp/workspace</code> is writable.
          </p>
          <div className="pt-2 border-t border-cyber-800 text-[11px] font-mono text-emerald-400 flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" /> Enforced at Kernel
          </div>
        </div>

        {/* Egress Network Namespaces */}
        <div className="p-4 rounded-xl bg-cyber-900/80 border border-cyber-800 space-y-3">
          <div className="flex items-center gap-2 text-nvidia-green font-mono text-xs font-bold">
            <Network className="w-4 h-4" />
            <span>Network Egress Scoping</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Outbound traffic strictly restricted via NemoClaw policies. All internal addresses (<code className="text-slate-300">10.0.0.0/8</code>, <code className="text-slate-300">169.254.169.254</code>) are blocked.
          </p>
          <div className="pt-2 border-t border-cyber-800 text-[11px] font-mono text-emerald-400 flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" /> Domain-Scoped Only
          </div>
        </div>

        {/* seccomp Syscall Filter */}
        <div className="p-4 rounded-xl bg-cyber-900/80 border border-cyber-800 space-y-3">
          <div className="flex items-center gap-2 text-nvidia-green font-mono text-xs font-bold">
            <Lock className="w-4 h-4" />
            <span>seccomp-bpf</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Blocks dangerous syscalls like <code className="text-slate-300">execve</code>, <code className="text-slate-300">ptrace</code>, <code className="text-slate-300">mount</code>, and user namespace cloning inside sandboxes.
          </p>
          <div className="pt-2 border-t border-cyber-800 text-[11px] font-mono text-emerald-400 flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" /> Syscall Whitelist
          </div>
        </div>

        {/* Zero-Trust Credentials */}
        <div className="p-4 rounded-xl bg-cyber-900/80 border border-cyber-800 space-y-3">
          <div className="flex items-center gap-2 text-nvidia-green font-mono text-xs font-bold">
            <Key className="w-4 h-4" />
            <span>Zero-Trust Vault</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            API keys and tokens are never exposed in generated code or environment variables. They are injected transparently at the network egress proxy.
          </p>
          <div className="pt-2 border-t border-cyber-800 text-[11px] font-mono text-emerald-400 flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" /> Zero Token Leakage
          </div>
        </div>
      </div>

      {/* Active Sandboxes Table */}
      <div className="rounded-xl border border-cyber-800 bg-cyber-900/70 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-nvidia-green" />
            <span>Active OpenShell Sandboxes ({sandboxesCount})</span>
          </h2>
          <span className="text-xs text-slate-500 font-mono">
            Policy Dir: <code className="text-slate-300">{systemStatus?.sandbox?.policy_dir || '~/.dynamicmcp/policies'}</code>
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-cyber-800 text-slate-400">
                <th className="py-2.5 px-3">Sandbox Name</th>
                <th className="py-2.5 px-3">Target Domain</th>
                <th className="py-2.5 px-3">Isolation Mode</th>
                <th className="py-2.5 px-3">FS Policy</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-800/60 text-slate-300">
              {tools.filter(t => t.state === 'REGISTERED').map((tool) => (
                <tr key={tool.id} className="hover:bg-cyber-850/50">
                  <td className="py-2.5 px-3 font-semibold text-white">sandbox-{tool.name.replace(/_/g, '-')}</td>
                  <td className="py-2.5 px-3 text-nvidia-green">{tool.target_domain || 'api.local'}</td>
                  <td className="py-2.5 px-3 text-slate-400">OpenShell / Landlock</td>
                  <td className="py-2.5 px-3 text-slate-400">RO root + /tmp/workspace</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px]">
                      ENFORCED
                    </span>
                  </td>
                </tr>
              ))}
              {tools.filter(t => t.state === 'REGISTERED').length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No active sandboxes yet. Assemble a tool in the Studio to mount an OpenShell container.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
