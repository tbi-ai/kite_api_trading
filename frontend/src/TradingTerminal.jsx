import { useState, useRef, useEffect } from 'react';
import { Play, Square, Terminal, IndianRupee, AlertCircle, CheckCircle2 } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function TradingTerminal({ onNavigate, expiry }) {
  const [logs, setLogs] = useState([]);
  const [isTrading, setIsTrading] = useState(false);
  const [tradeSummary, setTradeSummary] = useState(null);
  const logEndRef = useRef(null);

  const startTrade = () => {
    setIsTrading(true);
    setLogs([]);
    setTradeSummary(null);

    console.log(`[Terminal] Initializing trade stream for expiry: ${expiry}...`);
    const eventSource = new EventSource(`${API_BASE}/execute_trade?expiry=${expiry}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("[Terminal] SSE Log Received:", data);
      setLogs((prev) => [...prev, data.log]);

      if (data.status === "done" || data.status === "error") {
        console.log(`[Terminal] Stream finished with status: ${data.status}`);
        setIsTrading(false);
        eventSource.close();
        if (data.status === "done") {
          setTradeSummary({ pnl: data.pnl, log: data.log });
          
          // Auto-redirect to trade DB after 3 seconds
          setTimeout(() => {
            if (onNavigate) onNavigate('stats');
          }, 3500);
        }
      }
    };

    eventSource.onerror = (error) => {
      console.error("[Terminal] SSE Connection Error:", error);
      eventSource.close();
      setIsTrading(false);
      setLogs((prev) => [...prev, "Fatal error: Connection lost to trading server."]);
    };
  };

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="animate-fade-in" style={{ maxWidth: '900px', margin: '40px auto', padding: '0 20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h1 style={{ margin: '0 0 8px 0', fontSize: '32px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Terminal size={32} color="var(--primary)" /> Live Trading Terminal
          </h1>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>Execute trades and stream live logs</p>
        </div>
        <button
          onClick={startTrade}
          disabled={isTrading}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px',
            background: isTrading ? 'rgba(255,255,255,0.1)' : 'var(--primary)',
            color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: '700',
            cursor: isTrading ? 'not-allowed' : 'pointer', transition: 'all 0.3s'
          }}
        >
          {isTrading ? <><Square size={20} /> Trade in Progress...</> : <><Play size={20} /> START TRADE</>}
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '0', overflow: 'hidden', border: '1px solid var(--glass-border)', background: 'rgba(0, 0, 0, 0.3)', fontFamily: 'monospace' }}>
        <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '12px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: 'var(--text-muted)', fontSize: '13px', display: 'flex', gap: '8px' }}>
          <div style={{width: '12px', height: '12px', borderRadius: '50%', background: '#ef4444'}}></div>
          <div style={{width: '12px', height: '12px', borderRadius: '50%', background: '#eab308'}}></div>
          <div style={{width: '12px', height: '12px', borderRadius: '50%', background: '#22c55e'}}></div>
          <span style={{marginLeft: '12px'}}>trading_execution.py</span>
        </div>
        
        <div style={{ padding: '20px', height: '400px', overflowY: 'auto', color: '#a1a1aa', fontSize: '14px', lineHeight: '1.6' }}>
          {logs.length === 0 ? (
            <div style={{ color: '#52525b', fontStyle: 'italic' }}>System ready. Press "Start Trade" to execute sequence.</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} style={{ marginBottom: '8px', display: 'flex', gap: '12px' }}>
                <span style={{ color: '#3b82f6', userSelect: 'none' }}>~</span>
                <span style={{ 
                  color: log.includes('Target hit') ? '#22c55e' : 
                         log.includes('Stop Loss') ? '#ef4444' : 
                         log.includes('Failed') ? '#ef4444' : '#e4e4e7' 
                }}>
                  {log}
                </span>
              </div>
            ))
          )}
          {isTrading && (
            <div style={{ display: 'flex', gap: '12px', animation: 'pulse 1s infinite' }}>
              <span style={{ color: '#3b82f6' }}>~</span>
              <span style={{ width: '8px', height: '16px', background: '#e4e4e7', display: 'inline-block', marginTop: '3px' }}></span>
            </div>
          )}
          <div ref={logEndRef} />
        </div>
      </div>

      {tradeSummary && (
        <div className="animate-slide-up glass-panel" style={{ marginTop: '24px', padding: '24px', border: `1px solid ${tradeSummary.pnl > 0 ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {tradeSummary.pnl > 0 ? (
                <CheckCircle2 size={40} color="var(--bullish)" />
              ) : (
                <AlertCircle size={40} color="var(--bearish)" />
              )}
              <div>
                <div style={{ fontSize: '18px', fontWeight: '700', marginBottom: '4px' }}>Trade Complete</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>{tradeSummary.log}</div>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>Realised PnL</div>
              <div style={{ fontSize: '32px', fontWeight: '800', color: tradeSummary.pnl > 0 ? 'var(--bullish)' : tradeSummary.pnl < 0 ? 'var(--bearish)' : 'white' }}>
                {tradeSummary.pnl > 0 ? '+' : ''}₹{tradeSummary.pnl.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
