import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, TrendingDown, Target, Activity, Calendar } from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function StatsDashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/stats`);
      if (response.data.success) {
        setStats(response.data.data);
      }
    } catch (err) {
      console.error("Failed to fetch stats", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--primary)' }}>Loading Statistics...</div>;
  if (!stats) return <div style={{ textAlign: 'center', padding: '40px' }}>Failed to load statistics.</div>;

  return (
    <div className="animate-fade-in" style={{ maxWidth: '1200px', margin: '40px auto', padding: '0 20px' }}>
      <div style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: '0 0 8px 0', fontSize: '32px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <BarChart3 size={32} color="var(--accent)" /> Trading Performance
          </h1>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>Aggregated statistics and trade history</p>
        </div>
        <button 
          onClick={() => onNavigate('terminal')}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: '700', cursor: 'pointer', transition: 'all 0.3s', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)' }}
        >
          <Target size={20} /> New Trade
        </button>
      </div>

      {/* Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px', marginBottom: '40px' }}>
        
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={16} /> Total Trades
          </div>
          <div style={{ fontSize: '32px', fontWeight: '700' }}>{stats.total_trades}</div>
        </div>

        <div className="glass-panel" style={{ padding: '24px', border: `1px solid ${stats.net_pnl > 0 ? 'rgba(34,197,94,0.3)' : stats.net_pnl < 0 ? 'rgba(239,68,68,0.3)' : 'var(--glass-border)'}` }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {stats.net_pnl >= 0 ? <TrendingUp size={16} color="var(--bullish)" /> : <TrendingDown size={16} color="var(--bearish)" />} Net PnL
          </div>
          <div style={{ fontSize: '32px', fontWeight: '700', color: stats.net_pnl > 0 ? 'var(--bullish)' : stats.net_pnl < 0 ? 'var(--bearish)' : 'white' }}>
            ₹{stats.net_pnl.toFixed(2)}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Target size={16} color="var(--primary)" /> Win Rate
          </div>
          <div style={{ fontSize: '32px', fontWeight: '700' }}>{stats.win_rate}%</div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px' }}>Avg Win / Loss</div>
          <div style={{ fontSize: '20px', fontWeight: '600', color: 'var(--bullish)', marginBottom: '4px' }}>+₹{stats.avg_win.toFixed(2)}</div>
          <div style={{ fontSize: '20px', fontWeight: '600', color: 'var(--bearish)' }}>-₹{stats.avg_loss.toFixed(2)}</div>
        </div>
      </div>

      {/* Trade History Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2 style={{ margin: '0 0 20px 0', fontSize: '20px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calendar size={20} /> Recent Trade History
        </h2>
        
        {stats.history.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>No trades recorded yet.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Time</th>
                <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Symbol</th>
                <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Direction</th>
                <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Exit Reason</th>
                <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>PnL</th>
              </tr>
            </thead>
            <tbody>
              {stats.history.map((trade, idx) => (
                <tr key={idx}>
                  <td style={{ padding: '16px 12px', fontSize: '14px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {new Date(trade.timestamp).toLocaleString()}
                  </td>
                  <td style={{ padding: '16px 12px', fontSize: '14px', fontWeight: '600', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {trade.symbol}
                  </td>
                  <td style={{ padding: '16px 12px', fontSize: '14px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ background: trade.direction === 'BULL' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', color: trade.direction === 'BULL' ? 'var(--bullish)' : 'var(--bearish)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '700' }}>
                      {trade.direction}
                    </span>
                  </td>
                  <td style={{ padding: '16px 12px', fontSize: '14px', textAlign: 'right', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {trade.type === 'Target' ? 'Target Hit' : 'Time/SL'}
                  </td>
                  <td style={{ padding: '16px 12px', fontSize: '15px', fontWeight: '700', textAlign: 'right', color: trade.pnl > 0 ? 'var(--bullish)' : 'var(--bearish)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {trade.pnl > 0 ? '+' : ''}₹{trade.pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
