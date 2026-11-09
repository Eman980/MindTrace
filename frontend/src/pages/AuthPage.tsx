import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  Brain,
  Mail,
  Lock,
  User as UserIcon,
  AlertCircle,
  ArrowRight,
  Eye,
  EyeOff,
  CheckCircle2,
  RefreshCw,
  KeyRound,
  ArrowLeft,
  Sparkles
} from 'lucide-react';

interface AuthPageProps {
  initialMode?: 'login' | 'signup' | 'forgot-password' | 'reset-password';
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
  const [mode, setMode] = useState<'login' | 'signup' | 'forgot-password' | 'reset-password'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [resetToken, setResetToken] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [noteMessage, setNoteMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { login, signup } = useAuth();

  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tokenParam = params.get('token') || params.get('reset_token');
      const hash = window.location.hash;
      if (tokenParam) {
        setResetToken(tokenParam);
        setMode('reset-password');
      } else if (hash.includes('reset-password')) {
        setMode('reset-password');
      }
    } catch {
      // Ignore URL parsing errors
    }
  }, []);

  const handleModeChange = (newMode: 'login' | 'signup' | 'forgot-password' | 'reset-password') => {
    setMode(newMode);
    setError(null);
    setInfoMessage(null);
    setNoteMessage(null);
    if (onSwitchMode && (newMode === 'login' || newMode === 'signup')) {
      onSwitchMode(newMode);
    }
  };

  const handleLoginOrSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setError(null);
    setInfoMessage(null);
    setNoteMessage(null);

    // Validation
    const cleanEmail = email.trim();
    if (!cleanEmail && !password) {
      setError('Please enter your email and password.');
      return;
    }
    if (!cleanEmail) {
      setError('Please enter your email address.');
      return;
    }
    if (!cleanEmail.includes('@') || !cleanEmail.includes('.')) {
      setError('Please enter a valid email address.');
      return;
    }

    if (!password) {
      setError('Please enter your password.');
      return;
    }

    if (mode === 'signup') {
      if (!fullName.trim()) {
        setError('Please enter your full name.');
        return;
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters long.');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(cleanEmail, password);
      } else {
        await signup(cleanEmail, password, fullName.trim());
      }
      if (onSuccess) onSuccess();
      if (setActiveTab) setActiveTab('dashboard');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgotPasswordRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setError('Please enter your registered email address.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.auth.forgotPassword({ email: cleanEmail });
      setInfoMessage(res.message);
      if (res.note) {
        setNoteMessage(res.note);
      }
      if (res.reset_token) {
        setResetToken(res.reset_token);
        // Automatically give user opportunity to reset right now
        setMode('reset-password');
      }
    } catch (err: any) {
      setError(err.message || 'Could not process password recovery.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);

    if (!resetToken.trim()) {
      setError('Password reset token is required. Please check your email or enter your token.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (!anyDigitOrSpecial(password)) {
      setError('Password must contain at least one number or special symbol.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify both fields.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.auth.resetPassword({
        token: resetToken.trim(),
        new_password: password,
        confirm_password: confirmPassword,
      });
      setInfoMessage(res.message);
      setPassword('');
      setConfirmPassword('');
      setResetToken('');
      // Transition to login after short delay or allow one-click login
      setTimeout(() => {
        setMode('login');
        setInfoMessage('Password reset successfully! You can now sign in with your new password.');
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to reset password. The link or token may have expired.');
    } finally {
      setSubmitting(false);
    }
  };

  const anyDigitOrSpecial = (str: string) => {
    return /\d/.test(str) || /[^a-zA-Z0-9]/.test(str);
  };

  return (
    <div style={{ maxWidth: '460px', margin: '40px auto 80px', width: '100%', padding: '0 16px' }}>
      <div className="card" style={{ padding: '36px', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-lg)' }}>
        {/* Brand header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
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
            {mode === 'login'
              ? 'Welcome Back'
              : mode === 'signup'
              ? 'Create Your Account'
              : mode === 'forgot-password'
              ? 'Reset Password'
              : 'Set New Password'}
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px', lineHeight: 1.5 }}>
            {mode === 'login'
              ? 'Access your course lectures and misconception analytics'
              : mode === 'signup'
              ? 'Join MindTrace to track and master your learning concepts'
              : mode === 'forgot-password'
              ? 'Enter your registered email to receive secure recovery instructions'
              : 'Enter and confirm your new secure password'}
          </p>
        </div>

        {/* Mode Selector Tabs (only shown on login/signup) */}
        {(mode === 'login' || mode === 'signup') && (
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
        )}

        {/* Error Alert */}
        {error && (
          <div
            className="alert-banner alert-warning"
            style={{
              marginBottom: '18px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              padding: '12px 14px',
              background: '#FEE2E2',
              border: '1px solid #FECACA',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <AlertCircle size={18} color="#DC2626" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1, fontSize: '13px', color: '#B91C1C', fontWeight: 600, lineHeight: 1.4 }}>
              {error}
            </div>
          </div>
        )}

        {/* Success / Info Alert */}
        {infoMessage && (
          <div
            style={{
              marginBottom: noteMessage ? '10px' : '18px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              padding: '12px 14px',
              background: '#DCFCE7',
              border: '1px solid #BBF7D0',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <CheckCircle2 size={18} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1, fontSize: '13px', color: '#166534', fontWeight: 600, lineHeight: 1.4 }}>
              {infoMessage}
            </div>
          </div>
        )}

        {/* Server Note Alert (e.g. SMTP info / Dev token info) */}
        {noteMessage && (
          <div
            style={{
              marginBottom: '18px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              padding: '12px 14px',
              background: '#EEF2FF',
              border: '1px solid #C7D2FE',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <Sparkles size={18} color="#4F46E5" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1, fontSize: '12px', color: '#3730A3', lineHeight: 1.5 }}>
              <strong>Notice:</strong> {noteMessage}
            </div>
          </div>
        )}

        {/* ── 1. LOGIN & SIGNUP FORMS ────────────────────────────────────────── */}
        {(mode === 'login' || mode === 'signup') && (
          <form onSubmit={handleLoginOrSignup}>
            {mode === 'signup' && (
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                  Full Name
                </label>
                <div style={{ position: 'relative' }}>
                  <UserIcon size={16} color="var(--text-light)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                  <input
                    id="auth-fullname-input"
                    type="text"
                    className="input-field"
                    placeholder="e.g. Alex Chen"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px 10px 36px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                    disabled={submitting}
                  />
                </div>
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} color="var(--text-light)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  id="auth-email-input"
                  type="email"
                  className="input-field"
                  placeholder="you@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px 10px 36px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                  disabled={submitting}
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '8px' }}>
              <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color="var(--text-light)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  id="auth-password-input"
                  type={showPassword ? 'text' : 'password'}
                  className="input-field"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ width: '100%', padding: '10px 40px 10px 36px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                  disabled={submitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '12px',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-light)',
                    cursor: 'pointer',
                    padding: 0
                  }}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Forgot Password link in login mode */}
            {mode === 'login' && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}>
                <button
                  id="auth-forgot-password-link"
                  type="button"
                  onClick={() => handleModeChange('forgot-password')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--primary-accent)',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  Forgot Password?
                </button>
              </div>
            )}

            {mode === 'signup' && <div style={{ height: '16px' }} />}

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
              {submitting ? (
                <>
                  <RefreshCw size={16} className="spin-animation" />
                  <span>{mode === 'login' ? 'Authenticating...' : 'Creating account...'}</span>
                </>
              ) : (
                <>
                  <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>
        )}

        {/* ── 2. FORGOT PASSWORD REQUEST FORM ─────────────────────────────────── */}
        {mode === 'forgot-password' && (
          <form onSubmit={handleForgotPasswordRequest}>
            <div className="form-group" style={{ marginBottom: '20px' }}>
              <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                Registered Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} color="var(--text-light)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  id="auth-recovery-email-input"
                  type="email"
                  className="input-field"
                  placeholder="you@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px 10px 36px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                  disabled={submitting}
                  required
                />
              </div>
            </div>

            <button
              id="auth-send-recovery-btn"
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
                gap: '8px',
                marginBottom: '14px'
              }}
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <RefreshCw size={16} className="spin-animation" />
                  <span>Generating token...</span>
                </>
              ) : (
                <>
                  <KeyRound size={16} />
                  <span>Send Recovery Instructions</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => handleModeChange('login')}
              style={{
                width: '100%',
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '8px'
              }}
            >
              <ArrowLeft size={14} />
              <span>Back to Sign In</span>
            </button>
          </form>
        )}

        {/* ── 3. RESET PASSWORD FORM ─────────────────────────────────────────── */}
        {mode === 'reset-password' && (
          <form onSubmit={handleResetPasswordSubmit}>
            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                Recovery Reset Token
              </label>
              <div style={{ position: 'relative' }}>
                <KeyRound size={16} color="var(--text-light)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  id="auth-reset-token-input"
                  type="text"
                  className="input-field"
                  placeholder="Paste your 36-character reset token"
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px 10px 36px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '13px', fontFamily: 'JetBrains Mono, monospace' }}
                  disabled={submitting}
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                New Password (minimum 8 characters)
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color="var(--text-light)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  id="auth-new-password-input"
                  type={showPassword ? 'text' : 'password'}
                  className="input-field"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ width: '100%', padding: '10px 40px 10px 36px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                  disabled={submitting}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '12px',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-light)',
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {password.length > 0 && (
                <div style={{ marginTop: '4px', fontSize: '11px', display: 'flex', gap: '8px' }}>
                  <span style={{ color: password.length >= 8 ? '#16A34A' : '#DC2626' }}>
                    {password.length >= 8 ? '✓' : '✗'} 8+ characters
                  </span>
                  <span style={{ color: anyDigitOrSpecial(password) ? '#16A34A' : '#DC2626' }}>
                    {anyDigitOrSpecial(password) ? '✓' : '✗'} 1+ number or symbol
                  </span>
                </div>
              )}
            </div>

            <div className="form-group" style={{ marginBottom: '22px' }}>
              <label className="form-label" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                Confirm New Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color="var(--text-light)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  id="auth-confirm-password-input"
                  type={showConfirmPassword ? 'text' : 'password'}
                  className="input-field"
                  placeholder="••••••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  style={{ width: '100%', padding: '10px 40px 10px 36px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                  disabled={submitting}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '12px',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-light)',
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {confirmPassword.length > 0 && (
                <div style={{ marginTop: '4px', fontSize: '11px', color: password === confirmPassword ? '#16A34A' : '#DC2626' }}>
                  {password === confirmPassword ? '✓ Passwords match' : '✗ Passwords do not match'}
                </div>
              )}
            </div>

            <button
              id="auth-reset-submit-btn"
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
                gap: '8px',
                marginBottom: '14px'
              }}
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <RefreshCw size={16} className="spin-animation" />
                  <span>Saving new password...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={16} />
                  <span>Update Password</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => handleModeChange('login')}
              style={{
                width: '100%',
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '8px'
              }}
            >
              <ArrowLeft size={14} />
              <span>Back to Sign In</span>
            </button>
          </form>
        )}

        {/* Footer Mode Switch */}
        {(mode === 'login' || mode === 'signup') && (
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
        )}
      </div>
    </div>
  );
};
