import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { MisconceptionLedgerItem, ReprobeItem, CheckpointEvaluation } from '../types';
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RotateCcw,
  Download,
  RefreshCw,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Brain,
  HelpCircle,
  FileQuestion,
  Send,
  Zap,
  BookmarkCheck,
  History,
  Info
} from 'lucide-react';

interface LedgerPageProps {
  onGoToLecture?: (lectureId: number) => void;
  onReviewConcept?: (misconceptionId: number) => void;
}

export const LedgerPage: React.FC<LedgerPageProps> = ({ onGoToLecture, onReviewConcept }) => {
  const [ledgerItems, setLedgerItems] = useState<MisconceptionLedgerItem[]>([]);
  const [reprobeItems, setReprobeItems] = useState<ReprobeItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<boolean>(false);

  // Filter state: 'All' | 'Confirmed' | 'Suspected' | 'Memorized' | 'Resolved' | 'Recurred'
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Active reprobe modal / drawer state
  const [activeReprobe, setActiveReprobe] = useState<ReprobeItem | null>(null);
  const [selectedMcqOption, setSelectedMcqOption] = useState<string>('');
  const [shortAnswerText, setShortAnswerText] = useState<string>('');
  const [confidenceLevel, setConfidenceLevel] = useState<number | null>(null);
  const [explanationText, setExplanationText] = useState<string>('');
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [evalResult, setEvalResult] = useState<CheckpointEvaluation | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ledgerData, reprobeData] = await Promise.all([
        api.misconceptions.getLedger(),
        api.misconceptions.getReprobe()
      ]);
      setLedgerItems(ledgerData);
      setReprobeItems(reprobeData);
    } catch (err: any) {
      setError(err.message || 'Failed to load misconception ledger.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      await api.misconceptions.downloadEvidenceCsv();
    } catch (err: any) {
      alert('Error downloading evidence CSV: ' + err.message);
    } finally {
      setExporting(false);
    }
  };

  const openReprobe = (item: ReprobeItem) => {
    setActiveReprobe(item);
    setSelectedMcqOption('');
    setShortAnswerText('');
    setConfidenceLevel(null);
    setExplanationText('');
    setEvalResult(null);
  };

  const closeReprobe = () => {
    setActiveReprobe(null);
    setEvalResult(null);
    fetchData(); // refresh to show updated states
  };

  const handleSubmitReprobe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeReprobe || !activeReprobe.reprobe_checkpoint) return;

    const answer =
      activeReprobe.reprobe_checkpoint.question_type === 'mcq'
        ? selectedMcqOption
        : shortAnswerText;

    if (!answer.trim()) return;

    setEvaluating(true);
    try {
      const result = await api.checkpoints.submitAnswer({
        checkpoint_id: activeReprobe.reprobe_checkpoint.id,
        student_answer: answer.trim(),
        confidence_level: confidenceLevel ?? undefined,
        explanation_text: explanationText.trim() || undefined,
      });
      setEvalResult(result);
    } catch (err: any) {
      alert('Failed to evaluate answer: ' + err.message);
    } finally {
      setEvaluating(false);
    }
  };

  const formatTimestamp = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatSeconds = (sec?: number) => {
    if (sec === undefined || sec === null) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const filteredItems = ledgerItems.filter((item) => {
    if (statusFilter === 'All') return true;
    const currentStatus = item.evidence_status || 'Suspected';
    return currentStatus.toLowerCase() === statusFilter.toLowerCase();
  });

  // Metric stats
  const countConfirmed = ledgerItems.filter(i => (i.evidence_status || '').toLowerCase() === 'confirmed').length;
  const countMemorized = ledgerItems.filter(i => i.memorized_flag || (i.evidence_status || '').toLowerCase() === 'memorized').length;
  const countResolved = ledgerItems.filter(i => (i.evidence_status || '').toLowerCase() === 'resolved').length;
  const countDueReprobes = reprobeItems.filter(r => r.is_due).length;

  const getStatusBadge = (status?: string, memorized?: boolean) => {
    if (memorized || status === 'Memorized') {
      return (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '3px 10px',
          borderRadius: '9999px',
          fontSize: '12px',
          fontWeight: 700,
          background: '#FEF3C7',
          color: '#B45309',
          border: '1px solid #FDE68A'
        }}>
          <History size={12} /> Memorized (Rote)
        </span>
      );
    }
    switch (status) {
      case 'Resolved':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: 700,
            background: 'var(--status-resolved-bg)',
            color: 'var(--status-resolved-text)',
            border: '1px solid var(--status-resolved-border)'
          }}>
            <CheckCircle2 size={12} /> Resolved
          </span>
        );
      case 'Confirmed':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: 700,
            background: 'var(--priority-high-bg)',
            color: 'var(--priority-high-text)',
            border: '1px solid var(--priority-high-border)'
          }}>
            <ShieldAlert size={12} /> Confirmed Misconception
          </span>
        );
      case 'Recurred':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: 700,
            background: '#FDF2F8',
            color: '#BE185D',
            border: '1px solid #FBCFE8'
          }}>
            <RotateCcw size={12} /> Recurred
          </span>
        );
      default:
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: 700,
            background: '#EFF6FF',
            color: '#1D4ED8',
            border: '1px solid #BFDBFE'
          }}>
            <HelpCircle size={12} /> Suspected
          </span>
        );
    }
  };

  return (
    <div className="main-content" style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 20px 80px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, var(--accent-purple), var(--primary-accent))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff'
            }}>
              <Brain size={22} />
            </div>
            <div>
              <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy-800)', margin: 0 }}>
                Persistent Misconception Ledger
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Verifiable evidence chains, explanation fidelity checks, spaced re-probing, and video remediation anchors.
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={fetchData}
            className="btn btn-secondary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExportCsv}
            disabled={exporting}
            className="btn btn-primary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Download size={14} />
            <span>{exporting ? 'Exporting...' : 'Export Evidence (CSV)'}</span>
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '14px',
        marginBottom: '28px'
      }}>
        <div className="card" style={{ padding: '16px 20px', borderLeft: '4px solid var(--primary-accent)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Total Tracked
          </div>
          <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--navy-800)', marginTop: '4px' }}>
            {ledgerItems.length}
          </div>
        </div>

        <div className="card" style={{ padding: '16px 20px', borderLeft: '4px solid var(--priority-high-text)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Confirmed Flaws
          </div>
          <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--priority-high-text)', marginTop: '4px' }}>
            {countConfirmed}
          </div>
        </div>

        <div className="card" style={{ padding: '16px 20px', borderLeft: '4px solid #D97706' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Memorized / Transfer Gap
          </div>
          <div style={{ fontSize: '26px', fontWeight: 800, color: '#D97706', marginTop: '4px' }}>
            {countMemorized}
          </div>
        </div>

        <div className="card" style={{ padding: '16px 20px', borderLeft: '4px solid #16A34A' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Evidence-Resolved
          </div>
          <div style={{ fontSize: '26px', fontWeight: 800, color: '#16A34A', marginTop: '4px' }}>
            {countResolved}
          </div>
        </div>

        <div className="card" style={{ padding: '16px 20px', borderLeft: '4px solid var(--accent-purple)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Spaced Reprobes Due
          </div>
          <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--accent-purple)', marginTop: '4px' }}>
            {countDueReprobes}
          </div>
        </div>
      </div>

      {/* Due for Spaced Re-probe section */}
      {reprobeItems.filter(r => r.is_due).length > 0 && (
        <div style={{
          background: 'linear-gradient(to right, #EEF2FF, #FAF5FF)',
          border: '1px solid #C7D2FE',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          marginBottom: '28px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Zap size={18} color="var(--accent-purple)" />
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--navy-800)', margin: 0 }}>
              Spaced Re-probes Ready for Verification
            </h2>
            <span style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '9999px',
              background: 'var(--accent-purple)',
              color: '#fff',
              fontWeight: 700
            }}>
              {reprobeItems.filter(r => r.is_due).length} Due
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            To protect against shallow memorization, MindTrace requires transfer re-testing after the delay window.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
            {reprobeItems.filter(r => r.is_due).map((rp) => (
              <div
                key={rp.misconception_id}
                style={{
                  background: '#FFFFFF',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent-purple)' }}>
                      {rp.lecture_title} • {rp.concept_name}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {rp.hours_since_last_seen}h elapsed
                    </span>
                  </div>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy-800)', marginTop: '4px', marginBottom: '8px' }}>
                    {rp.title}
                  </h3>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                    {rp.reprobe_checkpoint
                      ? `Follow-up question: ${rp.reprobe_checkpoint.question_text.slice(0, 75)}...`
                      : 'A transfer question is queued for this concept.'}
                  </div>
                </div>

                <button
                  onClick={() => openReprobe(rp)}
                  className="btn btn-primary btn-sm"
                  style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <BookmarkCheck size={14} />
                  <span>Attempt Transfer Probe</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {['All', 'Confirmed', 'Suspected', 'Memorized', 'Resolved', 'Recurred'].map((tab) => (
          <button
            key={tab}
            onClick={() => setStatusFilter(tab)}
            style={{
              padding: '6px 14px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              border: statusFilter === tab ? '1px solid var(--primary-accent)' : '1px solid var(--border-subtle)',
              background: statusFilter === tab ? 'var(--primary-accent)' : 'var(--bg-surface)',
              color: statusFilter === tab ? '#FFFFFF' : 'var(--text-muted)',
              transition: 'all 0.15s ease'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Ledger Item List */}
      {loading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 12px' }} />
          <div>Loading Persistent Misconception Ledger...</div>
        </div>
      ) : error ? (
        <div style={{ padding: '24px', background: '#FEE2E2', borderRadius: 'var(--radius-md)', color: '#DC2626' }}>
          {error}
        </div>
      ) : filteredItems.length === 0 ? (
        <div style={{ padding: '60px 20px', textAlign: 'center', background: '#FFFFFF', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)' }}>
          <CheckCircle2 size={36} color="#16A34A" style={{ margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--navy-800)' }}>
            No misconceptions found for filter: {statusFilter}
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Check back after completing lecture checkpoints or watching video modules.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredItems.map((item) => {
            const isExpanded = expandedId === item.id;
            return (
              <div
                key={item.id}
                className="card"
                style={{
                  padding: '20px',
                  borderRadius: 'var(--radius-lg)',
                  border: isExpanded ? '1px solid var(--primary-accent)' : '1px solid var(--border-subtle)',
                  transition: 'border 0.15s ease',
                }}
              >
                {/* Main Row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ flex: 1, minWidth: '280px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '6px' }}>
                      {getStatusBadge(item.evidence_status, item.memorized_flag)}
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Lecture: <strong>{item.lecture_title || 'General'}</strong>
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Concept: <strong>{item.concept_name}</strong>
                      </span>
                    </div>

                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--navy-800)', margin: '4px 0 6px' }}>
                      {item.title}
                    </h3>

                    {item.summary && (
                      <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                        {item.summary}
                      </p>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                      <span>Severity Score: <strong>{item.severity_score}</strong></span>
                      <span>Signals Logged: <strong>{item.evidence.length}</strong></span>
                      <span>First Detected: <strong>{formatTimestamp(item.first_detected)}</strong></span>
                      <span>Last Seen: <strong>{formatTimestamp(item.last_detected)}</strong></span>
                      {item.resolved_at && (
                        <span style={{ color: '#16A34A', fontWeight: 600 }}>
                          Resolved At: {formatTimestamp(item.resolved_at)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {item.remediation_start_time !== undefined && item.remediation_start_time !== null && (
                      <button
                        onClick={() => onGoToLecture && onGoToLecture(item.lecture_id)}
                        className="btn btn-secondary btn-sm"
                        style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                        title="Jump to video remediation segment"
                      >
                        <ExternalLink size={13} />
                        <span>Remediation Video ({formatSeconds(item.remediation_start_time)})</span>
                      </button>
                    )}

                    {onReviewConcept && (
                      <button
                        onClick={() => onReviewConcept(item.id)}
                        className="btn btn-primary btn-sm"
                        style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <Sparkles size={13} />
                        <span>Review</span>
                      </button>
                    )}

                    <button
                      onClick={() => setExpandedId(isExpanded ? null : item.id)}
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '6px 10px' }}
                      title="View Evidence Timeline"
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>
                </div>

                {/* Expanded Timeline Details */}
                {isExpanded && (
                  <div style={{
                    marginTop: '20px',
                    paddingTop: '20px',
                    borderTop: '1px solid var(--border-subtle)',
                  }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy-800)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <History size={15} color="var(--primary-accent)" />
                      Verifiable Evidence & Attempt Timeline
                    </h4>

                    {/* Timeline Container */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {/* Checkpoint Attempts */}
                      {item.attempts && item.attempts.length > 0 && (
                        <div style={{ marginBottom: '10px' }}>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                            Student Explanation Checks
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {item.attempts.map((att) => (
                              <div
                                key={att.id}
                                style={{
                                  background: att.is_correct ? '#F0FDF4' : '#FEF2F2',
                                  border: `1px solid ${att.is_correct ? '#BBF7D0' : '#FECACA'}`,
                                  borderRadius: 'var(--radius-md)',
                                  padding: '12px',
                                  fontSize: '12px'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                  <span style={{ fontWeight: 700, color: att.is_correct ? '#16A34A' : '#DC2626' }}>
                                    {att.is_correct ? 'Correct Answer' : 'Incorrect Answer'}
                                    {att.confidence_level && (
                                      <span style={{ marginLeft: '8px', color: '#4B5563', fontWeight: 500 }}>
                                        (Reported Confidence: {att.confidence_level === 3 ? 'High' : att.confidence_level === 2 ? 'Medium' : 'Low'})
                                      </span>
                                    )}
                                  </span>
                                  <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                                    {formatTimestamp(att.created_at)}
                                  </span>
                                </div>

                                {att.explanation_text && (
                                  <div style={{ color: '#1F2937', marginTop: '4px', fontStyle: 'italic' }}>
                                    "{att.explanation_text}"
                                  </div>
                                )}

                                {att.explanation_verdict && (
                                  <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span style={{
                                      padding: '1px 6px',
                                      borderRadius: '4px',
                                      fontSize: '11px',
                                      fontWeight: 700,
                                      background: att.explanation_verdict === 'valid' ? '#DCFCE7' : '#FEF3C7',
                                      color: att.explanation_verdict === 'valid' ? '#16A34A' : '#D97706'
                                    }}>
                                      LLM Verdict: {att.explanation_verdict}
                                    </span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Multimodal Evidence Signals */}
                      <div>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                          Signal Stream ({item.evidence.length} logs)
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {item.evidence.map((ev) => (
                            <div
                              key={ev.id}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                background: 'var(--bg-subtle)',
                                padding: '8px 12px',
                                borderRadius: 'var(--radius-sm)',
                                fontSize: '12px'
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  background: 'var(--bg-surface)',
                                  border: '1px solid var(--border-subtle)',
                                  color: 'var(--text-main)'
                                }}>
                                  {ev.signal_type}
                                </span>
                                <span>{ev.evidence_text}</span>
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)', fontSize: '11px' }}>
                                <span style={{ fontWeight: 600, color: 'var(--priority-high-text)' }}>
                                  +{ev.points_added} severity
                                </span>
                                <span>{formatTimestamp(ev.created_at)}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Reprobe Modal / Drawer */}
      {activeReprobe && activeReprobe.reprobe_checkpoint && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(11, 19, 43, 0.6)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: 'var(--radius-xl)',
            maxWidth: '620px',
            width: '100%',
            padding: '28px',
            boxShadow: 'var(--shadow-xl)',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-purple)', textTransform: 'uppercase' }}>
                  Spaced Transfer Probe
                </span>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy-800)' }}>
                  {activeReprobe.concept_name}
                </h3>
              </div>
              <button
                onClick={closeReprobe}
                style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Verifying resolution for: <strong>{activeReprobe.title}</strong>
            </p>

            <form onSubmit={handleSubmitReprobe}>
              <div style={{
                background: 'var(--bg-subtle)',
                padding: '16px',
                borderRadius: 'var(--radius-md)',
                marginBottom: '16px',
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--navy-800)'
              }}>
                {activeReprobe.reprobe_checkpoint.question_text}
              </div>

              {/* Options */}
              {activeReprobe.reprobe_checkpoint.question_type === 'mcq' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                  {activeReprobe.reprobe_checkpoint.options.map((opt, idx) => (
                    <label
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        padding: '10px 14px',
                        border: selectedMcqOption === opt ? '2px solid var(--primary-accent)' : '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        cursor: evalResult ? 'not-allowed' : 'pointer',
                        background: selectedMcqOption === opt ? 'var(--accent-soft)' : '#FFFFFF'
                      }}
                    >
                      <input
                        type="radio"
                        name="reprobe_mcq"
                        value={opt}
                        checked={selectedMcqOption === opt}
                        onChange={() => !evalResult && setSelectedMcqOption(opt)}
                        disabled={!!evalResult}
                      />
                      <span style={{ fontSize: '13px', color: 'var(--navy-800)' }}>{opt}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <textarea
                  value={shortAnswerText}
                  onChange={(e) => setShortAnswerText(e.target.value)}
                  disabled={!!evalResult}
                  placeholder="Type your answer here..."
                  rows={3}
                  className="input-field"
                  style={{ width: '100%', marginBottom: '16px' }}
                />
              )}

              {/* Confidence & Explanation */}
              {!evalResult && (
                <div style={{
                  background: 'var(--bg-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  marginBottom: '16px'
                }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--navy-800)', marginBottom: '6px' }}>
                    How sure are you?
                  </div>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                    {[
                      { level: 1, label: '1 - Not Sure' },
                      { level: 2, label: '2 - Somewhat' },
                      { level: 3, label: '3 - Very Sure' }
                    ].map(({ level, label }) => (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setConfidenceLevel(level)}
                        style={{
                          flex: 1,
                          padding: '6px 8px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          border: confidenceLevel === level ? '2px solid var(--primary-accent)' : '1px solid var(--border-strong)',
                          background: confidenceLevel === level ? 'var(--primary-accent)' : '#FFFFFF',
                          color: confidenceLevel === level ? '#FFFFFF' : 'var(--navy-800)'
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--navy-800)', marginBottom: '4px' }}>
                    Why? (One sentence explanation of your reasoning)
                  </div>
                  <input
                    type="text"
                    value={explanationText}
                    onChange={(e) => setExplanationText(e.target.value)}
                    placeholder="e.g., Because base case prevents infinite call stack..."
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-strong)',
                      fontSize: '12px'
                    }}
                  />
                </div>
              )}

              {/* Result Banner */}
              {evalResult && (
                <div style={{
                  padding: '14px',
                  borderRadius: 'var(--radius-md)',
                  background: evalResult.is_correct ? '#DCFCE7' : '#FEE2E2',
                  border: `1px solid ${evalResult.is_correct ? '#BBF7D0' : '#FECACA'}`,
                  marginBottom: '16px'
                }}>
                  <div style={{ fontWeight: 700, color: evalResult.is_correct ? '#16A34A' : '#DC2626' }}>
                    {evalResult.is_correct ? 'Probe Passed!' : 'Misconception Persists'}
                  </div>
                  <div style={{ fontSize: '12px', marginTop: '4px', color: '#1F2937' }}>
                    {evalResult.feedback_reason}
                  </div>
                  {evalResult.explanation_verdict && (
                    <div style={{ fontSize: '11px', fontWeight: 600, marginTop: '6px', color: '#4B5563' }}>
                      Reasoning Check: {evalResult.explanation_verdict} ({evalResult.verdict_reason})
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" onClick={closeReprobe} className="btn btn-secondary btn-sm">
                  Close
                </button>
                {!evalResult && (
                  <button
                    type="submit"
                    disabled={evaluating || (!selectedMcqOption && !shortAnswerText.trim())}
                    className="btn btn-primary btn-sm"
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Send size={14} />
                    <span>{evaluating ? 'Evaluating...' : 'Commit Answer'}</span>
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
