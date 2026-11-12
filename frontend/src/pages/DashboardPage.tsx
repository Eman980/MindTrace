import React, { useEffect, useState, useRef } from 'react';
import { api } from '../services/api';
import type { DashboardStats, Lecture } from '../types';
import {
  Video,
  Brain,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Upload,
  RefreshCw,
  FileQuestion,
  MoreVertical,
  Edit3,
  Trash2,
  ExternalLink,
  X,
  Check
} from 'lucide-react';

interface DashboardPageProps {
  setActiveTab: (tab: string) => void;
  onSelectLecture: (lectureId: number) => void;
  onReviewConcept?: (misconceptionId: number) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ setActiveTab, onSelectLecture }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 3-dot dropdown menu state
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Rename Modal State
  const [renameModalLecture, setRenameModalLecture] = useState<{ id: number; title: string } | null>(null);
  const [newTitle, setNewTitle] = useState<string>('');
  const [renameSaving, setRenameSaving] = useState<boolean>(false);
  const [renameError, setRenameError] = useState<string | null>(null);

  // Delete Modal State
  const [deleteModalLecture, setDeleteModalLecture] = useState<{ id: number; title: string } | null>(null);
  const [deleteDeleting, setDeleteDeleting] = useState<boolean>(false);

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

  // Close 3-dot menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);



  // Open rename modal
  const handleOpenRename = (lec: { id: number; title: string }) => {
    setOpenMenuId(null);
    setRenameModalLecture(lec);
    setNewTitle(lec.title);
    setRenameError(null);
  };

  // Save renamed title
  const handleSaveRename = async () => {
    if (!renameModalLecture) return;
    if (!newTitle.trim()) {
      setRenameError('Lecture title cannot be empty.');
      return;
    }
    setRenameSaving(true);
    setRenameError(null);
    try {
      await api.lectures.rename(renameModalLecture.id, newTitle.trim());
      setSuccessMessage(`Lecture renamed to "${newTitle.trim()}".`);
      setTimeout(() => setSuccessMessage(null), 3000);
      setRenameModalLecture(null);
      await loadStats();
    } catch (err: any) {
      setRenameError(err.message || 'Failed to rename lecture.');
    } finally {
      setRenameSaving(false);
    }
  };

  // Open delete single lecture confirmation
  const handleOpenDelete = (lec: { id: number; title: string }) => {
    setOpenMenuId(null);
    setDeleteModalLecture(lec);
  };

  // Confirm delete single lecture
  const handleConfirmDelete = async () => {
    if (!deleteModalLecture) return;
    setDeleteDeleting(true);
    try {
      await api.lectures.delete(deleteModalLecture.id);
      setSuccessMessage(`Deleted "${deleteModalLecture.title}".`);
      setTimeout(() => setSuccessMessage(null), 3000);
      setDeleteModalLecture(null);
      await loadStats();
    } catch (err: any) {
      setError(err.message || 'Failed to delete lecture.');
    } finally {
      setDeleteDeleting(false);
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
      <div className="section-header" style={{ marginBottom: '24px' }}>
        <div>
          <h1 className="section-title">Student Learning Dashboard</h1>
          <p className="section-subtitle">
            Evidence-based misconception tracking and lecture concept mastery.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
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

      {successMessage && (
        <div
          style={{
            padding: '12px 18px',
            marginBottom: '20px',
            borderRadius: 'var(--radius-md)',
            background: '#DCFCE7',
            color: '#16A34A',
            border: '1px solid #BBF7D0',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <Check size={16} />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="alert-banner alert-warning" style={{ marginBottom: '20px' }}>
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
            <span>View All Misconceptions</span>
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
              Upload your first lecture recording (.mp4, .mov, .webm, .wav, .mp3, .ogg) to start tracking learning concepts and persistent misconceptions.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button className="btn btn-primary btn-sm" onClick={() => setActiveTab('upload')}>
                <Upload size={14} />
                <span>Upload Lecture</span>
              </button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            {stats.recent_lectures.map((lec) => (
              <div key={lec.id} className="card card-hover" style={{ display: 'flex', flexDirection: 'column', position: 'relative' }}>
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

                  {/* Top-Right: Date & 3-dot menu */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-light)' }}>
                      {formatDate(lec.created_at)}
                    </span>

                    {/* 3-dot menu button */}
                    <div style={{ position: 'relative' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuId(openMenuId === lec.id ? null : lec.id);
                        }}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--text-muted)',
                          padding: '4px',
                          borderRadius: 'var(--radius-sm)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                        title="Lecture options"
                      >
                        <MoreVertical size={16} />
                      </button>

                      {/* Dropdown Menu */}
                      {openMenuId === lec.id && (
                        <div
                          ref={menuRef}
                          style={{
                            position: 'absolute',
                            top: '100%',
                            right: 0,
                            marginTop: '4px',
                            background: 'var(--bg-surface)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-md)',
                            boxShadow: 'var(--shadow-lg)',
                            zIndex: 100,
                            minWidth: '160px',
                            overflow: 'hidden',
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() => {
                              setOpenMenuId(null);
                              onSelectLecture(lec.id);
                            }}
                            style={{
                              width: '100%',
                              padding: '10px 14px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              background: 'transparent',
                              border: 'none',
                              fontSize: '13px',
                              color: 'var(--text-main)',
                              cursor: 'pointer',
                              textAlign: 'left',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-subtle)')}
                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                          >
                            <ExternalLink size={14} color="var(--primary-accent)" />
                            <span>Open Lecture</span>
                          </button>

                          <button
                            onClick={() => handleOpenRename(lec)}
                            style={{
                              width: '100%',
                              padding: '10px 14px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              background: 'transparent',
                              border: 'none',
                              fontSize: '13px',
                              color: 'var(--text-main)',
                              cursor: 'pointer',
                              textAlign: 'left',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-subtle)')}
                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                          >
                            <Edit3 size={14} color="var(--accent-purple)" />
                            <span>Rename Lecture</span>
                          </button>

                          <div style={{ height: '1px', background: 'var(--border-subtle)' }} />

                          <button
                            onClick={() => handleOpenDelete(lec)}
                            style={{
                              width: '100%',
                              padding: '10px 14px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              background: 'transparent',
                              border: 'none',
                              fontSize: '13px',
                              color: '#DC2626',
                              cursor: 'pointer',
                              textAlign: 'left',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = '#FEE2E2')}
                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                          >
                            <Trash2 size={14} color="#DC2626" />
                            <span>Delete Lecture</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
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

      {/* Rename Lecture Modal */}
      {renameModalLecture && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(11, 19, 43, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
            backdropFilter: 'blur(3px)',
          }}
          onClick={() => !renameSaving && setRenameModalLecture(null)}
        >
          <div
            className="card"
            style={{ maxWidth: '480px', width: '100%', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Edit3 size={18} color="var(--accent-purple)" />
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>Rename Lecture</h3>
              </div>
              <button
                onClick={() => setRenameModalLecture(null)}
                disabled={renameSaving}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            {renameError && (
              <div style={{ padding: '8px 12px', background: '#FEE2E2', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '13px', marginBottom: '12px' }}>
                {renameError}
              </div>
            )}

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                Lecture Title
              </label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                disabled={renameSaving}
                placeholder="Enter lecture title..."
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-strong)',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveRename();
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setRenameModalLecture(null)}
                disabled={renameSaving}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSaveRename}
                disabled={renameSaving || !newTitle.trim()}
              >
                {renameSaving ? 'Saving...' : 'Save Title'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Single Lecture Modal */}
      {deleteModalLecture && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(11, 19, 43, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
            backdropFilter: 'blur(3px)',
          }}
          onClick={() => !deleteDeleting && setDeleteModalLecture(null)}
        >
          <div
            className="card"
            style={{ maxWidth: '440px', width: '100%', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  background: '#FEE2E2',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#DC2626',
                }}
              >
                <Trash2 size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>Delete Lecture</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>This action cannot be undone.</p>
              </div>
            </div>

            <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.5, marginBottom: '20px' }}>
              Are you sure you want to delete <strong>"{deleteModalLecture.title}"</strong> and all its associated concepts, questions, checkpoints, and analytics?
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setDeleteModalLecture(null)}
                disabled={deleteDeleting}
              >
                Cancel
              </button>
              <button
                className="btn btn-sm"
                style={{ background: '#DC2626', color: '#FFFFFF', borderColor: '#DC2626' }}
                onClick={handleConfirmDelete}
                disabled={deleteDeleting}
              >
                {deleteDeleting ? 'Deleting...' : 'Delete Lecture'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
