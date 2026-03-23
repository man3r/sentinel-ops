import { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Plus, Shield, ShieldOff } from 'lucide-react';

const API_URL = 'http://localhost:8000';

interface Guardrail {
  id: string;
  rule_type: string;
  value: string;
  description: string;
  active: boolean;
}

export default function GuardrailConfig() {
  const [rules, setRules] = useState<Guardrail[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [type, setType] = useState('NO_GO_ZONE');
  const [val, setVal] = useState('');
  const [desc, setDesc] = useState('');
  
  // Simulated Confidence Slider state (mock for UI)
  const [confidence, setConfidence] = useState(75);

  useEffect(() => {
    fetchRules();
  }, []);

  async function fetchRules() {
    try {
      const res = await axios.get(`${API_URL}/api/guardrails`);
      setRules(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/guardrails`, {
        rule_type: type,
        value: val,
        description: desc
      });
      setVal('');
      setDesc('');
      fetchRules();
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-y-auto relative z-10 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <ShieldAlert className="w-8 h-8 text-cyber-purple" />
          Guardrails & Policies
        </h1>
        <p className="text-slate-500 mt-2">Configure automated enforcement policies prior to mitigation.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column Config */}
        <div className="lg:col-span-1 space-y-6">
          
          {/* Confidence Slider (Mock Representation) */}
          <div className="glass-panel p-6 rounded-xl">
            <h2 className="text-lg font-bold text-white mb-4">Minimum AI Confidence</h2>
            <div className="flex items-end justify-between mb-2">
              <span className="text-3xl font-light text-cyber-cyan">{confidence}%</span>
              <span className="text-sm text-slate-500 mb-1">Required Threshold</span>
            </div>
            <input 
              type="range" min="50" max="99" 
              value={confidence} 
              onChange={e => setConfidence(parseInt(e.target.value))}
              className="w-full accent-cyber-cyan mt-2"
            />
            <p className="text-xs text-slate-400 mt-3 leading-relaxed">
              Automated mitigations will be blocked if Bedrock RCA confidence drops below this value.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="glass-panel p-6 rounded-xl flex flex-col gap-4">
            <h2 className="text-lg font-bold text-white mb-2">Add New Rule</h2>
            
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">Rule Type</label>
              <select 
                value={type} onChange={e => setType(e.target.value)}
                className="w-full bg-slate-950/50 border border-slate-700/50 rounded-lg p-2.5 text-sm text-slate-200 outline-none"
              >
                <option value="NO_GO_ZONE">No-Go Zone (Service/Repo)</option>
                <option value="RATE_LIMIT">Rate Limit (Actions/Hour)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">Target Value</label>
              <input 
                required value={val} onChange={e => setVal(e.target.value)}
                placeholder="e.g. auth-service"
                className="w-full bg-slate-950/50 border border-slate-700/50 rounded-lg p-2.5 text-sm outline-none text-slate-200"
               />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">Reason / Description</label>
              <input 
                required value={desc} onChange={e => setDesc(e.target.value)}
                placeholder="e.g. Core banking service requires manual auth"
                className="w-full bg-slate-950/50 border border-slate-700/50 rounded-lg p-2.5 text-sm outline-none text-slate-200"
               />
            </div>

            <button className="mt-2 glass-button w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-cyber-purple/10 text-cyber-purple border-cyber-purple/30 hover:bg-cyber-purple/20">
              <Plus className="w-4 h-4"/> Enforce Policy
            </button>
          </form>
        </div>

        {/* Active Rules List */}
        <div className="lg:col-span-2">
          <h2 className="text-lg font-bold text-white mb-4">Active System Policies</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {loading ? (
               <div className="text-slate-500">Loading...</div>
            ) : rules.map(rule => (
              <div key={rule.id} className="glass-panel p-5 rounded-xl border-l-2 border-l-cyber-purple">
                <div className="flex items-center justify-between mb-3">
                  <div className="px-2 py-1 rounded bg-slate-800 text-xs font-mono text-slate-300">
                    {rule.rule_type}
                  </div>
                  {rule.active ? <Shield className="w-4 h-4 text-cyber-purple" /> : <ShieldOff className="w-4 h-4 text-slate-600" />}
                </div>
                <div className="font-bold text-white text-lg font-mono mb-1">{rule.value}</div>
                <div className="text-sm text-slate-400">{rule.description}</div>
              </div>
            ))}
          </div>
        </div>
        
      </div>
    </div>
  );
}
