import { useState, useEffect } from 'react';
import { Activity, IndianRupee, Layers, Zap, TrendingUp, TrendingDown, MinusCircle, AlertCircle } from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function Dashboard({ onLogout, onNavigate, expiry }) {
  const [data, setData] = useState(null);
  const [mlData, setMlData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mlLoading, setMlLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Training states
  const [isTraining, setIsTraining] = useState(false);
  const [trainingLogs, setTrainingLogs] = useState([]);
  const [sessionActive, setSessionActive] = useState(null);

  const fetchData = async (forceML = false) => {
    if (forceML) {
      setMlLoading(true);
      console.log("[Dashboard] Manual ML Refresh triggered.");
    }
    
    try {
      console.log(`[Dashboard] Fetching live data for expiry: ${expiry}...`);
      const [dashRes, mlRes, sessRes] = await Promise.all([
        axios.get(`${API_BASE}/dashboard?expiry=${expiry}`),
        axios.get(`${API_BASE}/ml_prediction?force_refresh=${forceML}`),
        axios.get(`${API_BASE}/session_status`)
      ]);
      
      console.log("[Dashboard] Price Data:", dashRes.data.success ? "OK" : "FAILED", dashRes.data.data);
      console.log("[Dashboard] ML Signal Data:", mlRes.data.success ? "OK" : "FAILED", mlRes.data.data);
      console.log("[Dashboard] Session Authenticated:", sessRes.data.authenticated);

      if (dashRes.data.success) setData(dashRes.data.data);
      if (mlRes.data?.success) setMlData(mlRes.data.data);
      if (sessRes.data?.success) setSessionActive(sessRes.data.authenticated);
    } catch (err) {
      console.error("[Dashboard] Fetch Error:", err);
      if (err.response?.status === 401) {
        console.warn("[Dashboard] 401 Unauthorized - redirecting to login.");
        onLogout();
      } else {
        setError(err.response?.data?.error || err.message || 'Failed to fetch dashboard data');
      }
    } finally {
      setLoading(false);
      setMlLoading(false);
    }
  };

  const startTraining = () => {
    setIsTraining(true);
    setTrainingLogs(["Initializing LSTM training process..."]);
    
    const eventSource = new EventSource(`${API_BASE}/train_model`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setTrainingLogs((prev) => [...prev.slice(-15), data.log]); // Keep last 15 lines

      if (data.status === "done") {
        setIsTraining(false);
        eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      console.error("SSE Error:", err);
      setIsTraining(false);
      eventSource.close();
      setTrainingLogs((prev) => [...prev, "Error: Lost connection to training server."]);
    };
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(false), 5000);
    return () => clearInterval(interval);
  }, [onLogout, expiry]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <div style={{ color: 'var(--primary)', fontSize: '20px', fontWeight: '600', animation: 'pulse 2s infinite' }}>
          Loading Market Intelligence...
        </div>
      </div>
    );
  }

  if (error) {
    const isSessionError = error.toLowerCase().includes('session') || error.toLowerCase().includes('token');
    return (
      <div style={{ padding: '40px', maxWidth: '600px', margin: '40px auto' }}>
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--bearish)', padding: '32px', borderRadius: '16px', border: '1px solid rgba(239, 68, 68, 0.2)', textAlign: 'center' }}>
          <AlertCircle size={48} style={{ marginBottom: '16px' }} />
          <h2 style={{ margin: '0 0 12px 0', color: 'white' }}>{isSessionError ? 'Kite Session Expired' : 'Connection Error'}</h2>
          <p style={{ margin: '0 0 24px 0', lineHeight: '1.5', color: 'rgba(255,255,255,0.7)' }}>
            {isSessionError 
              ? 'Your Zerodha session has expired or the token is invalid. Please login again to restore connection.' 
              : `We encountered an issue connecting to the API: ${error}`}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px' }}>
            <button 
              onClick={() => fetchData()} 
              style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: 'white', padding: '12px 24px', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}
            >
              Retry Connection
            </button>
            <button 
              onClick={onLogout} 
              style={{ background: 'var(--primary)', border: 'none', color: 'white', padding: '12px 24px', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)' }}
            >
              Go to Login Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ paddingBottom: '40px' }}>
      <div style={{ maxWidth: '1200px', margin: '40px auto', padding: '0 20px' }}>
        
        {/* --- Header Section --- */}
        <div style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: '0 0 8px 0', fontSize: '32px', fontWeight: '700' }}>Trading Terminal</h1>
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>Modular Trading & AI Prediction Suite</p>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button 
              onClick={() => onNavigate('terminal')}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: '700', cursor: 'pointer', transition: 'all 0.3s', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)' }}
            >
              <Zap size={20} /> Execute Trade
            </button>
          </div>
        </div>

        {/* --- ZONE 1: PREPARATION & TRAINING (Pre-Market) --- */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}><Activity size={18} color="var(--accent)" /></div>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '1px' }}>Preparation Zone <span style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: '400', marginLeft: '8px' }}>(Run Before Market Opens)</span></h2>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', background: sessionActive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', border: `1px solid ${sessionActive ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`, borderRadius: '20px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: sessionActive ? 'var(--bullish)' : 'var(--bearish)', boxShadow: sessionActive ? '0 0 10px var(--bullish)' : 'none' }}></div>
              <span style={{ fontSize: '12px', fontWeight: '700', color: sessionActive ? 'var(--bullish)' : 'var(--bearish)' }}>
                {sessionActive === null ? 'Checking Session...' : sessionActive ? 'KITE SESSION ACTIVE' : 'SESSION EXPIRED'}
              </span>
            </div>
          </div>
          
          <div className="glass-panel" style={{ padding: '24px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>Deep Learning Model Retraining</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '4px 0 0 0' }}>Fetch 180 days of history and optimize LSTM weights</p>
              </div>
              <button
                onClick={startTraining}
                disabled={isTraining}
                style={{ padding: '10px 24px', background: isTraining ? 'rgba(255,255,255,0.1)' : 'var(--accent)', color: 'white', border: 'none', borderRadius: '10px', fontWeight: '700', cursor: isTraining ? 'not-allowed' : 'pointer', transition: 'all 0.3s' }}
              >
                {isTraining ? 'Training in Progress...' : 'Start Model Retraining'}
              </button>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '12px', padding: '16px', fontFamily: 'monospace', fontSize: '13px', minHeight: '100px', maxHeight: '180px', overflowY: 'auto', border: '1px solid var(--glass-border)', color: '#a1a1aa' }}>
              {trainingLogs.length === 0 ? (
                <div style={{ color: '#52525b', fontStyle: 'italic' }}>Waiting for command... Retrain the model daily for best results.</div>
              ) : (
                trainingLogs.map((log, i) => (
                  <div key={i} style={{ marginBottom: '4px', display: 'flex', gap: '8px' }}>
                    <span style={{ color: 'var(--accent)' }}>$</span> <span>{log}</span>
                  </div>
                ))
              )}
              {isTraining && (
                <div style={{ animation: 'pulse 1s infinite', color: 'var(--accent)', marginLeft: '4px' }}>_</div>
              )}
            </div>
          </div>
        </div>

        <div style={{ height: '1px', background: 'linear-gradient(90deg, transparent, var(--glass-border), transparent)', marginBottom: '40px' }}></div>

        {/* --- ZONE 2: MARKET INTELLIGENCE (Live Market) --- */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{ padding: '8px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px' }}><Zap size={18} color="var(--primary)" /></div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '1px' }}>Market Intelligence <span style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: '400', marginLeft: '8px' }}>(Real-time Inference)</span></h2>
        </div>

        {mlData && (
          <div className="glass-panel" style={{ padding: '32px', marginBottom: '40px', position: 'relative', overflow: 'hidden', border: `1px solid ${mlData.signal === 'BULL' ? 'rgba(16, 185, 129, 0.3)' : mlData.signal === 'BEAR' ? 'rgba(239, 68, 68, 0.3)' : 'var(--glass-border)'}` }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '4px', background: mlData.signal === 'BULL' ? 'var(--bullish)' : mlData.signal === 'BEAR' ? 'var(--bearish)' : 'var(--neutral)' }}></div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '24px' }}>
              
              {/* Signal Status */}
              <div style={{ flex: '1 1 300px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={16} color="var(--accent)" /> LSTM Prediction
                  </div>
                  <button 
                    onClick={() => fetchData(true)}
                    disabled={mlLoading}
                    style={{ background: 'var(--primary)', border: 'none', borderRadius: '8px', color: 'white', padding: '6px 14px', fontSize: '12px', fontWeight: '700', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', boxShadow: '0 4px 10px rgba(59, 130, 246, 0.2)' }}
                  >
                    {mlLoading ? 'Recalculating...' : <><Activity size={14} /> GET LIVE INFERENCE</>}
                  </button>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
                  {mlData.signal === 'BULL' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--bullish)', fontSize: '36px', fontWeight: '800', textShadow: '0 0 20px rgba(16, 185, 129, 0.4)' }}>
                      <TrendingUp size={40} /> BULLISH
                    </div>
                  )}
                  {mlData.signal === 'BEAR' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--bearish)', fontSize: '36px', fontWeight: '800', textShadow: '0 0 20px rgba(239, 68, 68, 0.4)' }}>
                      <TrendingDown size={40} /> BEARISH
                    </div>
                  )}
                  {mlData.signal === 'NO_SIGNAL' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-muted)', fontSize: '32px', fontWeight: '700' }}>
                      <MinusCircle size={36} /> NEUTRAL
                    </div>
                  )}
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>AI EXPECTED MOVE:</div>
                  <div style={{ fontSize: '28px', fontWeight: '800', color: mlData.lstm_prediction > 0 ? 'var(--bullish)' : mlData.lstm_prediction < 0 ? 'var(--bearish)' : 'white' }}>
                    {mlData.lstm_prediction > 0 ? '+' : ''}{mlData.lstm_prediction} pts
                  </div>
                  <div style={{ color: '#52525b', fontSize: '11px', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Activity size={10} /> Prediction Age: {mlData.lstm_timestamp ? new Date(mlData.lstm_timestamp * 1000).toLocaleTimeString() : 'N/A'}
                  </div>
                </div>

                {mlData.squeeze_active && (
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', padding: '6px 12px', borderRadius: '20px', fontSize: '13px', fontWeight: '600', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                    <AlertCircle size={14} /> Volatility Squeeze Active (Signals Suppressed)
                  </div>
                )}
              </div>

              {/* Indicator Metrics */}
              <div style={{ flex: '1 1 400px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '16px', border: '1px solid var(--glass-border)' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>RSI (14) / Fast RSI (6)</div>
                  <div style={{ fontSize: '16px', fontWeight: '600' }}>{mlData.indicators.rsi14} <span style={{color: 'var(--text-muted)'}}>/</span> {mlData.indicators.rsi6}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>EMA (9) / EMA (21)</div>
                  <div style={{ fontSize: '16px', fontWeight: '600' }}>{mlData.indicators.ema9} <span style={{color: 'var(--text-muted)'}}>/</span> {mlData.indicators.ema21}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>MACD</div>
                  <div style={{ fontSize: '16px', fontWeight: '600', color: mlData.indicators.macd > 0 ? 'var(--bullish)' : 'var(--bearish)' }}>{mlData.indicators.macd}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>SuperTrend</div>
                  <div style={{ fontSize: '16px', fontWeight: '600', color: mlData.indicators.current_price > mlData.indicators.supertrend ? 'var(--bullish)' : 'var(--bearish)' }}>{mlData.indicators.supertrend}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', marginBottom: '40px' }}>
          
          {/* Spot Card */}
          <div className="glass-panel" style={{ padding: '24px', position: 'relative', overflow: 'hidden' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={16} color="var(--primary)" /> Nifty 50 (Spot)
            </div>
            <div style={{ fontSize: '36px', fontWeight: '700', display: 'flex', alignItems: 'center' }}>
              <span style={{ fontSize: '20px', color: 'var(--text-muted)', marginRight: '8px' }}><IndianRupee size={20} /></span>
              {data?.spot_price}
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '12px' }}>Rounded ATM: ₹{data?.rounded_spot}</p>
          </div>

          {/* Range Card */}
          <div className="glass-panel" style={{ padding: '24px', position: 'relative', overflow: 'hidden' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={16} color="var(--bullish)" /> Tracked Range
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700', marginTop: '8px' }}>
              {data?.lower_range} <span style={{ color: 'var(--text-muted)', fontSize: '16px', margin: '0 8px' }}>to</span> {data?.upper_range}
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '12px' }}>± 1000 points from ATM</p>
          </div>
        </div>

        {/* Generated Option Strikes */}
        {data && (
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600' }}>Live Option Chain</h2>
              <span style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', padding: '6px 12px', borderRadius: '20px', fontSize: '13px', fontWeight: '600', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                {data.options.length} Strikes
              </span>
            </div>
            <div className="glass-panel" style={{ overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--glass-border)' }}>
                  <th style={{ padding: '16px 24px', fontSize: '12px', fontWeight: '700', color: 'var(--bullish)', textTransform: 'uppercase' }}>CALL PREMIUM</th>
                  <th style={{ padding: '16px 24px', fontSize: '12px', fontWeight: '700', color: 'var(--text-muted)', textAlign: 'center' }}>STRIKE</th>
                  <th style={{ padding: '16px 24px', fontSize: '12px', fontWeight: '700', color: 'var(--bearish)', textTransform: 'uppercase', textAlign: 'right' }}>PUT PREMIUM</th>
                </tr>
              </thead>
              <tbody>
                {data?.options?.map((opt, idx) => {
                  const isATM = opt.strike === data.rounded_spot;
                  return (
                    <tr key={idx} style={{ 
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                      background: isATM ? 'rgba(59, 130, 246, 0.05)' : 'transparent',
                      transition: 'background 0.2s'
                    }}>
                      <td style={{ padding: '16px 24px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ color: 'var(--bullish)', fontWeight: '700', fontSize: '16px' }}>₹{opt.ce_price.toFixed(2)}</span>
                          <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>{opt.ce_symbol.split(':').pop()}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px', textAlign: 'center' }}>
                        <div style={{ 
                          display: 'inline-block', padding: '4px 12px', borderRadius: '6px',
                          background: isATM ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                          color: isATM ? 'white' : 'var(--text-main)',
                          fontWeight: '800', fontSize: '14px', border: isATM ? 'none' : '1px solid rgba(255,255,255,0.1)'
                        }}>
                          {opt.strike}
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                          <span style={{ color: 'var(--bearish)', fontWeight: '700', fontSize: '16px' }}>₹{opt.pe_price.toFixed(2)}</span>
                          <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>{opt.pe_symbol.split(':').pop()}</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          </div>
        )}
      </div>
    </div>
  );
}
