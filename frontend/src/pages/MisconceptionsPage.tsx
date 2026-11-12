import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';
import type { Misconception, MisconceptionDetail } from '../types';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  RotateCcw,
  HelpCircle,
  FileQuestion,
  RefreshCw,
  Sparkles,
  ArrowRight,
  Search,
  X,
  ExternalLink,
  BookOpen,
  Info,
  ChevronDown,
  Check,
  Video,
  ListChecks,
  AlertCircle
} from 'lucide-react';

interface MisconceptionsPageProps {
  onReviewConcept: (misconceptionId: number) => void;
  onGoToLecture?: (lectureId: number) => void;
}

export const MisconceptionsPage: React.FC<MisconceptionsPageProps> = ({
  onReviewConcept,
  onGoToLecture,
}) => {
  const [misconceptions, setMisconceptions] = useState<Misconception[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');

  // Full Details Modal
  const [detailModalItem, setDetailModalItem] = useState<Misconception | null>(null);
  const [detailData, setDetailData] = useState<MisconceptionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

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

  // Open details modal - fetch enriched data
  const handleViewDetails = async (m: Misconception) => {
    setDetailModalItem(m);
    setDetailData(null);
    setDetailLoading(true);
    try {
      const data = await api.misconceptions.getDetails(m.id);
      setDetailData(data);
    } catch {
      setDetailData(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const formatSeconds = (totalSeconds?: number) => {
    if (totalSeconds === undefined || totalSeconds === null) return null;
    const mins = Math.floor(totalSeconds / 60);
    const secs = Math.floor(totalSeconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'explicit_checkpoint':
        return <FileQuestion size={14} color="#DC2626" />;
      case 'behavioural_replay':
        return <RotateCcw size={14} color="#D97706" />;
      case 'manual_unresolved':
      case 'manual_status_update':
        return <HelpCircle size={14} color="#DC2626" />;
      case 'checkpoint_resolved':
        return <CheckCircle2 size={14} color="#16A34A" />;
      default:
        return <AlertTriangle size={14} color="#4F46E5" />;
    }
  };

  // Client-side live search filtering
  const filteredMisconceptions = useMemo(() => {
    if (!searchQuery.trim()) return misconceptions;
    const q = searchQuery.toLowerCase();
    return misconceptions.filter((m) => {
      const matchTitle = m.title?.toLowerCase().includes(q);
      const matchConcept = m.concept_name?.toLowerCase().includes(q);
      const matchLecture = m.lecture_title?.toLowerCase().includes(q);
      const matchSummary = m.summary?.toLowerCase().includes(q);
      const matchIncorrect = m.incorrect_understanding?.toLowerCase().includes(q);
      const matchCorrect = m.correct_explanation?.toLowerCase().includes(q);
      return matchTitle || matchConcept || matchLecture || matchSummary || matchIncorrect || matchCorrect;
    });
  }, [misconceptions, searchQuery]);

  const getStatusBadgeStyle = (status: string) => {
    switch (status) {
      case 'Resolved':
        return { bg: '#DCFCE7', text: '#16A34A', border: '#BBF7D0' };
      case 'In Progress':
      case 'Improving':
        return { bg: '#E0E7FF', text: '#4338CA', border: '#C7D2FE' };
      case 'Needs Review':
        return { bg: '#FEF3C7', text: '#D97706', border: '#FDE68A' };
      case 'Unresolved':
      default:
        return { bg: '#FEE2E2', text: '#DC2626', border: '#FECACA' };
    }
  };

  const getSeverityBadgeStyle = (level: string) => {
    switch (level) {
      case 'High':
        return { bg: '#FEE2E2', text: '#DC2626', border: '#FECACA' };
      case 'Medium':
        return { bg: '#FEF3C7', text: '#D97706', border: '#FDE68A' };
      case 'Low':
      default:
        return { bg: '#DBEAFE', text: '#2563EB', border: '#BFDBFE' };
    }
  };

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* Page Header */}
      <div className="section-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', width: '100%' }}>
          <div>
            <h1 className="section-title">Persistent Misconceptions Tracker</h1>
            <p className="section-subtitle">
              Structured longitudinal memory of conceptual friction points detected from your lecture study interactions.
            </p>
          </div>
          <button
            onClick={loadMisconceptions}
            disabled={loading}
            className="btn btn-secondary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'spin-animation' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>


      {/* Search & Filter Toolbar */}
      <div
        className="card"
        style={{
          padding: '18px 22px',
          marginBottom: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        {/* Search Bar */}
        <div style={{ position: 'relative', width: '100%' }}>
          <Search
            size={18}
            style={{
              position: 'absolute',
              left: '14px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-light)',
            }}
          />
          <input
            type="text"
            placeholder="Search misconceptions, concepts, lecture titles, or explanations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '11px 40px 11px 42px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-strong)',
              fontSize: '14px',
              fontFamily: 'inherit',
              outline: 'none',
              boxSizing: 'border-box',
              background: 'var(--bg-main)',
              transition: 'border-color var(--transition-fast)',
            }}
            onFocus={(e) => (e.target.style.borderColor = 'var(--accent-purple)')}
            onBlur={(e) => (e.target.style.borderColor = 'var(--border-strong)')}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-light)',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Clear search"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Filters */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '16px',
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: '14px',
          }}
        >
          {/* Status Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', marginRight: '4px' }}>
              Status:
            </span>
            {['All', 'Unresolved', 'Needs Review', 'Improving', 'Resolved'].map((s) => (
              <button
                key={s}
                className={`btn btn-sm ${statusFilter === s ? 'btn-accent' : 'btn-secondary'}`}
                onClick={() => setStatusFilter(s)}
                style={{ fontSize: '12px', padding: '6px 12px' }}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Priority Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', marginRight: '4px' }}>
              Severity:
            </span>
            {['All', 'High', 'Medium', 'Low'].map((p) => (
              <button
                key={p}
                className={`btn btn-sm ${priorityFilter === p ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setPriorityFilter(p)}
                style={{ fontSize: '12px', padding: '6px 12px' }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content Rendering */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <RefreshCw size={28} className="spin-animation" style={{ color: 'var(--accent-purple)' }} />
          <div style={{ marginTop: '12px', color: 'var(--text-muted)' }}>Loading misconceptions...</div>
        </div>
      ) : error ? (
        <div className="alert-banner alert-warning">{error}</div>
      ) : filteredMisconceptions.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <CheckCircle2 size={46} color="#16A34A" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>
            {searchQuery || statusFilter !== 'All' || priorityFilter !== 'All'
              ? 'No misconceptions found matching your filters'
              : 'No misconceptions recorded'}
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '480px', margin: '8px auto 20px' }}>
            {searchQuery || statusFilter !== 'All' || priorityFilter !== 'All'
              ? 'Try adjusting your search terms or clearing status/severity filters.'
              : 'Keep studying and taking lecture checkpoints. When conceptual friction occurs, MindTrace will track it persistently here.'}
          </p>
          {(searchQuery || statusFilter !== 'All' || priorityFilter !== 'All') && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSearchQuery('');
                setPriorityFilter('All');
                setStatusFilter('All');
              }}
            >
              Reset Filters
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>
            Showing {filteredMisconceptions.length} misconception{filteredMisconceptions.length !== 1 ? 's' : ''}
          </div>

          {filteredMisconceptions.map((m) => {
            const statusStyle = getStatusBadgeStyle(m.status);
            const severityStyle = getSeverityBadgeStyle(m.severity_level);
            const isResolved = m.status === 'Resolved';
            const isUpdating = false; // Status managed by system

            return (
              <div
                key={m.id}
                id={`misconception-card-${m.id}`}
                className="card"
                style={{
                  borderLeft: `5px solid ${statusStyle.text}`,
                  padding: '24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  transition: 'box-shadow var(--transition-fast)',
                }}
              >
                {/* Header Row */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: '12px',
                  }}
                >
                  <div style={{ flex: 1, minWidth: '280px' }}>
                    {/* Badges Row */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          background: severityStyle.bg,
                          color: severityStyle.text,
                          border: `1px solid ${severityStyle.border}`,
                          textTransform: 'uppercase',
                        }}
                      >
                        {m.severity_level} Severity • {m.severity_score}/100
                      </span>

                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          background: statusStyle.bg,
                          color: statusStyle.text,
                          border: `1px solid ${statusStyle.border}`,
                        }}
                      >
                        {m.status}
                      </span>

                      {/* Clickable Lecture Link */}
                      {m.lecture_id && (
                        <button
                          onClick={() => onGoToLecture && onGoToLecture(m.lecture_id)}
                          style={{
                            background: 'var(--bg-subtle)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '3px 8px',
                            fontSize: '12px',
                            color: 'var(--primary-accent)',
                            fontWeight: 600,
                            cursor: onGoToLecture ? 'pointer' : 'default',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                          title="Open lecture in player"
                        >
                          <Video size={12} />
                          <span>{m.lecture_title || `Lecture #${m.lecture_id}`}</span>
                          {onGoToLecture && <ExternalLink size={11} />}
                        </button>
                      )}
                    </div>

                    {/* Misconception Title */}
                    <h3
                      style={{
                        fontSize: '19px',
                        fontWeight: 800,
                        color: 'var(--primary-navy)',
                        marginBottom: '6px',
                        lineHeight: 1.3,
                      }}
                    >
                      {m.title}
                    </h3>

                    {/* Concept & Timestamp */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        fontSize: '13px',
                        color: 'var(--accent-purple)',
                        fontWeight: 600,
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <BookOpen size={13} />
                        Concept: {m.concept_name}
                      </span>
                      {m.concept_start_time !== undefined && m.concept_start_time !== null && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)' }}>
                          <Clock size={12} />
                          {formatSeconds(m.concept_start_time)}
                          {m.concept_end_time ? ` - ${formatSeconds(m.concept_end_time)}` : ''}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Header Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleViewDetails(m)}
                      style={{ fontSize: '12px' }}
                    >
                      <Info size={14} />
                      <span>View Details</span>
                    </button>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onReviewConcept(m.id)}
                      style={{ fontSize: '12px' }}
                    >
                      <Sparkles size={14} />
                      <span>Review Concept</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </div>

                {/* Summary */}
                {m.summary && (
                  <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    {m.summary}
                  </p>
                )}

                {/* Comparison Boxes: Incorrect Understanding vs Correct Explanation */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: '14px',
                  }}
                >
                  {/* Incorrect Understanding */}
                  <div
                    style={{
                      background: '#FFF5F5',
                      border: '1px solid #FED7D7',
                      borderRadius: 'var(--radius-md)',
                      padding: '14px 16px',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '11px',
                        fontWeight: 800,
                        color: '#C53030',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        marginBottom: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <AlertCircle size={14} />
                      <span>Incorrect Understanding</span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#742A2A', lineHeight: 1.5 }}>
                      {m.incorrect_understanding ||
                        m.evidence?.[0]?.evidence_text ||
                        'Student exhibited conceptual confusion regarding underlying rules.'}
                    </div>
                  </div>

                  {/* Correct Explanation */}
                  <div
                    style={{
                      background: '#F0FDF4',
                      border: '1px solid #BBF7D0',
                      borderRadius: 'var(--radius-md)',
                      padding: '14px 16px',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '11px',
                        fontWeight: 800,
                        color: '#15803D',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        marginBottom: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <CheckCircle2 size={14} />
                      <span>Correct Mental Model / Explanation</span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#166534', lineHeight: 1.5 }}>
                      {m.correct_explanation ||
                        `Master the foundational definition of "${m.concept_name}" by verifying inputs and outputs in step-by-step evaluation.`}
                    </div>
                  </div>
                </div>

                {/* System Status & Signal Summary */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 16px',
                  }}
                >
                  {/* Read-only Status Badge */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-main)' }}>
                      Status:
                    </span>
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        padding: '4px 10px',
                        borderRadius: 'var(--radius-sm)',
                        background: getStatusBadgeStyle(m.status).bg,
                        color: getStatusBadgeStyle(m.status).text,
                        border: `1px solid ${getStatusBadgeStyle(m.status).border}`,
                      }}
                    >
                      {m.status}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      System-managed
                    </span>
                  </div>

                  {/* Signals recorded count */}
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>
                    Evidentiary Signals: <strong>{m.evidence?.length || 0}</strong> recorded
                  </div>
                </div>

                {/* Footer Metadata */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '8px',
                    fontSize: '12px',
                    color: 'var(--text-light)',
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '12px',
                  }}
                >
                  <span>Occurrences: <strong>{m.occurrence_count}</strong></span>
                  <span>First identified: {formatDate(m.first_detected)}</span>
                  <span>Last recorded: {formatDate(m.last_detected)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Details Modal */}
      {detailModalItem && (
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
          onClick={() => setDetailModalItem(null)}
        >
          <div
            className="card"
            style={{
              maxWidth: '680px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '28px',
              position: 'relative',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              onClick={() => { setDetailModalItem(null); setDetailData(null); }}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                padding: '4px',
              }}
            >
              <X size={20} />
            </button>

            {/* Modal Header */}
            <div style={{ marginBottom: '18px', paddingRight: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-sm)',
                    ...getSeverityBadgeStyle(detailModalItem.severity_level),
                  }}
                >
                  {detailModalItem.severity_level} Severity ({detailModalItem.severity_score}/100)
                </span>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-sm)',
                    ...getStatusBadgeStyle(detailModalItem.status),
                  }}
                >
                  {detailModalItem.status}
                </span>
              </div>
              <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--primary-navy)', lineHeight: 1.3 }}>
                {detailModalItem.title}
              </h2>
              <div style={{ fontSize: '13px', color: 'var(--accent-purple)', fontWeight: 600, marginTop: '4px' }}>
                Lecture: {detailModalItem.lecture_title || 'Introduction to Functions'} • Concept: {detailModalItem.concept_name}
              </div>
            </div>

            {/* Detail Loading Spinner */}
            {detailLoading && (
              <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)', fontSize: '14px' }}>
                <RefreshCw size={18} className="spin-animation" style={{ display: 'inline-block', marginRight: '8px' }} />
                Loading detailed analysis...
              </div>
            )}

            {/* Enriched Detail Sections — shown when detailData loaded */}
            {!detailLoading && detailData && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>

                {/* Why It Was Detected */}
                <div style={{ background: '#FEF9C3', border: '1px solid #FDE68A', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 800, color: '#B45309', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    Why It Was Detected
                  </div>
                  <div style={{ fontSize: '13px', color: '#78350F', lineHeight: 1.6 }}>
                    {detailData.why_detected}
                  </div>
                </div>

                {/* Original Question & Answers */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 16px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--primary-navy)', textTransform: 'uppercase', marginBottom: '6px' }}>Original Question</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5 }}>{detailData.original_question}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div style={{ background: '#FFF5F5', border: '1px solid #FED7D7', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 800, color: '#C53030', marginBottom: '5px', textTransform: 'uppercase' }}>Student's Wrong Answer</div>
                      <div style={{ fontSize: '13px', color: '#742A2A' }}>{detailData.student_wrong_answer}</div>
                    </div>
                    <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 800, color: '#15803D', marginBottom: '5px', textTransform: 'uppercase' }}>Correct Answer</div>
                      <div style={{ fontSize: '13px', color: '#166534' }}>{detailData.correct_answer}</div>
                    </div>
                  </div>
                </div>

                {/* Detection Evidence */}
                <div style={{ background: '#EEF2FF', border: '1px solid #C7D2FE', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 800, color: '#3730A3', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>Detection Evidence</div>
                  <div style={{ fontSize: '13px', color: '#312E81', lineHeight: 1.6 }}>{detailData.detection_evidence}</div>
                </div>

                {/* Lecture Evidence */}
                {detailData.lecture_evidence && detailData.lecture_evidence !== 'Evidence not available' ? (
                  <div style={{ background: '#F0F9FF', border: '1px solid #BAE6FD', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 800, color: '#0369A1', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                      Lecture Evidence
                    </div>
                    <div style={{ fontSize: '13px', color: '#0C4A6E', lineHeight: 1.6, fontStyle: 'italic' }}>
                      "{detailData.lecture_evidence}"
                    </div>
                    {detailData.concept_start_time != null && onGoToLecture && (
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ marginTop: '10px', fontSize: '12px' }}
                        onClick={() => {
                          setDetailModalItem(null);
                          setDetailData(null);
                          onGoToLecture(detailData.lecture_id);
                        }}
                      >
                        <Video size={13} />
                        <span>Watch This Part ({formatSeconds(detailData.concept_start_time)})</span>
                      </button>
                    )}
                  </div>
                ) : (
                  <div style={{ background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 16px', fontSize: '13px', color: 'var(--text-muted)' }}>
                    Lecture evidence not available for this misconception.
                  </div>
                )}

                {/* Marked Unresolved */}
                {detailData.marked_unresolved && (
                  <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius-md)', padding: '12px 16px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 800, color: '#B91C1C', textTransform: 'uppercase', marginBottom: '5px' }}>Marked Unresolved</div>
                    <div style={{ fontSize: '13px', color: '#7F1D1D' }}>{detailData.marked_unresolved_reason || 'System detected incorrect answer.'}</div>
                  </div>
                )}

                {/* Assessment History */}
                {detailData.assessment_history && detailData.assessment_history.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '10px', textTransform: 'uppercase' }}>
                      Assessment History ({detailData.assessment_history.length})
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
                      {detailData.assessment_history.map((attempt, idx) => (
                        <div key={idx} style={{ background: attempt.is_correct ? '#F0FDF4' : '#FFF5F5', border: `1px solid ${attempt.is_correct ? '#BBF7D0' : '#FED7D7'}`, borderRadius: 'var(--radius-sm)', padding: '10px 14px', fontSize: '13px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontWeight: 700, color: attempt.is_correct ? '#16A34A' : '#DC2626', fontSize: '12px' }}>
                              {attempt.is_correct ? '✓ Correct' : '✗ Incorrect'} — {attempt.context_type}
                            </span>
                            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                              {attempt.created_at ? new Date(attempt.created_at).toLocaleDateString() : ''}
                            </span>
                          </div>
                          <div style={{ color: 'var(--text-main)', marginBottom: '2px' }}>{attempt.question}</div>
                          <div style={{ color: attempt.is_correct ? '#166534' : '#742A2A', fontSize: '12px' }}>
                            Answer: {attempt.student_answer}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Next Reassessment Info */}
                {detailData.next_reassessment_info && (
                  <div style={{ background: '#F5F3FF', border: '1px solid #DDD6FE', borderRadius: 'var(--radius-md)', padding: '12px 16px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 800, color: '#5B21B6', textTransform: 'uppercase', marginBottom: '5px' }}>Next Reassessment</div>
                    <div style={{ fontSize: '13px', color: '#3B0764' }}>{detailData.next_reassessment_info}</div>
                    {detailData.recheck_due && (
                      <div style={{ fontSize: '12px', color: '#6D28D9', marginTop: '4px' }}>Due: {detailData.recheck_due}</div>
                    )}
                  </div>
                )}

              </div>
            )}

            {/* Fallback: show existing shallow data when detailData not loaded */}
            {!detailLoading && !detailData && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
              <div>
                <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '4px', textTransform: 'uppercase' }}>
                  Overview & Summary
                </h4>
                <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.6 }}>
                  {detailModalItem.summary}
                </p>
              </div>

              {/* Contrast Section */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ background: '#FFF5F5', border: '1px solid #FED7D7', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#C53030', marginBottom: '4px' }}>
                    Flawed Student Mental Model:
                  </div>
                  <div style={{ fontSize: '13px', color: '#742A2A', lineHeight: 1.5 }}>
                    {detailModalItem.incorrect_understanding || 'Misconception regarding conceptual boundaries.'}
                  </div>
                </div>

                <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#15803D', marginBottom: '4px' }}>
                    Remediation & Correct Explanation:
                  </div>
                  <div style={{ fontSize: '13px', color: '#166534', lineHeight: 1.5 }}>
                    {detailModalItem.correct_explanation || 'Step-by-step conceptual mastery pathway.'}
                  </div>
                </div>
              </div>

              {/* Evidentiary Signals List */}
              <div>
                <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '10px', textTransform: 'uppercase' }}>
                  Evidentiary Signal Trail ({detailModalItem.evidence?.length || 0})
                </h4>
                <div
                  style={{
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    maxHeight: '180px',
                    overflowY: 'auto',
                  }}
                >
                  {detailModalItem.evidence?.length ? (
                    detailModalItem.evidence.map((ev) => (
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
                          {ev.points_added > 0 ? `+${ev.points_added}` : ev.points_added} severity
                        </span>
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                      No evidentiary signals recorded yet.
                    </div>
                  )}
                </div>
              </div>
            </div>
            )}

            {/* Modal Actions */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px',
                borderTop: '1px solid var(--border-subtle)',
                paddingTop: '18px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-main)' }}>Status:</span>
                <span
                  style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-sm)',
                    background: getStatusBadgeStyle(detailModalItem.status).bg,
                    color: getStatusBadgeStyle(detailModalItem.status).text,
                    border: `1px solid ${getStatusBadgeStyle(detailModalItem.status).border}`,
                  }}
                >
                  {detailModalItem.status}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>System-managed</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {detailModalItem.lecture_id && onGoToLecture && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setDetailModalItem(null);
                      onGoToLecture(detailModalItem.lecture_id);
                    }}
                  >
                    <Video size={14} />
                    <span>Open Lecture</span>
                  </button>
                )}
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    setDetailModalItem(null);
                    setDetailData(null);
                    onReviewConcept(detailModalItem.id);
                  }}
                >
                  <Sparkles size={14} />
                  <span>Review Concept</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
