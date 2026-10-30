import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Brain, Mail, Lock, User as UserIcon, AlertCircle, ArrowRight } from 'lucide-react';

interface AuthPageProps {
  initialMode?: 'login' | 'signup';
  setActiveTab?: (tab: string) => void;
  onSuccess?: () => void;
  onSwitchMode?: (mode: string) => void;
}

export const AuthPage: React.FC<AuthPageProps> = ({
  initialMode = 'login',
  setActiveTab,
  onSuccess,
  onSwitchMode
}) => {
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { login, signup } = useAuth();

  const handleModeChange = (newMode: 'login' | 'signup') => {
    setMode(newMode);
    setError(null);
    if (onSwitchMode) onSwitchMode(newMode);
    if (setActiveTab) setActiveTab(newMode);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        if (!fullName.trim()) {
          throw new Error('Please enter your full name.');
        }
        await signup(email, password, fullName);
      }
      if (onSuccess) onSuccess();
      if (setActiveTab) setActiveTab('dashboard');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '440px', margin: '40px auto 80px', width: '100%', padding: '0 16px' }}>
      <div className="card" style={{ padding: '36px', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-lg)' }}>
        {/* Brand header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              width: '52px',
              height: '52px',
              background: 'linear-gradient(135deg, var(--navy-800) 0%, var(--primary-accent) 100%)',
              color: 'white',
              borderRadius: 'var(--radius-md)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '14px',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <Brain size={28} />
          </div>
          <h2 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy-800)' }}>
            {mode === 'login' ? 'Welcome Back' : 'Create Your Account'}
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {mode === 'login'
              ? 'Access your course lectures and misconception analytics'
              : 'Join MindTrace to track and master your learning concepts'}
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div style={{
          display: 'flex',
          background: 'var(--bg-subtle)',
          padding: '4px',
          borderRadius: 'var(--radius-md)',
          marginBottom: '24px',
        }}>
          <button
            type="button"
            onClick={() => handleModeChange('login')}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              background: mode === 'login' ? '#FFFFFF' : 'transparent',
              color: mode === 'login' ? 'var(--navy-800)' : 'var(--text-muted)',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              boxShadow: mode === 'login' ? 'var(--shadow-sm)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => handleModeChange('signup')}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              background: mode === 'signup' ? '#FFFFFF' : 'transparent',
              color: mode === 'signup' ? 'var(--navy-800)' : 'var(--text-muted)',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              boxShadow: mode === 'signup' ? 'var(--shadow-sm)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="alert-banner alert-warning" style={{ marginBottom: '18px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={18} color="#DC2626" style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: '#DC2626', fontWeight: 500 }}>{error}</span>
            </div>
            {error.toLowerCase().includes('no account exists') && (
              <button
                type="button"
                onClick={() => handleModeChange('signup')}
                style={{
                  alignSelf: 'flex-start',
                  marginLeft: '26px',
                  fontSize: '12px',
                  fontWeight: 700,
                  color: 'var(--primary-accent)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0
                }}
              >
                Click here to sign up now →
              </button>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                Full Name
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="auth-fullname-input"
                  type="text"
                  className="input-field"
                  placeholder="e.g. Sarah Jenkins"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                  required
                />
              </div>
            </div>
          )}

          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
              Email Address
            </label>
            <input
              id="auth-email-input"
              type="email"
              className="input-field"
              placeholder="you@university.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
              required
            />
          </div>

          <div className="form-group" style={{ marginBottom: '22px' }}>
            <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
              Password
            </label>
            <input
              id="auth-password-input"
              type="password"
              className="input-field"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
              required
            />
          </div>

          <button
            id="auth-submit-btn"
            type="submit"
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '14px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
            disabled={submitting}
          >
            <span>{submitting ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}</span>
            {!submitting && <ArrowRight size={16} />}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '22px', fontSize: '13px', color: 'var(--text-muted)' }}>
          {mode === 'login' ? (
            <span>
              Don't have an account yet?{' '}
              <button
                type="button"
                style={{ color: 'var(--primary-accent)', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => handleModeChange('signup')}
              >
                Create one now
              </button>
            </span>
          ) : (
            <span>
              Already registered?{' '}
              <button
                type="button"
                style={{ color: 'var(--primary-accent)', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => handleModeChange('login')}
              >
                Sign in to your account
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
