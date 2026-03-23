import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { formatDistanceToNow } from 'date-fns';
import { AlertTriangle, Activity, CheckCircle2, AlertCircle, Clock, ChevronRight } from 'lucide-react';
import { cn } from '../lib/utils';

// Hardcode API base URL for local dev
const API_URL = 'http://localhost:8000';

interface Incident {
  id: string;
  severity: string;
  affected_service: string;
  status: string;
  confidence: number | null;
  causal_commit: string | null;
  created_at: string;
}

export default function IncidentFeed() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchIncidents() {
      try {
        const response = await axios.get(`${API_URL}/api/incidents`);
        setIncidents(response.data.items || []);
      } catch (err) {
        setError('Failed to fetch incident feed stream. Ensure the backend is running.');
      } finally {
        setLoading(false);
      }
    }
    
    fetchIncidents();
    // Poll every 5s for the cinematic live dashboard feel
    const interval = setInterval(fetchIncidents, 5000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (severity: string) => {
    if (severity.includes('SEV1')) return 'text-cyber-red bg-cyber-red/10 border-cyber-red/20';
    if (severity.includes('SEV2')) return 'text-cyber-yellow bg-cyber-yellow/10 border-cyber-yellow/20';
    return 'text-slate-400 bg-slate-800/50 border-slate-700/50';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OPEN': return <AlertCircle className="w-4 h-4 text-cyber-red animate-pulse" />;
      case 'ACKNOWLEDGED': return <Activity className="w-4 h-4 text-cyber-cyan animate-pulse" />;
      case 'RESOLVED': return <CheckCircle2 className="w-4 h-4 text-cyber-green" />;
      default: return <Clock className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
      
      <header className="px-8 py-6 border-b border-slate-800/60 bg-slate-900/30 sticky top-0 backdrop-blur z-20 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 tracking-tight">
              Live Incident Feed
            </h1>
            <p className="text-sm font-mono text-slate-500 mt-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyber-green animate-pulse"></span>
              Real-time Threat Monitoring Matrix
            </p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-8 pt-0">
        <div className="mt-8">
          {error ? (
        <div className="glass-panel p-6 rounded-xl flex items-start gap-4 border-cyber-red/30 bg-red-950/20">
          <AlertTriangle className="w-6 h-6 text-cyber-red shrink-0" />
          <div>
            <h3 className="text-lg font-medium text-red-200">System Offline</h3>
            <p className="text-red-300/80 text-sm mt-1">{error}</p>
          </div>
        </div>
      ) : loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-cyber-cyan border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : incidents.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl flex flex-col items-center justify-center text-slate-500 border-dashed">
          <CheckCircle2 className="w-12 h-12 mb-4 text-cyber-green/50" />
          <h3 className="text-lg font-medium text-slate-300">All Systems Nominal</h3>
          <p className="text-sm mt-2">No active incidents detected in the production matrix.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {incidents.map((incident) => (
            <div 
              key={incident.id} 
              onClick={() => navigate(`/incidents/${incident.id}`)}
              className="group glass-panel rounded-xl p-5 hover:bg-slate-800/80 transition-all duration-300 cursor-pointer flex items-center gap-6 relative overflow-hidden"
            >
              {/* Highlight bar for SEV1 */}
              {incident.severity.includes('SEV1') && incident.status !== 'RESOLVED' && (
                 <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyber-red neon-border-red"></div>
              )}

              {/* Severity Badge */}
              <div className={cn(
                "px-3 py-1.5 rounded-md border font-mono text-xs font-bold shrink-0 tracking-wider",
                getSeverityColor(incident.severity)
              )}>
                {incident.severity.replace('_CRITICAL', '').replace('_HIGH', '').replace('_LOW', '')}
              </div>

              {/* Core Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="text-lg font-medium text-white truncate group-hover:text-cyber-cyan transition-colors">
                    {incident.affected_service}
                  </h3>
                  <div className="flex items-center gap-1.5 bg-slate-900/50 px-2 py-0.5 rounded text-xs font-mono text-slate-400">
                    {getStatusIcon(incident.status)}
                    <span className="uppercase tracking-wide">{incident.status}</span>
                  </div>
                </div>
                
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  <span className="flex items-center gap-1 font-mono">
                    <Clock className="w-3.5 h-3.5" /> 
                    {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}
                  </span>
                  
                  {incident.confidence !== null && (
                    <span className="flex items-center gap-1">
                      <span className="w-1 h-1 rounded-full bg-slate-600"></span>
                      AI Confidence: <span className="text-cyber-cyan ml-1 font-mono">{Math.round(incident.confidence * 100)}%</span>
                    </span>
                  )}
                  {incident.causal_commit && (
                    <span className="flex items-center gap-1">
                      <span className="w-1 h-1 rounded-full bg-slate-600"></span>
                      Commit: <span className="font-mono text-slate-300">`{incident.causal_commit.substring(0, 7)}`</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Arrow */}
              <div className="shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-slate-800/50 group-hover:bg-cyber-cyan/20 group-hover:text-cyber-cyan transition-colors">
                <ChevronRight className="w-5 h-5" />
              </div>
            </div>
          ))}
        </div>
          )}
        </div>
      </div>
    </div>
  );
}
