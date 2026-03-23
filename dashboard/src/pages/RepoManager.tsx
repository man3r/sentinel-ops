import { useState, useEffect } from 'react';
import axios from 'axios';
import { GitBranch, Plus, Link as LinkIcon, Lock } from 'lucide-react';

const API_URL = 'http://localhost:8000';

interface Repo {
  id: string;
  name: string;
  provider: string;
  url: string;
}

export default function RepoManager() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [token, setToken] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchRepos();
  }, []);

  async function fetchRepos() {
    try {
      const res = await axios.get(`${API_URL}/api/repositories`);
      setRepos(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/api/repositories`, {
        name,
        provider: url.includes('github') ? 'github' : 'gitlab',
        url,
        token
      });
      setName('');
      setUrl('');
      setToken('');
      fetchRepos();
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-y-auto relative z-10 p-8">
      
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <GitBranch className="w-8 h-8 text-cyber-cyan" />
          Repository Integrations
        </h1>
        <p className="text-slate-500 mt-2">Connect source code repositories for AI Root Cause Analysis</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Add Repo Form */}
        <div className="lg:col-span-1">
          <form onSubmit={handleSubmit} className="glass-panel p-6 rounded-xl flex flex-col gap-4">
            <h2 className="text-lg font-bold text-white mb-2">Register New Repo</h2>
            
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">Repository Name</label>
              <input 
                required value={name} onChange={e => setName(e.target.value)}
                placeholder="e.g. transaction-service"
                className="w-full bg-slate-950/50 border border-slate-700/50 rounded-lg p-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyber-cyan transition-colors"
               />
            </div>
            
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">URL</label>
              <input 
                required value={url} onChange={e => setUrl(e.target.value)}
                placeholder="https://github.com/org/repo"
                className="w-full bg-slate-950/50 border border-slate-700/50 rounded-lg p-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyber-cyan transition-colors"
               />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">Access Token</label>
              <input 
                type="password" required value={token} onChange={e => setToken(e.target.value)}
                placeholder="ghp_xxxxxxxxxxxx"
                className="w-full bg-slate-950/50 border border-slate-700/50 rounded-lg p-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyber-cyan transition-colors"
               />
               <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                 <Lock className="w-3 h-3"/> Stored securely in AWS Secrets Manager
               </p>
            </div>

            <button 
              disabled={submitting}
              className="mt-2 glass-button w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/30 hover:bg-cyber-cyan/20"
            >
              {submitting ? 'Connecting...' : <><Plus className="w-4 h-4"/> Connect Repository</>}
            </button>
          </form>
        </div>

        {/* Repos List */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {loading ? (
            <div className="text-slate-500">Loading repositories...</div>
          ) : repos.map(repo => (
            <div key={repo.id} className="glass-panel p-5 rounded-xl flex items-center justify-between hover:border-slate-700 transition-colors">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center">
                   <GitBranch className="w-5 h-5 text-slate-400" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-lg">{repo.name}</h3>
                  <div className="flex items-center gap-2 text-sm text-slate-500 mt-0.5">
                    <span className="px-2 py-0.5 rounded text-xs bg-slate-800 uppercase tracking-wider">{repo.provider}</span>
                    <LinkIcon className="w-3 h-3" />
                    <span>{repo.url}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                 <span className="flex items-center gap-1.5 text-xs font-medium text-cyber-green bg-cyber-green/10 px-3 py-1.5 rounded-full border border-cyber-green/20">
                    <span className="w-1.5 h-1.5 bg-cyber-green rounded-full shadow-[0_0_5px_#10b981]"></span>
                    SYNCED
                 </span>
              </div>
            </div>
          ))}
          {!loading && repos.length === 0 && (
            <div className="text-center p-12 glass-panel rounded-xl text-slate-500">
               No repositories integrated yet.
            </div>
          )}
        </div>
        
      </div>
    </div>
  );
}
