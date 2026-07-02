import { useState, useEffect } from 'react';
import { Settings, RefreshCw, Save, ShieldAlert, Activity, DollarSign } from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function SettingsPanel() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [capital, setCapital] = useState(0);
  const [inputCapital, setInputCapital] = useState('');
  const [startingCapital, setStartingCapital] = useState(0);
  
  const [paperTrading, setPaperTrading] = useState(true);
  const [strategy, setStrategy] = useState('sixty_second_momentum');
  const [maxTrades, setMaxTrades] = useState(100);
  const [targetPercentage, setTargetPercentage] = useState(5.0);
  const [riskPercentage, setRiskPercentage] = useState(10.0);
  const [minPremium, setMinPremium] = useState(50.0);
  const [maxPremium, setMaxPremium] = useState(70.0);
  const [useFixedQuantity, setUseFixedQuantity] = useState(false);
  const [fixedQuantity, setFixedQuantity] = useState(250);

  useEffect(() => {
    fetchData();
    
    // Auto-refresh every 5 seconds to keep capital updated
    const interval = setInterval(() => {
      fetchData(false);
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchData = async (showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      const [portfolioRes, settingsRes] = await Promise.all([
        axios.get(`${API_BASE}/portfolio`),
        axios.get(`${API_BASE}/settings`)
      ]);
      
      if (portfolioRes.data.success) {
        const liveCapital = portfolioRes.data.data.capital;
        setCapital(liveCapital);
        setStartingCapital(portfolioRes.data.data.starting_capital);
        if (showLoader) {
          setInputCapital(liveCapital);
        }
      }
      
      if (settingsRes.data.success) {
        const s = settingsRes.data.data;
        setPaperTrading(s.paper_trading_mode);
        setStrategy(s.active_strategy);
        setMaxTrades(s.max_trades_per_day || 100);
        setTargetPercentage(s.target_percentage || 5.0);
        setRiskPercentage(s.risk_percentage || 10.0);
        setMinPremium(s.min_premium || 50.0);
        setMaxPremium(s.max_premium || 70.0);
        setUseFixedQuantity(s.use_fixed_quantity || false);
        setFixedQuantity(s.fixed_quantity || 250);
      }
    } catch (err) {
      console.error("Failed to load settings data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleResetCapital = async () => {
    if (window.confirm('Are you sure you want to reset your starting capital? This will restart your daily drawdown tracking.')) {
      try {
        await axios.post(`${API_BASE}/portfolio/reset`, { capital: parseFloat(inputCapital) });
        fetchData();
        alert('Capital reset successfully.');
      } catch (err) {
        console.error("Error resetting capital", err);
        alert('Failed to reset capital.');
      }
    }
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await axios.post(`${API_BASE}/settings/paper_trading`, { value: paperTrading });
      await axios.post(`${API_BASE}/settings/strategy`, { strategy_name: strategy });
      await axios.post(`${API_BASE}/settings/target_percentage`, { value: parseFloat(targetPercentage) });
      await axios.post(`${API_BASE}/settings/risk_percentage`, { value: parseFloat(riskPercentage) });
      await axios.post(`${API_BASE}/settings/min_premium`, { value: parseFloat(minPremium) });
      await axios.post(`${API_BASE}/settings/max_premium`, { value: parseFloat(maxPremium) });
      await axios.post(`${API_BASE}/settings/use_fixed_quantity`, { value: useFixedQuantity });
      await axios.post(`${API_BASE}/settings/fixed_quantity`, { value: parseInt(fixedQuantity) });
      await axios.post(`${API_BASE}/settings/max_trades_per_day`, { value: parseInt(maxTrades) });
      
      alert('Settings saved successfully.');
    } catch (err) {
      console.error("Failed to save settings", err);
      alert('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--primary)' }}>Loading Settings...</div>;

  const drawdownPct = startingCapital > 0 ? (((startingCapital - capital) / startingCapital) * 100).toFixed(2) : 0;
  const isNearStop = drawdownPct >= 15;

  return (
    <div className="animate-fade-in" style={{ maxWidth: '800px', margin: '40px auto', padding: '0 20px' }}>
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ margin: '0 0 8px 0', fontSize: '32px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Settings size={32} color="var(--accent)" /> Control Panel
        </h1>
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>Manage capital, toggle paper trading, and switch strategies.</p>
      </div>

      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <DollarSign size={20} color="var(--primary)" /> Portfolio Management
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Current Capital</div>
            <div style={{ fontSize: '28px', fontWeight: '700', color: capital >= startingCapital ? 'var(--bullish)' : 'var(--bearish)' }}>
              ₹{capital.toFixed(2)}
            </div>
          </div>
          
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Daily Drawdown</div>
            <div style={{ fontSize: '28px', fontWeight: '700', color: isNearStop ? 'var(--bearish)' : 'white' }}>
              {drawdownPct}% <span style={{fontSize: '12px', color: 'var(--text-muted)'}}>(Max 20%)</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Reset/Add Capital (₹)</label>
            <input 
              type="number" 
              value={inputCapital} 
              onChange={e => setInputCapital(e.target.value)}
              style={{ width: '100%', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', outline: 'none' }}
            />
          </div>
          <button 
            onClick={handleResetCapital}
            style={{ padding: '12px 24px', background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={16} /> Reset
          </button>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={20} color="var(--primary)" /> Bot Settings
        </h2>
        
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '16px' }}>Paper Trading Mode</div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Execute simulated trades using real-time price data without risking real money.</div>
            </div>
            
            <label style={{ position: 'relative', display: 'inline-block', width: '50px', height: '26px' }}>
              <input 
                type="checkbox" 
                checked={paperTrading} 
                onChange={e => setPaperTrading(e.target.checked)} 
                style={{ opacity: 0, width: 0, height: 0 }} 
              />
              <span style={{
                position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: paperTrading ? 'var(--primary)' : 'var(--glass-border)',
                transition: '.4s', borderRadius: '34px'
              }}>
                <span style={{
                  position: 'absolute', content: '""', height: '18px', width: '18px',
                  left: paperTrading ? '28px' : '4px', bottom: '4px', backgroundColor: 'white',
                  transition: '.4s', borderRadius: '50%'
                }}></span>
              </span>
            </label>
          </div>
          
          {!paperTrading && (
            <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--bearish)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <ShieldAlert size={20} color="var(--bearish)" />
              <span style={{ fontSize: '14px', color: 'var(--bearish)', fontWeight: '600' }}>Warning: Live trading is active. The bot will place real market orders.</span>
            </div>
          )}
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Active Strategy</label>
          <select 
            value={strategy}
            onChange={e => setStrategy(e.target.value)}
            style={{ width: '100%', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', outline: 'none' }}
          >
            <option value="sixty_second_momentum">Sixty Second Momentum (Rules + LSTM)</option>
            {/* Future strategies can be added here */}
          </select>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Max Trades Per Day</label>
          <input 
            type="number" 
            step="1"
            value={maxTrades} 
            onChange={e => setMaxTrades(e.target.value)}
            style={{ width: '100%', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', outline: 'none' }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Target Profit (%)</label>
            <input 
              type="number" 
              step="0.1"
              value={targetPercentage} 
              onChange={e => setTargetPercentage(e.target.value)}
              style={{ width: '100%', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', outline: 'none' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Capital Risk Per Trade (%)</label>
            <input 
              type="number" 
              step="0.1"
              value={riskPercentage} 
              onChange={e => setRiskPercentage(e.target.value)}
              style={{ width: '100%', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', outline: 'none' }}
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Min Premium (₹)</label>
            <input 
              type="number" 
              step="1"
              value={minPremium} 
              onChange={e => setMinPremium(e.target.value)}
              style={{ width: '100%', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', outline: 'none' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Max Premium (₹)</label>
            <input 
              type="number" 
              step="1"
              value={maxPremium} 
              onChange={e => setMaxPremium(e.target.value)}
              style={{ width: '100%', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', outline: 'none' }}
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Position Sizing Mode</label>
            <div style={{ display: 'flex', alignItems: 'center', padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', borderRadius: '8px', cursor: 'pointer' }} onClick={() => setUseFixedQuantity(!useFixedQuantity)}>
              <div style={{ width: '40px', height: '20px', background: useFixedQuantity ? 'var(--primary)' : 'var(--glass-border)', borderRadius: '10px', position: 'relative', transition: '0.3s', marginRight: '12px' }}>
                <div style={{ width: '16px', height: '16px', background: 'white', borderRadius: '50%', position: 'absolute', top: '2px', left: useFixedQuantity ? '22px' : '2px', transition: '0.3s' }}></div>
              </div>
              <span style={{ fontSize: '14px', color: 'white' }}>Use Fixed Quantity</span>
            </div>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Fixed Quantity (Units)</label>
            <input 
              type="number" 
              step="65"
              value={fixedQuantity} 
              onChange={e => setFixedQuantity(e.target.value)}
              disabled={!useFixedQuantity}
              style={{ width: '100%', padding: '12px', background: useFixedQuantity ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)', color: useFixedQuantity ? 'white' : 'var(--text-muted)', borderRadius: '8px', outline: 'none' }}
            />
          </div>
        </div>

        <button 
          onClick={handleSaveSettings}
          disabled={saving}
          style={{ width: '100%', padding: '14px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '8px', fontSize: '16px', fontWeight: '700', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
        >
          {saving ? <RefreshCw className="animate-spin" size={20} /> : <Save size={20} />} 
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  );
}
