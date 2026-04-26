import { useState, useEffect } from 'react';
import { LogIn, KeyRound, ArrowRight } from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function Login({ onLoginSuccess }) {
  const [loginUrl, setLoginUrl] = useState('https://kite.zerodha.com/connect/login?v=3&api_key=wthlsr41oawqdeoz');
  const [requestToken, setRequestToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    // Fetch the login URL from the backend
    axios.get(`${API_BASE}/login_url`)
      .then(res => setLoginUrl(res.data.login_url))
      .catch(err => console.error("Failed to fetch login URL", err));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!requestToken) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await axios.post(`${API_BASE}/generate_token`, {
        request_token: requestToken
      });
      
      if (response.data.success) {
        setSuccess('Access token generated successfully!');
        setTimeout(() => {
          onLoginSuccess();
        }, 1500);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to generate token');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', padding: '20px' }}>
      <div className="glass-panel animate-slide-up" style={{ padding: '40px', width: '100%', maxWidth: '450px' }}>
        <h1 className="text-gradient" style={{ textAlign: 'center', margin: '0 0 8px 0', fontSize: '26px' }}>
          NiftyVerse Trading
        </h1>
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginBottom: '32px', fontSize: '15px' }}>
          Connect your Kite account to initialize
        </p>

        <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '16px', padding: '24px', marginBottom: '28px', border: '1px solid var(--glass-border)' }}>
          <div style={{ marginBottom: '16px', fontSize: '14px', lineHeight: '1.6', color: 'var(--text-muted)' }}>
            <strong style={{ color: 'var(--text-main)' }}>Step 1:</strong> Authenticate with your Zerodha account.
            <a 
              href={loginUrl} 
              target="_blank" 
              rel="noreferrer"
              style={{
                display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px',
                width: '100%', padding: '14px', background: 'rgba(255, 255, 255, 0.05)',
                color: 'var(--text-main)', textDecoration: 'none', borderRadius: '10px',
                marginTop: '14px', border: '1px solid rgba(255,255,255,0.1)', fontWeight: '600'
              }}
            >
              <LogIn size={18} /> Login to Zerodha
            </a>
          </div>
          <div style={{ marginBottom: '16px', fontSize: '14px', lineHeight: '1.6', color: 'var(--text-muted)' }}>
            <strong style={{ color: 'var(--text-main)' }}>Step 2:</strong> You will be redirected. Look at the URL in your browser.
          </div>
          <div style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-muted)' }}>
            <strong style={{ color: 'var(--text-main)' }}>Step 3:</strong> Copy the `request_token` and paste it below.
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-muted)', fontWeight: '600' }}>
              Request Token
            </label>
            <input 
              type="text" 
              value={requestToken}
              onChange={(e) => setRequestToken(e.target.value)}
              placeholder="e.g. jB9mX..." 
              required
              style={{
                width: '100%', padding: '14px 16px', background: 'rgba(0, 0, 0, 0.2)',
                border: '1px solid var(--glass-border)', borderRadius: '10px', color: 'white',
                fontSize: '15px', outline: 'none'
              }}
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            style={{
              display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px',
              width: '100%', padding: '16px', background: 'var(--primary)', color: 'white',
              border: 'none', borderRadius: '10px', fontSize: '16px', fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Generating...' : (
              <>Generate Access Token <ArrowRight size={18} /></>
            )}
          </button>
        </form>

        {success && (
          <div className="animate-fade-in" style={{ marginTop: '24px', padding: '14px', borderRadius: '10px', fontSize: '14px', textAlign: 'center', background: 'rgba(16, 185, 129, 0.1)', color: 'var(--bullish)', border: '1px solid rgba(16, 185, 129, 0.2)', fontWeight: '600' }}>
            {success}
          </div>
        )}

        {error && (
          <div className="animate-fade-in" style={{ marginTop: '24px', padding: '14px', borderRadius: '10px', fontSize: '14px', textAlign: 'center', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--bearish)', border: '1px solid rgba(239, 68, 68, 0.2)', fontWeight: '600' }}>
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
