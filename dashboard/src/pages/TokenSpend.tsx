import { useState, useEffect } from 'react';
import axios from 'axios';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from 'recharts';
import { BarChart3, TrendingUp, Cpu, Coins } from 'lucide-react';

const API_URL = 'http://localhost:8000';

interface TokenData {
  date: string;
  tokens: number;
}

export default function TokenSpend() {
  const [data, setData] = useState<TokenData[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await axios.get(`${API_URL}/api/incidents/spend/tokens`);
        const payload: any[] = res.data || [];
        
        let sum = 0;
        const chartData = payload.map(i => {
          sum += (i.tokens || 0);
          return {
            date: new Date(i.timestamp).toLocaleDateString(),
            tokens: i.tokens
          };
        });
          
        setTotal(sum);
        // If DB has 0 actual incidents with >0 tokens (mock dev mode), still show empty state correctly:
        setData(chartData);
        
      } catch (e) {
        console.error(e);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="flex-1 flex flex-col overflow-y-auto relative z-10 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <BarChart3 className="w-8 h-8 text-cyber-yellow" />
          GenAI Token Economics
        </h1>
        <p className="text-slate-500 mt-2">Monitor Bedrock RCA inference cost and token consumption patterns.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="glass-panel p-6 rounded-xl flex items-center justify-between col-span-1 md:col-span-2 relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyber-yellow shadow-[0_0_10px_#f59e0b]"></div>
          <div>
            <div className="text-sm font-mono text-slate-400 mb-1 flex items-center gap-2">
              <Coins className="w-4 h-4"/> 30-Day Bedrock Spend
            </div>
            <div className="text-4xl font-light text-white">${(total * 0.003 / 1000).toFixed(4)}</div>
            <div className="text-xs text-cyber-yellow mt-2">+12% vs last month</div>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-xl">
          <div className="text-sm font-mono text-slate-400 mb-1 flex items-center gap-2"><Cpu className="w-4 h-4"/> Total Tokens</div>
          <div className="text-2xl font-light text-white">{total.toLocaleString()}</div>
        </div>

        <div className="glass-panel p-6 rounded-xl">
          <div className="text-sm font-mono text-slate-400 mb-1 flex items-center gap-2"><TrendingUp className="w-4 h-4"/> Avg per RCA</div>
          <div className="text-2xl font-light text-white">{data.length ? Math.round(total / data.length).toLocaleString() : 0}</div>
        </div>
      </div>

      <div className="glass-panel p-6 rounded-xl border border-slate-800 flex-1 min-h-[400px]">
        <h3 className="text-lg font-bold text-white mb-6 font-mono">Inference Volume Over Time</h3>
        <ResponsiveContainer width="100%" height="85%">
          <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="date" stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} dy={10} />
            <YAxis stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} dx={-10} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
              itemStyle={{ color: '#f59e0b' }}
            />
            <Area type="monotone" dataKey="tokens" stroke="#f59e0b" strokeWidth={2} fillOpacity={1} fill="url(#colorTokens)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
