import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { DashboardStats } from '../types';
import {
  Video,
  Brain,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Upload,
  RefreshCw,
  PlusCircle,
  FileQuestion
} from 'lucide-react';

interface DashboardPageProps {
  setActiveTab: (tab: string) => void;
  onSelectLecture: (lectureId: number) => void;
  onReviewConcept?: (misconceptionId: number) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ setActiveTab, onSelectLecture }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [seeding, setSeeding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.dashboard.getStats();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      await api.demo.seed();
      await loadStats();
    } catch (err: any) {
      alert(`Could not seed demo lecture: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs.toString().padStart(2, '0')}s`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div style={{ padding: '60px 0', textAlign: 'center' }}>
        <RefreshCw size={32} className="spin-animation" style={{ color: 'var(--accent-purple)' }} />
        <div style={{ marginTop: '16px', fontSize: '15px', color: 'var(--text-muted)' }}>
          Loading your learning metrics...
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header with Title and Action buttons */}
      <div className="section-header">
        <div>
          <h1 className="section-title">Student Learning Dashboard</h1>
          <p className="section-subtitle">
            Evidence-based misconception tracking and lecture concept mastery.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            id="dash-seed-demo-btn"
            className="btn btn-secondary btn-sm"
            onClick={handleSeedDemo}
            disabled={seeding}
            title="Reloads the standard Functions demo lecture"
          >
            <Sparkles size={14} color="var(--accent-purple)" />
            <span>{seeding ? 'Seeding...' : 'Load Sample Lecture'}</span>
          </button>
          <button
            id="dash-upload-btn"
            className="btn btn-primary btn-sm"
            onClick={() => setActiveTab('upload')}
          >
            <Upload size={14} />
            <span>Upload New Lecture</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-banner alert-warning">
          <span>{error}</span>
        </div>
      )}

      {/* 5 Core Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: '#EEF2FF', color: '#4F46E5' }}>
            <Video size={24} />
          </div>
          <div>
            <div className="metric-num">{stats?.total_lectures || 0}</div>
            <div className="metric-label">Total Lectures</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: '#E0F2FE', color: '#0284C7' }}>
            <Brain size={24} />
          </div>
          <div>
            <div className="metric-num">{stats?.concepts_identified || 0}</div>
            <div className="metric-label">Concepts Identified</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: '#FEF3C7', color: '#D97706' }}>
            <AlertTriangle size={24} />
          </div>
          <div>
            <div className="metric-num">{stats?.misconceptions_detected || 0}</div>
            <div className="metric-label">Misconceptions Detected</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: '#FEE2E2', color: '#DC2626' }}>
            <FileQuestion size={24} />
          </div>
          <div>
            <div className="metric-num">{stats?.unresolved_concepts || 0}</div>
            <div className="metric-label">Unresolved Concepts</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box" style={{ background: '#DCFCE7', color: '#16A34A' }}>
            <CheckCircle2 size={24} />
          </div>
          <div>
            <div className="metric-num">{stats?.concepts_improved || 0}</div>
            <div className="metric-label">Concepts Improved</div>
          </div>
        </div>
      </div>

      {/* Misconception Priority Profile */}
      <div className="card" style={{ marginBottom: '36px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--primary-navy)' }}>
              Misconception Priority Profile
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Active tracking across detected high, medium, and low severity conceptual friction points.
            </p>
          </div>
          <button
            id="view-all-misconceptions-btn"
            className="btn btn-secondary btn-sm"
            onClick={() => setActiveTab('misconceptions')}
          >
            <span>View All</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          <div
            style={{
              background: 'var(--priority-high-bg)',
              border: '1px solid var(--priority-high-border)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--priority-high-text)', textTransform: 'uppercase' }}>
              High Priority
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--priority-high-text)', marginTop: '4px' }}>
              {stats?.misconception_summary.high_priority || 0}
            </div>
            <div style={{ fontSize: '12px', color: '#991B1B', marginTop: '2px' }}>
              Require immediate conceptual review
            </div>
          </div>

          <div
            style={{
              background: 'var(--priority-med-bg)',
              border: '1px solid var(--priority-med-border)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--priority-med-text)', textTransform: 'uppercase' }}>
              Medium Priority
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--priority-med-text)', marginTop: '4px' }}>
              {stats?.misconception_summary.medium_priority || 0}
            </div>
            <div style={{ fontSize: '12px', color: '#92400E', marginTop: '2px' }}>
              Multiple friction points detected
            </div>
          </div>

          <div
            style={{
              background: 'var(--priority-low-bg)',
              border: '1px solid var(--priority-low-border)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--priority-low-text)', textTransform: 'uppercase' }}>
              Low Priority
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--priority-low-text)', marginTop: '4px' }}>
              {stats?.misconception_summary.low_priority || 0}
            </div>
            <div style={{ fontSize: '12px', color: '#1E40AF', marginTop: '2px' }}>
              Minor checkpoint slip
            </div>
          </div>

          <div
            style={{
              background: 'var(--status-resolved-bg)',
              border: '1px solid var(--status-resolved-border)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--status-resolved-text)', textTransform: 'uppercase' }}>
              Resolved
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--status-resolved-text)', marginTop: '4px' }}>
              {stats?.misconception_summary.resolved || 0}
            </div>
            <div style={{ fontSize: '12px', color: '#166534', marginTop: '2px' }}>
              Successfully verified in review
            </div>
          </div>
        </div>
      </div>

      {/* Recent Lectures Section */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <div>
            <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--primary-navy)' }}>Recent Lectures</h2>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
              Click 'Continue Learning' to open the interactive concept timeline player.
            </p>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setActiveTab('lectures')}
          >
            <span>View All Lectures</span>
            <ArrowRight size={14} />
          </button>
        </div>

        {(!stats?.recent_lectures || stats.recent_lectures.length === 0) ? (
          <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <Video size={40} style={{ color: 'var(--text-light)', marginBottom: '12px' }} />
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--primary-navy)' }}>
              No lectures uploaded yet
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '440px', margin: '6px auto 20px' }}>
              Upload your first lecture recording or load the built-in 'Introduction to Functions' sample lecture.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button className="btn btn-accent btn-sm" onClick={handleSeedDemo} disabled={seeding}>
                <Sparkles size={14} />
                <span>Load Sample Lecture</span>
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => setActiveTab('upload')}>
                <Upload size={14} />
                <span>Upload Lecture</span>
              </button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            {stats.recent_lectures.map((lec) => (
              <div key={lec.id} className="card card-hover" style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        color: 'var(--accent-purple)',
                        background: 'var(--accent-soft)',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                      }}
                    >
                      {lec.course_code}
                    </span>
                    {lec.is_demo && (
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          color: '#0369A1',
                          background: '#E0F2FE',
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-full)',
                          marginLeft: '6px',
                        }}
                      >
                        Sample Demo
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--text-light)' }}>
                    {formatDate(lec.created_at)}
                  </span>
                </div>

                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)', marginBottom: '8px', lineHeight: 1.3 }}>
                  {lec.title}
                </h3>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5, flex: 1, marginBottom: '16px' }}>
                  {lec.description || 'Lecture recording covering core course concepts and practice checkpoints.'}
                </p>

                <div
                  style={{
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '13px',
                    marginBottom: '16px',
                  }}
                >
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Duration</div>
                    <div style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>
                      {formatDuration(lec.duration_seconds)}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Concepts</div>
                    <div style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>
                      {lec.concepts_count}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Unresolved</div>
                    <div
                      style={{
                        fontWeight: 700,
                        color: lec.unresolved_count > 0 ? 'var(--priority-high-text)' : '#16A34A',
                      }}
                    >
                      {lec.unresolved_count}
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Mastery Progress</span>
                    <span style={{ color: 'var(--primary-navy)' }}>{lec.progress_percentage}%</span>
                  </div>
                  <div style={{ height: '6px', background: 'var(--border-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${lec.progress_percentage}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, var(--accent-purple), var(--primary-accent))',
                        borderRadius: '9999px',
                      }}
                    />
                  </div>
                </div>

                <button
                  id={`btn-continue-lecture-${lec.id}`}
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                  onClick={() => onSelectLecture(lec.id)}
                >
                  <Video size={16} />
                  <span>Continue Learning</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
