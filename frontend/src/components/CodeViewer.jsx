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
      <div className="p-6 text-center text-base-500 font-mono text-xs border border-base-800 rounded-lg bg-base-950">
        No output generated.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-base-800 bg-base-950 text-base-200 font-mono text-xs overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-base-900 border-b border-base-800/80">
        <span className="text-base-400 font-medium text-[11px] truncate">{filename || language}</span>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-base-500 uppercase tracking-wider">{language}</span>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 rounded border border-base-800 hover:border-base-700 bg-base-850 hover:bg-base-800 text-base-300 hover:text-white transition-colors text-[11px]"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>
      <div className="p-3.5 max-h-[460px] overflow-auto">
        <pre className="leading-relaxed">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
