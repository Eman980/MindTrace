import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import type { Lecture } from '../types';
import {
  Video,
  Upload,
  Trash2,
  Clock,
  Brain,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
  BookOpen,
  MoreVertical,
  Edit2,
  Check,
  X,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';

interface LecturesPageProps {
  setActiveTab: (tab: string) => void;
  onSelectLecture: (lectureId: number) => void;
}

export const LecturesPage: React.FC<LecturesPageProps> = ({ setActiveTab, onSelectLecture }) => {
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Active Dropdown state (lecture ID or null)
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);

  // Rename Modal state
  const [renameTarget, setRenameTarget] = useState<Lecture | null>(null);
  const [newTitle, setNewTitle] = useState<string>('');
  const [renaming, setRenaming] = useState<boolean>(false);
  const [renameError, setRenameError] = useState<string | null>(null);

  // Delete All Modal state
  const [showDeleteAllModal, setShowDeleteAllModal] = useState<boolean>(false);
  const [deletingAll, setDeletingAll] = useState<boolean>(false);

  // Delete Single Modal state
  const [deleteTarget, setDeleteTarget] = useState<Lecture | null>(null);
  const [deletingSingle, setDeletingSingle] = useState<boolean>(false);

  const menuRef = useRef<HTMLDivElement | null>(null);

  const loadLectures = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.lectures.list();
      setLectures(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load lectures.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLectures();
  }, []);

  // Close three-dot menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenuId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleOpenRename = (lec: Lecture) => {
    setOpenMenuId(null);
    setRenameTarget(lec);
    setNewTitle(lec.title);
    setRenameError(null);
  };

  const handleSaveRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameTarget) return;

    const trimmed = newTitle.trim();
    if (!trimmed) {
      setRenameError('Lecture title cannot be empty.');
      return;
    }

    setRenaming(true);
    setRenameError(null);
    try {
      const res = await api.lectures.rename(renameTarget.id, { title: trimmed });
      setLectures((prev) =>
        prev.map((l) => (l.id === renameTarget.id ? { ...l, title: res.title } : l))
      );
      setSuccessMessage(`Lecture renamed to '${res.title}' successfully.`);
      setRenameTarget(null);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setRenameError(err.message || 'Failed to rename lecture.');
    } finally {
      setRenaming(false);
    }
  };

  const handleConfirmDeleteSingle = async () => {
    if (!deleteTarget) return;
    setDeletingSingle(true);
    try {
      await api.lectures.delete(deleteTarget.id);
      setLectures((prev) => prev.filter((l) => l.id !== deleteTarget.id));
      setSuccessMessage(`Deleted '${deleteTarget.title}' and associated records.`);
      setDeleteTarget(null);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeletingSingle(false);
    }
  };

  const handleConfirmDeleteAll = async () => {
    setDeletingAll(true);
    try {
      const res = await api.lectures.deleteAll();
      setLectures([]);
      setShowDeleteAllModal(false);
      setSuccessMessage(res.message || 'All lectures and study data deleted successfully.');
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      alert(`Delete all failed: ${err.message}`);
    } finally {
      setDeletingAll(false);
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

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* Header with Title and Action buttons */}
      <div
        className="section-header"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <h1 className="section-title" style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy-800)', margin: 0 }}>
            Lecture Library & Management
          </h1>
          <p className="section-subtitle" style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Course recordings processed into timestamped concept segments, diagnostic checkpoints, and misconception tracking.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={loadLectures}
            className="btn btn-secondary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            disabled={loading}
            title="Refresh lecture list"
          >
            <RefreshCw size={14} className={loading ? 'spin-animation' : ''} />
            <span>Refresh</span>
          </button>

          <button
            id="lectures-upload-btn"
            className="btn btn-primary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={() => setActiveTab('upload')}
          >
            <Upload size={14} />
            <span>Upload New Lecture</span>
          </button>

          {lectures.length > 0 && (
            <button
              id="btn-delete-all-lectures"
              className="btn btn-secondary btn-sm"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: '#DC2626',
                borderColor: '#FECACA',
                background: '#FEF2F2'
              }}
              onClick={() => setShowDeleteAllModal(true)}
              title="Delete all lectures and associated study data"
            >
              <Trash2 size={14} color="#DC2626" />
              <span>Delete All Lectures</span>
            </button>
          )}
        </div>
      </div>

      {/* Success notification banner */}
      {successMessage && (
        <div
          style={{
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            background: '#DCFCE7',
            border: '1px solid #BBF7D0',
            borderRadius: 'var(--radius-md)',
            color: '#166534',
            fontSize: '13px',
            fontWeight: 600,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={18} color="#16A34A" />
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#166534' }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <RefreshCw size={28} className="spin-animation" style={{ color: 'var(--primary-accent)', margin: '0 auto 12px' }} />
          <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading course lectures...</div>
        </div>
      ) : error ? (
        <div className="alert-banner alert-warning">{error}</div>
      ) : lectures.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px', borderRadius: 'var(--radius-xl)' }}>
          <Video size={48} style={{ color: 'var(--text-light)', margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--navy-800)' }}>No Lectures in Your Library</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '480px', margin: '8px auto 24px', lineHeight: 1.6 }}>
            Upload your course recording (.mp4, .mov, .webm, .wav, .mp3, .ogg) to explore concept segmentation, diagnostic quizzes, and misconception tracking.
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              className="btn btn-primary btn-md"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 24px' }}
              onClick={() => setActiveTab('upload')}
            >
              <Upload size={16} />
              <span>Upload New Lecture</span>
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
          {lectures.map((lec) => (
            <div
              key={lec.id}
              className="card card-hover"
              style={{
                display: 'flex',
                flexDirection: 'column',
                borderRadius: 'var(--radius-lg)',
                position: 'relative',
                padding: '22px'
              }}
            >
              {/* Header row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--primary-accent)',
                      background: 'var(--accent-soft)',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-full)',
                    }}
                  >
                    {lec.course_code || 'CS101'}
                  </span>
                  {lec.is_demo && (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        color: 'var(--accent-purple)',
                        background: '#EEF2FF',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                      }}
                    >
                      Sample Demo
                    </span>
                  )}
                </div>

                {/* Right side: Date and Three-dot Menu */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', position: 'relative' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-light)', marginRight: '4px' }}>
                    {formatDate(lec.created_at)}
                  </span>

                  {/* Three-Dot Menu Trigger */}
                  <button
                    id={`lecture-menu-btn-${lec.id}`}
                    type="button"
                    style={{
                      background: openMenuId === lec.id ? 'var(--bg-subtle)' : 'none',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '4px 6px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                    title="Lecture options"
                    onClick={() => setOpenMenuId(openMenuId === lec.id ? null : lec.id)}
                  >
                    <MoreVertical size={16} />
                  </button>

                  {/* Three-Dot Dropdown Menu */}
                  {openMenuId === lec.id && (
                    <div
                      ref={menuRef}
                      style={{
                        position: 'absolute',
                        top: '28px',
                        right: 0,
                        background: '#FFFFFF',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        boxShadow: 'var(--shadow-lg)',
                        width: '160px',
                        zIndex: 50,
                        overflow: 'hidden',
                        padding: '4px 0'
                      }}
                    >
                      <button
                        type="button"
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          background: 'none',
                          border: 'none',
                          padding: '8px 14px',
                          fontSize: '13px',
                          color: 'var(--text-main)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-subtle)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                        onClick={() => {
                          setOpenMenuId(null);
                          onSelectLecture(lec.id);
                        }}
                      >
                        <Video size={14} color="var(--primary-accent)" />
                        <span>Open Lecture</span>
                      </button>

                      <button
                        id={`btn-rename-lecture-${lec.id}`}
                        type="button"
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          background: 'none',
                          border: 'none',
                          padding: '8px 14px',
                          fontSize: '13px',
                          color: 'var(--text-main)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-subtle)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                        onClick={() => handleOpenRename(lec)}
                      >
                        <Edit2 size={14} color="var(--accent-purple)" />
                        <span>Rename Lecture</span>
                      </button>

                      <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '4px 0' }} />

                      <button
                        id={`btn-delete-lecture-${lec.id}`}
                        type="button"
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          background: 'none',
                          border: 'none',
                          padding: '8px 14px',
                          fontSize: '13px',
                          color: '#DC2626',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = '#FEE2E2')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                        onClick={() => {
                          setOpenMenuId(null);
                          setDeleteTarget(lec);
                        }}
                      >
                        <Trash2 size={14} color="#DC2626" />
                        <span>Delete Lecture</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Title and description */}
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy-800)', marginBottom: '8px', lineHeight: 1.3 }}>
                {lec.title}
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', flex: 1, marginBottom: '16px', lineHeight: 1.5 }}>
                {lec.description || 'Course lecture recording with automatic concept segmentation.'}
              </p>

              {/* Metric badges */}
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
                  <div style={{ fontWeight: 700, color: 'var(--navy-800)' }}>
                    {formatDuration(lec.duration_seconds)}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Concepts</div>
                  <div style={{ fontWeight: 700, color: 'var(--navy-800)' }}>
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
                  <span style={{ color: 'var(--navy-800)' }}>{lec.progress_percentage}%</span>
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

              {/* Open button */}
              <button
                id={`btn-open-lecture-${lec.id}`}
                className="btn btn-primary"
                style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                onClick={() => onSelectLecture(lec.id)}
              >
                <Video size={16} />
                <span>Open Lecture & Checkpoints</span>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── RENAME LECTURE MODAL ────────────────────────────────────────────── */}
      {renameTarget && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(11, 19, 43, 0.65)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px'
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '480px',
              width: '100%',
              padding: '28px',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-xl)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Edit2 size={20} color="var(--primary-accent)" />
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy-800)', margin: 0 }}>
                  Rename Lecture
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setRenameTarget(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveRename}>
              {renameError && (
                <div style={{ padding: '10px 12px', background: '#FEE2E2', color: '#DC2626', borderRadius: 'var(--radius-md)', fontSize: '13px', marginBottom: '14px' }}>
                  {renameError}
                </div>
              )}

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--navy-800)', marginBottom: '6px' }}>
                  Lecture Title
                </label>
                <input
                  id="rename-lecture-input"
                  type="text"
                  className="input-field"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '14px' }}
                  placeholder="Enter new lecture title"
                  autoFocus
                  disabled={renaming}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setRenameTarget(null)}
                  disabled={renaming}
                >
                  Cancel
                </button>
                <button
                  id="btn-save-rename-lecture"
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={renaming || !newTitle.trim()}
                >
                  {renaming ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DELETE SINGLE CONFIRMATION MODAL ─────────────────────────────────── */}
      {deleteTarget && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(11, 19, 43, 0.65)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px'
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '460px',
              width: '100%',
              padding: '28px',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-xl)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-md)', background: '#FEE2E2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Trash2 size={20} color="#DC2626" />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy-800)', margin: 0 }}>
                Delete Lecture?
              </h3>
            </div>

            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '20px' }}>
              Are you sure you want to delete <strong>'{deleteTarget.title}'</strong>? This will permanently remove its transcript segments, concept checkpoints, and associated student quiz attempts.
            </p>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setDeleteTarget(null)}
                disabled={deletingSingle}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-delete-single"
                type="button"
                className="btn btn-primary btn-sm"
                style={{ background: '#DC2626', borderColor: '#DC2626' }}
                onClick={handleConfirmDeleteSingle}
                disabled={deletingSingle}
              >
                {deletingSingle ? 'Deleting...' : 'Yes, Delete Lecture'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── DELETE ALL LECTURES CONFIRMATION MODAL ───────────────────────────── */}
      {showDeleteAllModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(11, 19, 43, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px'
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '500px',
              width: '100%',
              padding: '30px',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-xl)',
              border: '1px solid #FECACA'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: 'var(--radius-md)', background: '#FEE2E2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <AlertTriangle size={24} color="#DC2626" />
              </div>
              <div>
                <h3 style={{ fontSize: '19px', fontWeight: 800, color: '#B91C1C', margin: 0 }}>
                  Delete All Lectures?
                </h3>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  This action affects all {lectures.length} lecture records in your library
                </div>
              </div>
            </div>

            <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius-md)', padding: '14px', marginBottom: '18px' }}>
              <p style={{ fontSize: '13px', color: '#991B1B', lineHeight: 1.5, margin: 0 }}>
                <strong>Warning:</strong> This operation will permanently remove all your uploaded lecture videos, generated transcript segments, identified concept milestones, diagnostic checkpoints, and student misconception tracking records.
              </p>
              <div style={{ fontSize: '12px', color: '#B91C1C', marginTop: '6px' }}>
                ✓ Your student account and login credentials will <strong>not</strong> be deleted.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setShowDeleteAllModal(false)}
                disabled={deletingAll}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-delete-all"
                type="button"
                className="btn btn-primary btn-sm"
                style={{ background: '#DC2626', borderColor: '#DC2626', display: 'flex', alignItems: 'center', gap: '6px' }}
                onClick={handleConfirmDeleteAll}
                disabled={deletingAll}
              >
                {deletingAll ? (
                  <>
                    <RefreshCw size={14} className="spin-animation" />
                    <span>Deleting all data...</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={14} />
                    <span>Yes, Delete All My Lectures</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
