import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { Misconception } from '../types';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  RotateCcw,
  HelpCircle,
  TrendingUp,
  FileQuestion,
  RefreshCw,
  Sparkles,
  ArrowRight,
  Filter
} from 'lucide-react';

interface MisconceptionsPageProps {
  onReviewConcept: (misconceptionId: number) => void;
}

export const MisconceptionsPage: React.FC<MisconceptionsPageProps> = ({ onReviewConcept }) => {
  const [misconceptions, setMisconceptions] = useState<Misconception[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [priorityFilter, setPriorityFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');

  const loadMisconceptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.misconceptions.list({
        priority: priorityFilter,
        status_filter: statusFilter,
      });
      setMisconceptions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch misconceptions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMisconceptions();
  }, [priorityFilter, statusFilter]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'explicit_checkpoint':
        return <FileQuestion size={14} color="#DC2626" />;
      case 'behavioural_replay':
        return <RotateCcw size={14} color="#D97706" />;
      case 'manual_unresolved':
        return <HelpCircle size={14} color="#DC2626" />;
      case 'checkpoint_resolved':
        return <CheckCircle2 size={14} color="#16A34A" />;
      default:
        return <AlertTriangle size={14} color="#4F46E5" />;
    }
  };

  return (
    <div style={{ paddingBottom: '60px' }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Persistent Misconceptions Tracker</h1>
          <p className="section-subtitle">
            Structured longitudinal memory of conceptual friction points detected from lecture study interactions.
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div
        className="card"
        style={{
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', marginRight: '6px' }}>
            Priority:
          </span>
          {['All', 'High', 'Medium', 'Low'].map((p) => (
            <button
              key={p}
              id={`filter-priority-${p.toLowerCase()}`}
              className={`btn btn-sm ${priorityFilter === p ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setPriorityFilter(p)}
            >
              {p}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', marginRight: '6px' }}>
            Status:
          </span>
          {['All', 'Unresolved', 'Improving', 'Resolved'].map((s) => (
            <button
              key={s}
              id={`filter-status-${s.toLowerCase()}`}
              className={`btn btn-sm ${statusFilter === s ? 'btn-accent' : 'btn-secondary'}`}
              onClick={() => setStatusFilter(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <RefreshCw size={28} className="spin-animation" style={{ color: 'var(--accent-purple)' }} />
          <div style={{ marginTop: '12px', color: 'var(--text-muted)' }}>Filtering misconceptions...</div>
        </div>
      ) : error ? (
        <div className="alert-banner alert-warning">{error}</div>
      ) : misconceptions.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <CheckCircle2 size={44} color="#16A34A" style={{ margin: '0 auto 14px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>
            No misconceptions found matching this filter
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '460px', margin: '8px auto 20px' }}>
            Keep answering lecture checkpoints and studying. When conceptual friction occurs, MindTrace will persist it here.
          </p>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {
              setPriorityFilter('All');
              setStatusFilter('All');
            }}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {misconceptions.map((m) => {
            const isHigh = m.severity_level === 'High';
            const isMed = m.severity_level === 'Medium';
            const isResolved = m.status === 'Resolved';
            const isImproving = m.status === 'Improving';

            return (
              <div
                key={m.id}
                id={`misconception-card-${m.id}`}
                className="card"
                style={{
                  borderLeft: `5px solid ${
                    isResolved
                      ? '#16A34A'
                      : isImproving
                      ? 'var(--accent-purple)'
                      : isHigh
                      ? '#DC2626'
                      : isMed
                      ? '#D97706'
                      : '#2563EB'
                  }`,
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span className={`badge ${isHigh ? 'badge-high' : isMed ? 'badge-medium' : 'badge-low'}`}>
                        {m.severity_level} Priority • Score: {m.severity_score}
                      </span>
                      <span className={`badge ${isResolved ? 'badge-resolved' : isImproving ? 'badge-improving' : 'badge-unresolved'}`}>
                        {m.status}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>
                        {m.lecture_title}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                      {m.title}
                    </h3>
                    <div style={{ fontSize: '13px', color: 'var(--accent-purple)', fontWeight: 700 }}>
                      Concept: {m.concept_name}
                    </div>
                  </div>

                  <button
                    id={`btn-review-concept-${m.id}`}
                    className="btn btn-primary btn-sm"
                    onClick={() => onReviewConcept(m.id)}
                  >
                    <Sparkles size={14} />
                    <span>Review Concept</span>
                    <ArrowRight size={14} />
                  </button>
                </div>

                <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '16px' }}>
                  {m.summary}
                </p>

                {/* Evidence Chain Display (Section 15, 17) */}
                <div
                  style={{
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '14px 18px',
                    marginBottom: '16px',
                  }}
                >
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary-navy)', textTransform: 'uppercase', marginBottom: '8px' }}>
                    Evidentiary Signal Trail ({m.evidence.length} signals recorded)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {m.evidence.map((ev) => (
                      <div key={ev.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '13px' }}>
                        <div style={{ marginTop: '2px' }}>{getSignalIcon(ev.signal_type)}</div>
                        <div style={{ flex: 1, color: 'var(--text-main)' }}>{ev.evidence_text}</div>
                        <span
                          style={{
                            fontWeight: 700,
                            fontFamily: 'JetBrains Mono',
                            fontSize: '12px',
                            color: ev.points_added > 0 ? '#DC2626' : '#16A34A',
                          }}
                        >
                          {ev.points_added > 0 ? `+${ev.points_added}` : ev.points_added} pts
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Footer metadata */}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-light)', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                  <span>Occurrences: <strong>{m.occurrence_count}</strong></span>
                  <span>First detected: {formatDate(m.first_detected)}</span>
                  <span>Last active: {formatDate(m.last_detected)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
