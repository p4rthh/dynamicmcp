import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CodeViewer({ code, language = 'python', filename = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!code) return;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!code) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-sm border border-cyber-800 rounded-lg bg-cyber-900/50">
        No code generated yet.
      </div>
    );
  }

  return (
    <div className="relative rounded-lg overflow-hidden border border-cyber-800 bg-[#0B0E14] text-slate-200 font-mono text-xs shadow-xl">
      <div className="flex items-center justify-between px-4 py-2 bg-cyber-900/80 border-b border-cyber-800 text-slate-400">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/70"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-green-500/70"></div>
          {filename && <span className="ml-2 text-slate-300 font-medium text-xs">{filename}</span>}
        </div>
        <div className="flex items-center space-x-3">
          <span className="uppercase tracking-wider text-[10px] text-slate-500 font-semibold">{language}</span>
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-2 py-1 rounded bg-cyber-800 hover:bg-cyber-700 text-slate-300 hover:text-white transition-all text-[11px]"
            title="Copy to clipboard"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-nvidia-green" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>
      </div>
      <div className="p-4 max-h-[500px] overflow-auto">
        <pre className="leading-relaxed">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
