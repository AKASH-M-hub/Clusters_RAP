import React, { useState, useRef, useEffect } from 'react';
import { Upload, Send, FileText, Activity } from 'lucide-react';

interface Log {
  type: string;
  name?: string;
  args?: any;
  result?: string;
  content?: string;
}

interface Message {
  role: 'user' | 'agent';
  content: string;
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, logs]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setDocId(data.doc_id);
      setMessages([{ role: 'agent', content: `Successfully parsed "${data.filename}" (${data.pages} pages). You can now ask questions.` }]);
    } catch (error) {
      alert('Upload failed. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !docId) return;

    const userQ = input;
    setMessages(prev => [...prev, { role: 'user', content: userQ }]);
    setInput('');
    setLoading(true);

    const formData = new FormData();
    formData.append('doc_id', docId);
    formData.append('question', userQ);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      
      setMessages(prev => [...prev, { role: 'agent', content: data.answer }]);
      setLogs(prev => [...prev, ...data.logs, { type: 'separator' }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'agent', content: "Error communicating with server." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      {/* Main Chat Interface */}
      <div className="card chat-area">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 0 }}>
          <FileText size={24} /> Budgeted AI Agent (5-Call Max)
        </h2>
        
        {!docId ? (
          <div className="upload-area">
            <Upload size={48} color="#94a3b8" style={{ marginBottom: '1rem' }} />
            <h3>Upload PDF to Begin</h3>
            <input type="file" accept="application/pdf" onChange={handleUpload} disabled={loading} style={{ marginTop: '1rem' }} />
            {loading && <p>Parsing PDF...</p>}
          </div>
        ) : (
          <>
            <div className="messages">
              {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <strong>{msg.role === 'user' ? 'You' : 'Agent'}</strong>
                  <p style={{ margin: '0.5rem 0 0 0', whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            
            <form onSubmit={handleChat} className="input-area">
              <input 
                type="text" 
                value={input} 
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about the document..."
                disabled={loading}
              />
              <button type="submit" disabled={loading || !input.trim()}>
                <Send size={18} />
              </button>
            </form>
          </>
        )}
      </div>

      {/* Tool Call Logs Sidebar */}
      <div className="card" style={{ backgroundColor: '#1e293b', color: '#f8fafc' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 0, color: '#38bdf8' }}>
          <Activity size={20} /> Trace Logs
        </h3>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Live trace of the 5-Call Orchestrator</p>
        
        <div style={{ flexGrow: 1, overflowY: 'auto' }}>
          {logs.map((log, idx) => {
            if (log.type === 'separator') return <hr key={idx} style={{ borderColor: '#334155', margin: '1rem 0' }} />;
            if (log.type === 'tool_call') return (
              <div key={idx} className="log-entry" style={{ color: '#fbbf24' }}>
                ▶ TOOL CALL: <strong>{log.name}</strong><br/>
                <span style={{ color: '#94a3b8' }}>Args: {JSON.stringify(log.args)}</span>
              </div>
            );
            if (log.type === 'tool_result') return (
              <div key={idx} className="log-entry" style={{ color: '#34d399' }}>
                ✓ RESULT: {log.result}
              </div>
            );
            if (log.type === 'final_answer' || log.type === 'budget_exhausted') return (
              <div key={idx} className="log-entry" style={{ color: '#38bdf8' }}>
                ★ COMPLETE: {log.type === 'budget_exhausted' ? 'Budget Failed' : 'Success'}
              </div>
            );
            return null;
          })}
        </div>
      </div>
    </div>
  );
}

export default App;
