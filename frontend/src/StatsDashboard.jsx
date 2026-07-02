import { useState, useEffect, useRef } from 'react';
import { BarChart3, TrendingUp, TrendingDown, Target, Activity, Calendar, Columns } from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function StatsDashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [strategyFilter, setStrategyFilter] = useState('All');
  
  const allColumns = [
    { id: 'entry_time', label: 'Entry Time' },
    { id: 'exit_time', label: 'Exit Time' },
    { id: 'symbol', label: 'Symbol' },
    { id: 'direction', label: 'Direction' },
    { id: 'qty', label: 'Qty' },
    { id: 'entry', label: 'Entry' },
    { id: 'exit', label: 'Exit' },
    { id: 'status', label: 'Status' },
    { id: 'gross_pnl', label: 'Gross PnL' },
    { id: 'taxes', label: 'Taxes' },
    { id: 'pnl', label: 'Net PnL' },
    { id: 'pnl_pct', label: 'PnL %' }
  ];
  
  const [visibleColumns, setVisibleColumns] = useState(allColumns.map(c => c.id));
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const columnMenuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (columnMenuRef.current && !columnMenuRef.current.contains(event.target)) {
        setShowColumnMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    fetchStats();
    
    // Auto-refresh stats every 5 seconds to show "live" trades
    const interval = setInterval(() => {
      fetchStats(false); // pass false to avoid loading spinner on every tick
    }, 5000);
    
    return () => clearInterval(interval);
  }, [startDate, endDate, strategyFilter]);

  const fetchStats = async (showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/stats?start_date=${startDate}&end_date=${endDate}&strategy=${strategyFilter}`);
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
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '8px 16px', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>From:</span>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{ background: 'transparent', border: 'none', color: 'white', outline: 'none' }} />
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', marginLeft: '12px' }}>To:</span>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={{ background: 'transparent', border: 'none', color: 'white', outline: 'none' }} />
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', marginLeft: '12px' }}>Strategy:</span>
            <select value={strategyFilter} onChange={e => setStrategyFilter(e.target.value)} style={{ background: 'transparent', border: 'none', color: 'var(--accent)', outline: 'none', cursor: 'pointer', fontWeight: '600' }}>
              <option style={{ color: 'black' }} value="All">All</option>
              <option style={{ color: 'black' }} value="sixty_second_momentum">60s Momentum</option>
              <option style={{ color: 'black' }} value="tax_optimized_momentum">Tax Optimized</option>
              <option style={{ color: 'black' }} value="tax_optimized">Tax Optimized (Backtest)</option>
            </select>
          </div>
          
          <div style={{ position: 'relative' }} ref={columnMenuRef}>
            <button 
              onClick={() => setShowColumnMenu(!showColumnMenu)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 16px', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--glass-border)', borderRadius: '12px', cursor: 'pointer' }}
            >
              <Columns size={16} /> Columns
            </button>
            {showColumnMenu && (
              <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: '8px', background: 'rgba(30, 41, 59, 0.98)', border: '1px solid var(--glass-border)', borderRadius: '12px', padding: '12px', zIndex: 10, minWidth: '180px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)' }}>
                {allColumns.map(col => (
                  <label key={col.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0', cursor: 'pointer', color: 'white', fontSize: '14px' }}>
                    <input 
                      type="checkbox" 
                      checked={visibleColumns.includes(col.id)} 
                      onChange={() => {
                        if (visibleColumns.includes(col.id)) {
                          setVisibleColumns(visibleColumns.filter(id => id !== col.id));
                        } else {
                          setVisibleColumns([...visibleColumns, col.id]);
                        }
                      }}
                    />
                    {col.label}
                  </label>
                ))}
              </div>
            )}
          </div>
          
          <button 
            onClick={() => onNavigate('terminal')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: '700', cursor: 'pointer', transition: 'all 0.3s', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)' }}
          >
            <Target size={20} /> New Trade
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px', marginBottom: '40px' }}>
        
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={16} /> Total Trades
          </div>
          <div style={{ fontSize: '32px', fontWeight: '700', marginBottom: '4px' }}>{stats.total_trades}</div>
          {stats.portfolio && (
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Capital: ₹{stats.portfolio.capital.toFixed(2)}
            </div>
          )}
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
                {visibleColumns.includes('entry_time') && <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Entry Time</th>}
                {visibleColumns.includes('exit_time') && <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Exit Time</th>}
                {visibleColumns.includes('symbol') && <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Symbol</th>}
                {visibleColumns.includes('direction') && <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Direction</th>}
                {visibleColumns.includes('qty') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Qty</th>}
                {visibleColumns.includes('entry') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Entry</th>}
                {visibleColumns.includes('exit') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Exit</th>}
                {visibleColumns.includes('status') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Status</th>}
                {visibleColumns.includes('gross_pnl') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Gross PnL</th>}
                {visibleColumns.includes('taxes') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Taxes</th>}
                {visibleColumns.includes('pnl') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>Net PnL</th>}
                {visibleColumns.includes('pnl_pct') && <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-muted)', fontSize: '13px', borderBottom: '1px solid var(--glass-border)' }}>PnL %</th>}
              </tr>
            </thead>
            <tbody>
              {stats.history.map((trade, idx) => {
                const pnlPercent = trade.entry_price > 0 ? (trade.exit_price - trade.entry_price) / trade.entry_price * 100 : 0;
                return (
                <tr key={idx}>
                  {visibleColumns.includes('entry_time') && <td style={{ padding: '16px 12px', fontSize: '14px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {new Date(trade.timestamp).toLocaleString()}
                  </td>}
                  {visibleColumns.includes('exit_time') && <td style={{ padding: '16px 12px', fontSize: '14px', color: 'var(--text-muted)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {trade.exit_timestamp ? new Date(trade.exit_timestamp).toLocaleString() : '-'}
                  </td>}
                  {visibleColumns.includes('symbol') && <td style={{ padding: '16px 12px', fontSize: '14px', fontWeight: '600', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {trade.symbol}
                  </td>}
                  {visibleColumns.includes('direction') && <td style={{ padding: '16px 12px', fontSize: '14px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ background: trade.direction === 'BULL' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', color: trade.direction === 'BULL' ? 'var(--bullish)' : 'var(--bearish)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '700' }}>
                      {trade.direction}
                    </span>
                  </td>}
                  {visibleColumns.includes('qty') && <td style={{ padding: '16px 12px', fontSize: '14px', textAlign: 'right', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {trade.qty || 0}
                  </td>}
                  {visibleColumns.includes('entry') && <td style={{ padding: '16px 12px', fontSize: '14px', textAlign: 'right', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    ₹{(trade.entry_price || 0).toFixed(2)}
                  </td>}
                  {visibleColumns.includes('exit') && <td style={{ padding: '16px 12px', fontSize: '14px', textAlign: 'right', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    ₹{(trade.exit_price || 0).toFixed(2)}
                  </td>}
                  {visibleColumns.includes('status') && <td style={{ padding: '16px 12px', fontSize: '14px', textAlign: 'right', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginRight: '8px' }}>{trade.is_paper ? '(Paper)' : '(Live)'}</span>
                    {trade.status}
                  </td>}
                  {visibleColumns.includes('gross_pnl') && <td style={{ padding: '16px 12px', fontSize: '14px', textAlign: 'right', color: (trade.gross_pnl || 0) > 0 ? 'var(--bullish)' : (trade.gross_pnl || 0) < 0 ? 'var(--bearish)' : 'white', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {(trade.gross_pnl || 0) > 0 ? '+' : ''}₹{(trade.gross_pnl || 0).toFixed(2)}
                  </td>}
                  {visibleColumns.includes('taxes') && <td style={{ padding: '16px 12px', fontSize: '14px', textAlign: 'right', color: 'var(--bearish)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    -₹{(trade.taxes || 0).toFixed(2)}
                  </td>}
                  {visibleColumns.includes('pnl') && <td style={{ padding: '16px 12px', fontSize: '15px', fontWeight: '700', textAlign: 'right', color: trade.pnl > 0 ? 'var(--bullish)' : trade.pnl < 0 ? 'var(--bearish)' : 'white', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {trade.pnl > 0 ? '+' : ''}₹{trade.pnl.toFixed(2)}
                  </td>}
                  {visibleColumns.includes('pnl_pct') && <td style={{ padding: '16px 12px', fontSize: '14px', fontWeight: '600', textAlign: 'right', color: pnlPercent > 0 ? 'var(--bullish)' : pnlPercent < 0 ? 'var(--bearish)' : 'white', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {pnlPercent > 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                  </td>}
                </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
