import { useState, useEffect } from 'react';
import axios from 'axios';
import { format } from 'date-fns';
import { ShieldCheck, Download, Lock, Copy, Check } from 'lucide-react';
import { cn } from '../lib/utils';

const API_URL = 'http://localhost:8000';

interface AuditRecord {
  id: number;
  incident_id: string | null;
  event_type: string;
  actor: string | null;
  payload: any;
  record_hash: string;
  prev_hash: string | null;
  created_at: string;
}

export default function AuditTrail() {
  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      try {
        const response = await axios.get(`${API_URL}/api/audit?limit=100`);
        setLogs(response.data.items || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchLogs();
  }, []);

  const handleExport = () => {
    window.open(`${API_URL}/api/audit?format=json`, '_blank');
  };

  const [copiedId, setCopiedId] = useState<number | null>(null);

  const copyToClipboard = async (id: number, content: any) => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(content, null, 2));
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy!', err);
    }
  };

  const getEventStyle = (type: string) => {
    if (type.includes('GUARDRAIL')) return 'text-cyber-red border-cyber-red/20 bg-cyber-red/10';
    if (type.includes('MITIGATION')) return 'text-cyber-green border-cyber-green/20 bg-cyber-green/10';
    if (type.includes('HUMAN')) return 'text-cyber-yellow border-cyber-yellow/20 bg-cyber-yellow/10';
    if (type.includes('RCA') || type.includes('REASONING')) return 'text-cyber-purple border-cyber-purple/20 bg-cyber-purple/10';
    return 'text-cyber-cyan border-cyber-cyan/20 bg-cyber-cyan/10';
  };

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
      
      <header className="px-8 py-6 border-b border-slate-800/60 bg-slate-900/30 sticky top-0 backdrop-blur z-20 shrink-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              <Lock className="w-8 h-8 text-slate-500" />
              Immutable Audit Ledger
            </h1>
            <p className="text-sm text-slate-500 mt-2">
              Cryptographically chained event history. WORM-compliant.
            </p>
          </div>
          
          <button 
            onClick={handleExport}
            className="glass-button flex items-center gap-2 px-4 py-2 rounded-lg text-sm self-start md:self-center"
          >
            <Download className="w-4 h-4" />
            Export NDJSON Bundle
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-8 pt-0">
        <div className="glass-panel rounded-xl overflow-hidden shadow-2xl border-slate-800 mt-8">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 z-10 bg-slate-900 shadow-md">
              <tr className="border-b border-slate-800">
                <th className="py-4 px-6 text-xs font-semibold text-slate-400 uppercase tracking-wider">ID</th>
                <th className="py-4 px-6 text-xs font-semibold text-slate-400 uppercase tracking-wider">Timestamp</th>
                <th className="py-4 px-6 text-xs font-semibold text-slate-400 uppercase tracking-wider">Event Type</th>
                <th className="py-4 px-6 text-xs font-semibold text-slate-400 uppercase tracking-wider">Actor</th>
                <th className="py-4 px-6 text-xs font-semibold text-slate-400 uppercase tracking-wider">Payload</th>
                <th className="py-4 px-6 text-xs font-semibold text-slate-400 uppercase tracking-wider">SHA-256 Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr><td colSpan={6} className="py-8 text-center text-slate-500">Decrypting ledger...</td></tr>
              ) : logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-4 px-6 text-sm text-slate-500 font-mono">#{log.id}</td>
                  <td className="py-4 px-6 text-sm text-slate-300 whitespace-nowrap">
                    {format(new Date(log.created_at), 'MMM dd, HH:mm:ss')}
                  </td>
                  <td className="py-4 px-6">
                    <span className={cn("px-2.5 py-1 rounded text-xs font-mono font-medium border", getEventStyle(log.event_type))}>
                      {log.event_type}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-sm text-slate-300 font-medium">
                    {log.actor || 'System'}
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2 group max-w-xs">
                      <div className="text-xs font-mono text-slate-400 bg-slate-950/50 p-2 rounded border border-slate-800 overflow-hidden text-ellipsis whitespace-nowrap flex-1">
                        {JSON.stringify(log.payload)}
                      </div>
                      <button
                        onClick={() => copyToClipboard(log.id, log.payload)}
                        className={cn(
                          "p-2 rounded border transition-all duration-200 shrink-0",
                          copiedId === log.id 
                            ? "bg-cyber-green/20 border-cyber-green text-cyber-green" 
                            : "bg-slate-900 border-slate-700 text-slate-500 hover:text-cyber-cyan hover:border-cyber-cyan"
                        )}
                        title="Copy Payload"
                      >
                        {copiedId === log.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                       <ShieldCheck className="w-3.5 h-3.5 text-cyber-green shrink-0" />
                       <span className="text-xs font-mono text-slate-500 truncate w-32" title={log.record_hash}>
                         {log.record_hash.substring(0, 16)}...
                       </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    </div>
  );
}
