import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { CanonicalConceptProgress } from '../types';
import { Brain, RefreshCw, Video as VideoIcon, ArrowRight } from 'lucide-react';

interface ProgressPageProps {
  onGoToLecture?: (lectureId: number) => void;
}

const formatTime = (secs: number) => {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}m ${s}s`;
};

export const ProgressPage: React.FC<ProgressPageProps> = ({ onGoToLecture }) => {
  const [concepts, setConcepts] = useState<CanonicalConceptProgress[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadProgress = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.concepts.getCanonicalProgress();
      setConcepts(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load concept progress.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProgress();
  }, []);

  return (
    <div style={{ paddingBottom: '60px' }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Concept Progress</h1>
          <p className="section-subtitle">
            Your understanding of each concept, based on your quiz answers across all videos.
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <RefreshCw size={28} className="spin-animation" style={{ color: 'var(--accent-purple)' }} />
          <div style={{ marginTop: '12px', color: 'var(--text-muted)' }}>Calculating concept progress...</div>
        </div>
      ) : error ? (
        <div className="alert-banner alert-warning">{error}</div>
      ) : concepts.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <Brain size={44} color="var(--accent-purple)" style={{ margin: '0 auto 14px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 800 }}>No Concepts Tracked Yet</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Upload a lecture and answer its questions to start tracking your progress.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {concepts.map((c) => {
            const isMastered = c.status === 'Mastered';
            const isNeedsAttention = c.status === 'Needs Attention';
            const isImproving = c.status === 'Improving';
            const hasAttempts = c.questions_attempted > 0;
            const videoNames = Array.from(new Set(c.videos.map((v) => v.lecture_title)));

            return (
              <div key={c.id} className="card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
                  <div>
                    <span
                      className={`badge ${
                        isMastered ? 'badge-resolved' : isNeedsAttention ? 'badge-high' : isImproving ? 'badge-improving' : 'badge-low'
                      }`}
                    >
                      {c.status}
                    </span>
                    <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)', marginTop: '8px' }}>
                      {c.name}
                    </h3>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        marginTop: '4px',
                        fontSize: '13px',
                        color: 'var(--text-muted)',
                        fontWeight: 600,
                      }}
                    >
                      <VideoIcon size={13} />
                      <span>{videoNames.join(' • ')}</span>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div
                      style={{
                        fontSize: '24px',
                        fontWeight: 800,
                        color: !hasAttempts ? 'var(--text-muted)' : isNeedsAttention ? '#DC2626' : isMastered ? '#16A34A' : 'var(--primary-accent)',
                      }}
                    >
                      {hasAttempts ? `${c.understanding_percentage}%` : '—'}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Understanding</div>
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{ height: '8px', background: 'var(--bg-subtle)', borderRadius: '9999px', overflow: 'hidden', marginBottom: '16px' }}>
                  <div
                    style={{
                      width: `${hasAttempts ? c.understanding_percentage : 0}%`,
                      height: '100%',
                      background: isNeedsAttention ? '#EF4444' : isMastered ? '#22C55E' : 'linear-gradient(90deg, var(--accent-purple), var(--primary-accent))',
                      borderRadius: '9999px',
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>

                {/* Stats */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '12px',
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 16px',
                    fontSize: '13px',
                    marginBottom: '16px',
                  }}
                >
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Questions Attempted</div>
                    <div style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>{c.questions_attempted}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Answered Correctly</div>
                    <div style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>{c.questions_correct}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Open Misconceptions</div>
                    <div style={{ fontWeight: 700, color: c.open_misconceptions > 0 ? '#DC2626' : 'var(--primary-navy)' }}>
                      {c.open_misconceptions}
                    </div>
                  </div>
                </div>

                {/* Videos where this concept appears */}
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Appears in {c.videos.length} {c.videos.length === 1 ? 'video' : 'videos'}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {c.videos.map((v) => (
                    <button
                      key={v.concept_id}
                      onClick={() => onGoToLecture && onGoToLecture(v.lecture_id)}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '10px 14px',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        background: 'white',
                        cursor: 'pointer',
                        textAlign: 'left',
                        width: '100%',
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: 'var(--primary-navy)' }}>
                        <VideoIcon size={14} />
                        {v.lecture_title}
                        <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono', fontSize: '11px' }}>
                          {formatTime(v.start_time)} - {formatTime(v.end_time)}
                        </span>
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                        {v.questions_attempted > 0
                          ? `${v.questions_correct} of ${v.questions_attempted} correct`
                          : 'Not attempted'}
                        <ArrowRight size={14} />
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};