import { useState, useEffect } from 'react'
import Login from './Login'
import Dashboard from './Dashboard'
import TradingTerminal from './TradingTerminal'
import StatsDashboard from './StatsDashboard'
import { LayoutDashboard, TerminalSquare, BarChart3, LogOut } from 'lucide-react'
import axios from 'axios'
import './index.css'

const API_BASE = 'http://127.0.0.1:8000/api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentView, setCurrentView] = useState('market') // 'market', 'terminal', 'stats'
  const [expiry, setExpiry] = useState('26MAY')
  const [expiries, setExpiries] = useState([])

  useEffect(() => {
    if (isAuthenticated) {
      axios.get(`${API_BASE}/expiries`)
        .then(res => {
          if (res.data.success && res.data.data.length > 0) {
            setExpiries(res.data.data);
            setExpiry(res.data.data[0].value);
          }
        })
        .catch(err => console.error("Failed to fetch expiries", err));
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <Login onLoginSuccess={() => setIsAuthenticated(true)} />
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Global Navigation Bar */}
      <nav style={{ background: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(10px)', borderBottom: '1px solid var(--glass-border)', padding: '16px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, zIndex: 100 }}>
        <div className="text-gradient" style={{ fontSize: '22px', fontWeight: '700' }}>NiftyVerse</div>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={() => setCurrentView('market')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', background: currentView === 'market' ? 'rgba(59, 130, 246, 0.15)' : 'transparent', border: 'none', color: currentView === 'market' ? 'var(--primary)' : 'var(--text-muted)', cursor: 'pointer', fontSize: '14px', fontWeight: '600', padding: '8px 16px', borderRadius: '8px', transition: 'all 0.2s' }}
          >
            <LayoutDashboard size={18} /> Market Intel
          </button>
          <button 
            onClick={() => setCurrentView('terminal')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', background: currentView === 'terminal' ? 'rgba(59, 130, 246, 0.15)' : 'transparent', border: 'none', color: currentView === 'terminal' ? 'var(--primary)' : 'var(--text-muted)', cursor: 'pointer', fontSize: '14px', fontWeight: '600', padding: '8px 16px', borderRadius: '8px', transition: 'all 0.2s' }}
          >
            <TerminalSquare size={18} /> Trading Terminal
          </button>
          <button 
            onClick={() => setCurrentView('stats')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', background: currentView === 'stats' ? 'rgba(59, 130, 246, 0.15)' : 'transparent', border: 'none', color: currentView === 'stats' ? 'var(--primary)' : 'var(--text-muted)', cursor: 'pointer', fontSize: '14px', fontWeight: '600', padding: '8px 16px', borderRadius: '8px', transition: 'all 0.2s' }}
          >
            <BarChart3 size={18} /> Statistics
          </button>
          
          <div style={{ width: '1px', background: 'var(--glass-border)', margin: '0 8px' }}></div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.05)', padding: '4px 12px', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Expiry:</span>
            <select 
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              style={{ background: 'transparent', border: 'none', color: 'white', fontSize: '14px', fontWeight: '700', outline: 'none', cursor: 'pointer' }}
            >
              {expiries.length > 0 ? (
                expiries.map((exp, idx) => (
                  <option key={idx} value={exp.value} style={{ background: '#1e293b', color: 'white' }}>
                    {exp.display} ({exp.value})
                  </option>
                ))
              ) : (
                <option value="26MAY">26MAY</option>
              )}
            </select>
          </div>

          <div style={{ width: '1px', background: 'var(--glass-border)', margin: '0 8px' }}></div>
          
          <button 
            onClick={() => setIsAuthenticated(false)}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'transparent', border: 'none', color: 'var(--bearish)', cursor: 'pointer', fontSize: '14px', fontWeight: '600', padding: '8px 16px', borderRadius: '8px' }}
          >
            <LogOut size={18} /> Logout
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <div style={{ flex: 1 }}>
        {currentView === 'market' && <Dashboard onLogout={() => setIsAuthenticated(false)} onNavigate={setCurrentView} expiry={expiry} />}
        {currentView === 'terminal' && <TradingTerminal onNavigate={setCurrentView} expiry={expiry} />}
        {currentView === 'stats' && <StatsDashboard onNavigate={setCurrentView} />}
      </div>
    </div>
  )
}

export default App
