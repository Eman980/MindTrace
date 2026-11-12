import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Brain,
  LayoutDashboard,
  Video,
  Upload,
  AlertTriangle,
  TrendingUp,
  LogOut,
  User as UserIcon,
  BookOpen,
  ArrowRight,
  Menu,
  X
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleNavigate = (tab: string) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <a
          href="#dashboard"
          className="brand-link"
          onClick={(e) => {
            e.preventDefault();
            handleNavigate(user ? 'dashboard' : 'landing');
          }}
        >
          <div className="brand-logo-icon">
            <Brain size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="brand-title">MindTrace</span>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: 'var(--accent-soft)',
                  color: 'var(--primary-accent)',
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                }}
              >
                AI Platform
              </span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500, lineHeight: 1, marginTop: '2px' }}>
              Persistent Misconception Tracking
            </div>
          </div>
        </a>

        {/* Desktop Navigation */}
        {user ? (
          <nav className="nav-desktop">
            <ul className="nav-links">
              <li>
                <button
                  id="nav-dashboard-btn"
                  className={`nav-item-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
                  onClick={() => handleNavigate('dashboard')}
                >
                  <LayoutDashboard size={16} />
                  <span>Dashboard</span>
                </button>
              </li>
              <li>
                <button
                  id="nav-lectures-btn"
                  className={`nav-item-btn ${activeTab === 'lectures' ? 'active' : ''}`}
                  onClick={() => handleNavigate('lectures')}
                >
                  <Video size={16} />
                  <span>My Lectures</span>
                </button>
              </li>
              <li>
                <button
                  id="nav-upload-btn"
                  className={`nav-item-btn ${activeTab === 'upload' ? 'active' : ''}`}
                  onClick={() => handleNavigate('upload')}
                >
                  <Upload size={16} />
                  <span>Upload</span>
                </button>
              </li>
              <li>
                <button
                  id="nav-misconceptions-btn"
                  className={`nav-item-btn ${activeTab === 'misconceptions' ? 'active' : ''}`}
                  onClick={() => handleNavigate('misconceptions')}
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
                  onClick={() => handleNavigate('ledger')}
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
                  onClick={() => handleNavigate('progress')}
                >
                  <TrendingUp size={16} />
                  <span>Progress</span>
                </button>
              </li>
            </ul>
          </nav>
        ) : (
          <nav className="nav-desktop">
            <ul className="nav-links">
              <li>
                <button
                  className={`nav-item-btn ${activeTab === 'landing' ? 'active' : ''}`}
                  onClick={() => handleNavigate('landing')}
                >
                  Home
                </button>
              </li>
            </ul>
          </nav>
        )}

        {/* Desktop Auth Actions */}
        <div className="nav-auth-actions nav-auth-desktop">
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
                  handleNavigate('landing');
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
                onClick={() => handleNavigate('login')}
              >
                Sign In
              </button>
              <button
                id="btn-signup-modal"
                className="btn btn-primary btn-sm"
                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                onClick={() => handleNavigate('signup')}
              >
                <span>Get Started</span>
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Toggle Button */}
        <button
          id="btn-mobile-menu-toggle"
          className="nav-mobile-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          title="Toggle Navigation Menu"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="nav-mobile-menu open">
          {user ? (
            <>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 12px',
                  background: 'var(--bg-subtle)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '6px',
                }}
              >
                <UserIcon size={16} color="var(--primary-accent)" />
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy-800)' }}>
                  {user.full_name}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                  {user.email}
                </span>
              </div>

              <button
                className={`nav-item-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
                onClick={() => handleNavigate('dashboard')}
              >
                <LayoutDashboard size={16} />
                <span>Dashboard</span>
              </button>

              <button
                className={`nav-item-btn ${activeTab === 'lectures' ? 'active' : ''}`}
                onClick={() => handleNavigate('lectures')}
              >
                <Video size={16} />
                <span>My Lectures</span>
              </button>

              <button
                className={`nav-item-btn ${activeTab === 'upload' ? 'active' : ''}`}
                onClick={() => handleNavigate('upload')}
              >
                <Upload size={16} />
                <span>Upload Lecture</span>
              </button>

              <button
                className={`nav-item-btn ${activeTab === 'misconceptions' ? 'active' : ''}`}
                onClick={() => handleNavigate('misconceptions')}
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
                      marginLeft: 'auto',
                    }}
                  >
                    {unresolvedCount}
                  </span>
                )}
              </button>

              <button
                className={`nav-item-btn ${activeTab === 'ledger' ? 'active' : ''}`}
                onClick={() => handleNavigate('ledger')}
              >
                <BookOpen size={16} />
                <span>Misconception Ledger</span>
              </button>

              <button
                className={`nav-item-btn ${activeTab === 'progress' ? 'active' : ''}`}
                onClick={() => handleNavigate('progress')}
              >
                <TrendingUp size={16} />
                <span>Learning Progress</span>
              </button>

              <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '8px 0' }} />

              <button
                className="btn btn-secondary btn-sm"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => {
                  logout();
                  handleNavigate('landing');
                }}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </>
          ) : (
            <>
              <button
                className={`nav-item-btn ${activeTab === 'landing' ? 'active' : ''}`}
                onClick={() => handleNavigate('landing')}
              >
                Home
              </button>
              <button
                className="btn btn-secondary btn-sm"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => handleNavigate('login')}
              >
                Sign In
              </button>
              <button
                className="btn btn-primary btn-sm"
                style={{ width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: '6px' }}
                onClick={() => handleNavigate('signup')}
              >
                <span>Get Started</span>
                <ArrowRight size={14} />
              </button>
            </>
          )}
        </div>
      )}
    </header>
  );
};
