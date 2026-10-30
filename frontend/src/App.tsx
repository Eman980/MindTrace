import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LandingPage } from './pages/LandingPage';
import { AuthPage } from './pages/AuthPage';
import { DashboardPage } from './pages/DashboardPage';
import { LecturesPage } from './pages/LecturesPage';
import { UploadPage } from './pages/UploadPage';
import { PlayerPage } from './pages/PlayerPage';
import { MisconceptionsPage } from './pages/MisconceptionsPage';
import { LedgerPage } from './pages/LedgerPage';
import { ReviewPage } from './pages/ReviewPage';
import { ProgressPage } from './pages/ProgressPage';
import { FYP2RoadmapPage } from './pages/FYP2RoadmapPage';
import { api } from './services/api';

// ─── Inner app that consumes AuthContext ──────────────────────────────────────
const AppInner: React.FC = () => {
  const { user, loading } = useAuth();

  // Tab-based navigation state
  const [activeTab, setActiveTab] = useState<string>('landing');

  // For the lecture player — which lecture is open
  const [selectedLectureId, setSelectedLectureId] = useState<number | null>(null);

  // For the misconception review — which misconception is open
  const [selectedMisconceptionId, setSelectedMisconceptionId] = useState<number | null>(null);

  // Live unresolved count for the Navbar badge
  const [unresolvedCount, setUnresolvedCount] = useState<number>(0);

  // Once auth loads, redirect appropriately
  useEffect(() => {
    if (!loading) {
      if (user) {
        // Only redirect to dashboard if we're still on unauthenticated tabs
        if (activeTab === 'landing' || activeTab === 'login' || activeTab === 'signup') {
          setActiveTab('dashboard');
        }
      }
    }
  }, [user, loading]);

  // Refresh the unresolved badge whenever we're on a relevant tab
  useEffect(() => {
    if (user) {
      api.misconceptions
        .stats()
        .then((s) => setUnresolvedCount(s.unresolved))
        .catch(() => {});
    }
  }, [user, activeTab]);

  // ── Navigation helpers ────────────────────────────────────────────────────
  const handleSelectLecture = (lectureId: number) => {
    setSelectedLectureId(lectureId);
    setActiveTab('player');
  };


  const handlePlayerBack = () => {
    setSelectedLectureId(null);
    setActiveTab('lectures');
  };

  const handleReviewConcept = (misconceptionId: number) => {
    setSelectedMisconceptionId(misconceptionId);
    setActiveTab('review');
  };

  const handleReviewBack = () => {
    setSelectedMisconceptionId(null);
    setActiveTab('misconceptions');
  };

  const handleLectureCreated = (lectureId: number) => {
    setSelectedLectureId(lectureId);
    setActiveTab('player');
  };

  // ── Loading screen ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
          background: 'var(--bg-main)',
        }}
      >
        <div
          style={{
            width: '48px',
            height: '48px',
            border: '3px solid var(--border-subtle)',
            borderTopColor: 'var(--accent-purple)',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <div style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: 500 }}>
          Initializing MindTrace...
        </div>
      </div>
    );
  }

  // ── Unauthenticated pages (Landing, Login, Signup) ─────────────────────────
  if (!user && (activeTab === 'login' || activeTab === 'signup')) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg-main)', display: 'flex', flexDirection: 'column' }}>
        <Navbar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          unresolvedCount={unresolvedCount}
        />
        <AuthPage
          initialMode={activeTab === 'signup' ? 'signup' : 'login'}
          onSuccess={() => setActiveTab('dashboard')}
          onSwitchMode={(mode) => setActiveTab(mode)}
        />
      </div>
    );
  }

  // ── Router dispatch ────────────────────────────────────────────────────────
  const renderPage = () => {
    switch (activeTab) {
      case 'landing':
        return <LandingPage setActiveTab={setActiveTab} />;

      case 'dashboard':
        return (
          <DashboardPage
            setActiveTab={setActiveTab}
            onSelectLecture={handleSelectLecture}
            onReviewConcept={handleReviewConcept}
          />
        );

      case 'lectures':
        return (
          <LecturesPage
            setActiveTab={setActiveTab}
            onSelectLecture={handleSelectLecture}
          />
        );

      case 'upload':
        return (
          <UploadPage
            setActiveTab={setActiveTab}
            onLectureCreated={handleLectureCreated}
          />
        );

      case 'player':
        if (!selectedLectureId) {
          setActiveTab('lectures');
          return null;
        }
        return (
          <PlayerPage
            lectureId={selectedLectureId}
            onBack={handlePlayerBack}
            onNavigateToMisconceptions={() => setActiveTab('misconceptions')}
          />
        );

      case 'misconceptions':
        return <MisconceptionsPage onReviewConcept={handleReviewConcept} />;

      case 'ledger':
        return (
          <LedgerPage
            onGoToLecture={handleSelectLecture}
            onReviewConcept={handleReviewConcept}
          />
        );

      case 'review':
        if (!selectedMisconceptionId) {
          setActiveTab('misconceptions');
          return null;
        }
        return (
          <ReviewPage
            misconceptionId={selectedMisconceptionId}
            onBack={handleReviewBack}
          />
        );

      case 'progress':
        return <ProgressPage onGoToLecture={handleSelectLecture} />;

      case 'fyp2':
        return <FYP2RoadmapPage />;

      default:
        return <LandingPage setActiveTab={setActiveTab} />;
    }
  };

  // Pages that render without the top-level page padding (full-screen layouts)
  const fullscreenTabs = ['player'];
  const isFullscreen = fullscreenTabs.includes(activeTab);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', display: 'flex', flexDirection: 'column' }}>
      {/* Navbar — always visible */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        unresolvedCount={unresolvedCount}
      />

      {/* Page content */}
      <main
        style={{
          flex: 1,
          paddingTop: isFullscreen ? '0' : '24px',
          paddingBottom: isFullscreen ? '0' : '48px',
          paddingLeft: isFullscreen ? '0' : '20px',
          paddingRight: isFullscreen ? '0' : '20px',
          maxWidth: isFullscreen ? 'none' : '1200px',
          margin: '0 auto',
          width: '100%',
          boxSizing: 'border-box',
        }}
      >
        {renderPage()}
      </main>
    </div>
  );
};

// ─── Root App with Providers ──────────────────────────────────────────────────
const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
};

export default App;
