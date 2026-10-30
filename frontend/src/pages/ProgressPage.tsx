import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { Concept } from '../types';
import {
  TrendingUp,
  Brain,
  CheckCircle2,
  Clock,
  RotateCcw,
  RefreshCw,
  Award,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';

interface ProgressPageProps {
  onGoToLecture?: (lectureId: number) => void;
}

export const ProgressPage: React.FC<ProgressPageProps> = ({ onGoToLecture }) => {
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadProgress = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.concepts.getProgress();
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

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}m ${s}s`;
  };

  return (
    <div style={{ paddingBottom: '60px' }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Concept-Level Learning Progress</h1>
          <p className="section-subtitle">
            Longitudinal telemetry of understanding percentages, checkpoint correctness, and replay friction.
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
            Upload your course lecture recordings to start tracking concept mastery and friction points.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {concepts.map((concept) => {
            const isMastered = concept.status === 'Mastered';
            const isNeedsAttention = concept.status === 'Needs Attention';
            const isImproving = concept.status === 'Improving';

            return (
              <div key={concept.id} className="card card-hover" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span
                        className={`badge ${
                          isMastered
                            ? 'badge-resolved'
                            : isNeedsAttention
                            ? 'badge-high'
                            : isImproving
                            ? 'badge-improving'
                            : 'badge-low'
                        }`}
                      >
                        {concept.status}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono' }}>
                        Segment: {formatDuration(concept.start_time)} - {formatDuration(concept.end_time)}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                      {concept.title}
                    </h3>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: isNeedsAttention ? '#DC2626' : isMastered ? '#16A34A' : 'var(--primary-accent)' }}>
                      {concept.understanding_percentage}%
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                      Understanding Level
                    </div>
                  </div>
                </div>

                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
                  {concept.description}
                </p>

                {/* Progress bar */}
                <div style={{ height: '8px', background: 'var(--bg-subtle)', borderRadius: '9999px', overflow: 'hidden', marginBottom: '16px' }}>
                  <div
                    style={{
                      width: `${concept.understanding_percentage}%`,
                      height: '100%',
                      background: isNeedsAttention
                        ? '#EF4444'
                        : isMastered
                        ? '#22C55E'
                        : 'linear-gradient(90deg, var(--accent-purple), var(--primary-accent))',
                      borderRadius: '9999px',
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>

                {/* Telemetry Stats Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '12px',
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 16px',
                    fontSize: '13px',
                  }}
                >
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Checkpoints</div>
                    <div style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>
                      {concept.checkpoints_count} Available
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Replay Friction</div>
                    <div style={{ fontWeight: 700, color: concept.replay_count >= 3 ? '#DC2626' : 'var(--primary-navy)' }}>
                      {concept.replay_count} {concept.replay_count === 1 ? 'time' : 'times'}
                      {concept.replay_count >= 3 && ' (Signal Triggered)'}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Confidence Score</div>
                    <div style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>
                      {(concept.confidence_score * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
