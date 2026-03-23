import { useState } from 'react';
import { Library, UploadCloud, Database, FileText } from 'lucide-react';

export default function KnowledgeBase() {
  const [uploading, setUploading] = useState(false);

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploading(true);
      setTimeout(() => setUploading(false), 2000); // Mock upload delay
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-y-auto relative z-10 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <Library className="w-8 h-8 text-cyber-cyan" />
          RAG Knowledge Base
        </h1>
        <p className="text-slate-500 mt-2">Manage documentation ingested into Bedrock's OpenSearch vector store.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        
        {/* Upload Panel */}
        <div className="lg:col-span-1 glass-panel p-6 rounded-xl border border-cyber-cyan/30 flex flex-col items-center justify-center text-center">
          <UploadCloud className="w-12 h-12 text-cyber-cyan mb-4" />
          <h2 className="text-lg font-bold text-white mb-2">Ingest Runbooks</h2>
          <p className="text-sm text-slate-400 mb-6">Upload PDFs or Markdown files to expand SentinelOps reasoning capabilities.</p>
          
          <label className="glass-button w-full py-3 rounded-lg cursor-pointer bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/30 hover:bg-cyber-cyan/20 inline-flex items-center justify-center gap-2 font-medium">
             {uploading ? 'Generating Embeddings...' : 'Select Files'}
             <input type="file" multiple className="hidden" onChange={handleUpload} disabled={uploading}/>
          </label>
        </div>

        {/* Stats Panel */}
        <div className="lg:col-span-2 grid grid-cols-2 gap-4">
           <div className="glass-panel p-6 rounded-xl flex flex-col justify-center">
             <div className="text-sm font-mono text-slate-400 mb-2 flex items-center gap-2"><Database className="w-4 h-4"/> Vector Count</div>
             <div className="text-4xl font-light text-white">42,891</div>
             <div className="text-xs text-cyber-green mt-2 px-2 py-0.5 bg-cyber-green/10 rounded w-fit inline-flex">OPENSEARCH SYNCED</div>
           </div>
           
           <div className="glass-panel p-6 rounded-xl flex flex-col justify-center border-l-2 border-l-cyber-cyan">
             <div className="text-sm font-mono text-slate-400 mb-2 flex items-center gap-2"><FileText className="w-4 h-4"/> Indexed Runbooks</div>
             <div className="text-4xl font-light text-white">14</div>
             <div className="text-xs text-slate-500 mt-2 font-mono">Last indexed: 2 hours ago</div>
           </div>
        </div>
      </div>
    </div>
  );
}
