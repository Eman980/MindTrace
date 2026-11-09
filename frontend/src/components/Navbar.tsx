import React from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Brain,
  LayoutDashboard,
  Video,
  Upload,
  AlertTriangle,
  TrendingUp,
  HelpCircle,
  LogOut,
  User as UserIcon,
  BookOpen,
  ArrowRight
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  unresolvedCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  unresolvedCount = 0,
}) => {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <a
          href="#dashboard"
          className="brand-link"
          onClick={(e) => {
            e.preventDefault();
            setActiveTab(user ? 'dashboard' : 'landing');
          }}
        >
          <div className="brand-logo-icon">
            <Brain size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="brand-title">MindTrace</span>
              <span style={{
                fontSize: '10px',
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'var(--accent-soft)',
                color: 'var(--primary-accent)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase'
              }}>
                AI Platform
              </span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500, lineHeight: 1, marginTop: '2px' }}>
              Persistent Misconception Tracking
            </div>
          </div>
        </a>

        {user ? (
          <nav>
            <ul className="nav-links">
              <li>
                <button
                  id="nav-dashboard-btn"
                  className={`nav-item-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
                  onClick={() => setActiveTab('dashboard')}
                >
                  <LayoutDashboard size={16} />
                  <span>Dashboard</span>
                </button>
              </li>
              <li>
                <button
                  id="nav-lectures-btn"
                  className={`nav-item-btn ${activeTab === 'lectures' ? 'active' : ''}`}
                  onClick={() => setActiveTab('lectures')}
                >
                  <Video size={16} />
                  <span>My Lectures</span>
                </button>
              </li>
              <li>
                <button
                  id="nav-upload-btn"
                  className={`nav-item-btn ${activeTab === 'upload' ? 'active' : ''}`}
                  onClick={() => setActiveTab('upload')}
                >
                  <Upload size={16} />
                  <span>Upload</span>
                </button>
              </li>
              <li>
                <button
                  id="nav-misconceptions-btn"
                  className={`nav-item-btn ${activeTab === 'misconceptions' ? 'active' : ''}`}
                  onClick={() => setActiveTab('misconceptions')}
                >
                  <AlertTriangle size={16} />
                  <span>Misconceptions</span>
                  {unresolvedCount > 0 && (
                    <span
                      style={{
                        background: 'var(--priority-high-bg)',
                        color: 'var(--priority-high-text)',
                        fontSize: '11px',
                        padding: '1px 6px',
                        borderRadius: '9999px',
                        fontWeight: 700,
                      }}
                    >
                      {unresolvedCount}
                    </span>
                  )}
                </button>
              </li>
              <li>
                <button
                  id="nav-ledger-btn"
                  className={`nav-item-btn ${activeTab === 'ledger' ? 'active' : ''}`}
                  onClick={() => setActiveTab('ledger')}
                  title="Evidence-based Misconception Ledger"
                >
                  <BookOpen size={16} />
                  <span>Ledger</span>
                </button>
              </li>
              <li>
                <button
                  id="nav-progress-btn"
                  className={`nav-item-btn ${activeTab === 'progress' ? 'active' : ''}`}
                  onClick={() => setActiveTab('progress')}
                >
                  <TrendingUp size={16} />
                  <span>Progress</span>
                </button>
              </li>
            </ul>
          </nav>
        ) : (
          <nav>
            <ul className="nav-links">
              <li>
                <button
                  className={`nav-item-btn ${activeTab === 'landing' ? 'active' : ''}`}
                  onClick={() => setActiveTab('landing')}
                >
                  Home
                </button>
              </li>
            </ul>
          </nav>
        )}

        <div className="nav-auth-actions">
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 12px',
                  background: 'var(--bg-subtle)',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--navy-800)',
                }}
              >
                <UserIcon size={14} />
                <span>{user.full_name}</span>
              </div>
              <button
                id="btn-logout"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  logout();
                  setActiveTab('landing');
                }}
                title="Sign Out"
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                id="btn-login-modal"
                className="btn btn-secondary btn-sm"
                onClick={() => setActiveTab('login')}
              >
                Sign In
              </button>
              <button
                id="btn-signup-modal"
                className="btn btn-primary btn-sm"
                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                onClick={() => setActiveTab('signup')}
              >
                <span>Get Started</span>
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
