import React, { useState, useEffect } from 'react';
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
  BookOpen
} from 'lucide-react';

interface LecturesPageProps {
  setActiveTab: (tab: string) => void;
  onSelectLecture: (lectureId: number) => void;
}

export const LecturesPage: React.FC<LecturesPageProps> = ({ setActiveTab, onSelectLecture }) => {
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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

  const handleDelete = async (id: number, title: string) => {
    if (!confirm(`Are you sure you want to delete '${title}'? This will remove all associated concepts, checkpoints, and attempt history.`)) {
      return;
    }
    try {
      await api.lectures.delete(id);
      setLectures(lectures.filter((l) => l.id !== id));
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
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
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="section-title" style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy-800)', margin: 0 }}>
            My Uploaded Lectures
          </h1>
          <p className="section-subtitle" style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Course recordings processed into timestamped concept segments, diagnostic checkpoints, and misconception tracking.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={loadLectures}
            className="btn btn-secondary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
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
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <RefreshCw size={28} className="animate-spin" style={{ color: 'var(--primary-accent)', margin: '0 auto 12px' }} />
          <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading course lectures...</div>
        </div>
      ) : error ? (
        <div className="alert-banner alert-warning">{error}</div>
      ) : lectures.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px', borderRadius: 'var(--radius-xl)' }}>
          <Video size={48} style={{ color: 'var(--text-light)', margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--navy-800)' }}>No Lectures Uploaded Yet</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '480px', margin: '8px auto 24px', lineHeight: 1.6 }}>
            Upload your first course video or audio recording (.mp4, .mov, .webm, .mp3, .wav, .m4a, .ogg). MindTrace will automatically
            transcribe the media, partition it into concept milestones, and generate diagnostic checkpoints.
          </p>
          <button
            className="btn btn-primary btn-md"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 24px' }}
            onClick={() => setActiveTab('upload')}
          >
            <Upload size={16} />
            <span>Upload Your First Lecture</span>
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
          {lectures.map((lec) => (
            <div key={lec.id} className="card card-hover" style={{ display: 'flex', flexDirection: 'column', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
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
                    {lec.course_code}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-light)' }}>
                    {formatDate(lec.created_at)}
                  </span>
                  <button
                    style={{ background: 'none', border: 'none', color: 'var(--text-light)', cursor: 'pointer', padding: '4px' }}
                    title="Delete Lecture"
                    onClick={() => handleDelete(lec.id, lec.title)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy-800)', marginBottom: '8px', lineHeight: 1.3 }}>
                {lec.title}
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', flex: 1, marginBottom: '16px', lineHeight: 1.5 }}>
                {lec.description || 'Course lecture recording with automatic concept segmentation.'}
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

              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Progress</span>
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
    </div>
  );
};
