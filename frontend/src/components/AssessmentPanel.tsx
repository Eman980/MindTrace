import React, { useState, useEffect } from 'react';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Save,
  BookOpen,
  ChevronRight,
  ChevronDown,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  FileText,
  RotateCcw,
  Send,
  HelpCircle
} from 'lucide-react';

import type {
  AssessmentDifficulty,
  Assessment,
  AssessmentQuestion,
  AssessmentResult,
  AssessmentStatus
} from '../types';

import { api } from '../services/api';

interface ConceptMeta {
  id: number;
  title: string;
  start_time?: number;
}

interface AssessmentPanelProps {
  lectureId: number;
  lectureTitle: string;
  courseCode?: string;
  concepts?: ConceptMeta[];
  onSeekToTimestamp?: (seconds: number) => void;
  onBackToLecture?: () => void;
}

const DIFFICULTY_CONFIG: Record<
  AssessmentDifficulty,
  {
    title: string;
    subtitle: string;
    badgeColor: string;
    badgeBg: string;
    borderColor: string;
    focusSummary: string;
    description: string;
  }
> = {
  easy: {
    title: 'Easy',
    subtitle: 'Basic concepts, definitions & direct recall',
    badgeColor: '#16A34A',
    badgeBg: '#DCFCE7',
    borderColor: '#86EFAC',
    focusSummary: 'Foundational recall, core terminology & simple examples',
    description: 'Tests fundamental definitions and direct properties explicitly introduced in the lecture without complex edge cases.'
  },
  moderate: {
    title: 'Moderate',
    subtitle: 'Mechanisms, comparisons & practical applications',
    badgeColor: '#4F46E5',
    badgeBg: '#EEF2FF',
    borderColor: '#C7D2FE',
    focusSummary: 'Operational mechanisms, comparisons & standard applications',
    description: 'Tests how concepts operate, comparing related ideas, and explaining why specific rules or data structures are applied.'
  },
  hard: {
    title: 'Hard',
    subtitle: 'Complex scenarios, trade-offs & problem solving',
    badgeColor: '#DC2626',
    badgeBg: '#FEE2E2',
    borderColor: '#FCA5A5',
    focusSummary: 'System scenarios, edge cases & architectural trade-offs',
    description: 'Tests multi-step reasoning, real-world failure modes, edge-case troubleshooting, and synthesis across multiple topics.'
  }
};

export const AssessmentPanel: React.FC<AssessmentPanelProps> = ({
  lectureId,
  lectureTitle,
  courseCode,
  concepts = [],
  onSeekToTimestamp,
  onBackToLecture
}) => {
  // Navigation / screen state: 'select' | 'exam' | 'results'
  const [screen, setScreen] = useState<'select' | 'exam' | 'results'>('select');

  // Status & Attempt State
  const [statusLoading, setStatusLoading] = useState<boolean>(true);
  const [statusData, setStatusData] = useState<AssessmentStatus | null>(null);

  // Active Assessment State
  const [selectedDifficulty, setSelectedDifficulty] = useState<AssessmentDifficulty>('moderate');
  const [activeAssessment, setActiveAssessment] = useState<Assessment | null>(null);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Results State
  const [results, setResults] = useState<AssessmentResult | null>(null);

  // Confirm Submit Modal
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [showExitModal, setShowExitModal] = useState<boolean>(false);

  // Generating state
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generatingDifficulty, setGeneratingDifficulty] = useState<AssessmentDifficulty | null>(null);
  const [isRetaking, setIsRetaking] = useState<boolean>(false);

  // Load Status on Mount or Lecture change
  useEffect(() => {
    fetchStatus();
  }, [lectureId]);

  const fetchStatus = async () => {
    setStatusLoading(true);
    setErrorMessage('');
    try {
      const res = await api.assessments.getStatus(lectureId);
      setStatusData(res);
      // If there is an active in-progress attempt, default to its difficulty
      if (res.in_progress_attempt) {
        setSelectedDifficulty(res.in_progress_attempt.difficulty);
      }
    } catch (err: any) {
      console.error('[AssessmentPanel] Status fetch error:', err);
    } finally {
      setStatusLoading(false);
    }
  };

  // Start or directly resume assessment at chosen difficulty
  const handleStartAssessment = async (diff: AssessmentDifficulty) => {
    setSelectedDifficulty(diff);
    setIsGenerating(true);
    setGeneratingDifficulty(diff);
    setErrorMessage('');
    try {
      const res = await api.assessments.start(lectureId, diff);
      setActiveAssessment(res.assessment);
      setAttemptId(res.attempt_id);
      setAnswers(res.in_progress_answers || {});
      setScreen('exam');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to start assessment. Please try again.');
    } finally {
      setIsGenerating(false);
      setGeneratingDifficulty(null);
    }
  };

  // Retake: generate a fresh attempt at the same difficulty, preserve history
  const handleRetakeAssessment = async () => {
    if (!results) return;
    setIsRetaking(true);
    setErrorMessage('');
    try {
      const diff = results.difficulty as AssessmentDifficulty;
      const res = await api.assessments.retake(lectureId, diff);
      setActiveAssessment(res.assessment);
      setAttemptId(res.attempt_id);
      setAnswers({});
      setResults(null);
      setShowConfirmModal(false);
      setSelectedDifficulty(diff);
      setScreen('exam');
      fetchStatus();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate a new attempt. Please try again.');
    } finally {
      setIsRetaking(false);
    }
  };

  // Update Answer for a question
  const handleAnswerChange = (questionId: string, value: string) => {
    const updated = { ...answers, [questionId]: value };
    setAnswers(updated);
  };

  // Explicit Save Progress
  const handleSaveProgress = async () => {
    if (!attemptId) return;
    setIsSaving(true);
    setSaveMessage('');
    try {
      await api.assessments.saveProgress(attemptId, answers);
      setSaveMessage('Draft saved successfully');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err: any) {
      setSaveMessage('Failed to save draft.');
    } finally {
      setIsSaving(false);
    }
  };

  // Trigger Submit
  const handlePreSubmit = () => {
    if (!activeAssessment) return;
    const answeredCount = Object.values(answers).filter(a => a && a.trim().length > 0).length;
    const total = activeAssessment.questions.length;
    if (answeredCount < total) {
      setShowConfirmModal(true);
    } else {
      executeSubmit();
    }
  };

  const executeSubmit = async () => {
    if (!attemptId) return;
    setShowConfirmModal(false);
    setIsSubmitting(true);
    setErrorMessage('');
    try {
      const res = await api.assessments.submit(attemptId, answers);
      setResults(res);
      setScreen('results');
      fetchStatus();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit assessment.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // View past attempt
  const handleViewPastAttempt = async (pastAttemptId: number) => {
    setStatusLoading(true);
    setErrorMessage('');
    try {
      const res = await api.assessments.getAttempt(pastAttemptId);
      setResults(res);
      setScreen('results');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load attempt details.');
    } finally {
      setStatusLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: GENERATING OVERLAY
  // ─────────────────────────────────────────────────────────────────────────────
  if (isGenerating && generatingDifficulty) {
    const cfg = DIFFICULTY_CONFIG[generatingDifficulty];
    return (
      <div style={{ padding: '56px 20px', textAlign: 'center', fontFamily: 'inherit' }}>
        <div style={{
          width: '48px', height: '48px', borderRadius: '50%',
          border: `3px solid ${cfg.badgeBg}`,
          borderTopColor: cfg.badgeColor,
          animation: 'spin 0.8s linear infinite',
          margin: '0 auto 20px auto'
        }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <div style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', marginBottom: '6px' }}>
          Preparing {cfg.title} Final Assessment…
        </div>
        <div style={{ color: '#64748B', fontSize: '13px', maxWidth: '440px', margin: '0 auto' }}>
          Validating 4 Multiple Choice and 3 Conceptual Short Answer questions grounded in{' '}
          <strong>{lectureTitle}</strong>.
        </div>
        <div style={{
          marginTop: '20px', display: 'inline-flex', alignItems: 'center', gap: '6px',
          background: cfg.badgeBg, color: cfg.badgeColor,
          padding: '6px 14px', borderRadius: '16px', fontSize: '12px', fontWeight: 700
        }}>
          <Sparkles size={14} />
          {generatingDifficulty.toUpperCase()} • 7 Questions Total
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: SCREEN 1 - COMPACT ASSESSMENT CARD & PRACTICE MODE
  // ─────────────────────────────────────────────────────────────────────────────
  if (screen === 'select') {
    const inProgress = statusData?.in_progress_attempt;
    const selectedCfg = DIFFICULTY_CONFIG[selectedDifficulty];

    return (
      <div style={{ padding: '16px', maxWidth: '780px', margin: '0 auto', fontFamily: 'inherit' }}>
        {errorMessage && (
          <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#DC2626', padding: '10px 14px', borderRadius: '8px', marginBottom: '16px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} />
            {errorMessage}
          </div>
        )}

        {/* COMPACT ASSESSMENT CARD */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: '12px',
            border: '1px solid #E2E8F0',
            boxShadow: '0 4px 16px rgba(15, 23, 42, 0.05)',
            overflow: 'hidden',
            marginBottom: '20px'
          }}
        >
          {/* Card Top Banner */}
          <div style={{ background: 'linear-gradient(135deg, #1E1B4B 0%, #312E81 100%)', color: '#FFFFFF', padding: '22px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px', marginBottom: '10px' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(255,255,255,0.15)', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                <Award size={14} />
                Final Assessment
              </div>
              {courseCode && (
                <span style={{ fontSize: '12px', color: '#CBD5E1', fontWeight: 600 }}>
                  Course: {courseCode}
                </span>
              )}
            </div>

            <h2 style={{ fontSize: '22px', fontWeight: 800, margin: '0 0 6px 0', color: '#FFFFFF', lineHeight: 1.3 }}>
              {lectureTitle}
            </h2>

            <p style={{ margin: 0, fontSize: '13px', color: '#CBD5E1', lineHeight: 1.5 }}>
              Comprehensive evaluation of conceptual understanding, mechanisms, and application grounded directly in this lecture.
            </p>

            {/* Covered Concepts Row */}
            {concepts && concepts.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '14px' }}>
                <span style={{ fontSize: '11px', color: '#94A3B8', fontWeight: 600, alignSelf: 'center', marginRight: '4px' }}>
                  Topics:
                </span>
                {concepts.map((c) => (
                  <span
                    key={c.id}
                    style={{
                      background: 'rgba(255, 255, 255, 0.1)',
                      color: '#E0E7FF',
                      padding: '3px 9px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: 600
                    }}
                  >
                    {c.title}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Quick Metrics Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', padding: '12px 18px', textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A' }}>7</div>
              <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>Questions Total</div>
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A' }}>4 MCQ + 3 SA</div>
              <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>Question Mix</div>
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A' }}>35 Pts</div>
              <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>Partial Credit</div>
            </div>
          </div>

          {/* Card Body & Actions */}
          <div style={{ padding: '22px 24px' }}>
            {/* In-Progress Notification Banner */}
            {inProgress && (
              <div style={{ background: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: '8px', padding: '12px 16px', marginBottom: '18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <div style={{ fontWeight: 700, color: '#92400E', fontSize: '13px' }}>
                    Assessment in progress ({inProgress.difficulty.toUpperCase()})
                  </div>
                  <div style={{ color: '#B45309', fontSize: '12px' }}>
                    {Object.keys(inProgress.saved_answers || {}).length} of {inProgress.total_questions} questions answered. Draft answers are preserved.
                  </div>
                </div>
                <button
                  onClick={() => handleStartAssessment(inProgress.difficulty)}
                  style={{ background: '#D97706', color: '#FFFFFF', border: 'none', padding: '8px 14px', borderRadius: '6px', fontWeight: 700, fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  Resume Assessment <ArrowRight size={14} />
                </button>
              </div>
            )}

            {/* Optional Practice Mode / Difficulty Selector */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Practice Mode / Difficulty Level:
                </span>
                <span style={{ fontSize: '11px', color: selectedCfg.badgeColor, fontWeight: 700 }}>
                  {selectedCfg.focusSummary}
                </span>
              </div>

              {/* Segmented Control */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', background: '#F1F5F9', padding: '4px', borderRadius: '10px' }}>
                {(['easy', 'moderate', 'hard'] as AssessmentDifficulty[]).map((diff) => {
                  const cfg = DIFFICULTY_CONFIG[diff];
                  const isSelected = selectedDifficulty === diff;
                  const isCompleted = statusData?.completed_difficulties.includes(diff);

                  return (
                    <button
                      key={diff}
                      type="button"
                      onClick={() => setSelectedDifficulty(diff)}
                      style={{
                        padding: '10px 8px',
                        borderRadius: '8px',
                        border: isSelected ? `2px solid ${cfg.badgeColor}` : '2px solid transparent',
                        background: isSelected ? '#FFFFFF' : 'transparent',
                        color: isSelected ? '#0F172A' : '#64748B',
                        fontWeight: isSelected ? 800 : 600,
                        fontSize: '12px',
                        cursor: 'pointer',
                        textAlign: 'center',
                        transition: 'all 0.15s ease',
                        boxShadow: isSelected ? '0 2px 6px rgba(0,0,0,0.06)' : 'none',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '2px'
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {cfg.title}
                        {isCompleted && <CheckCircle2 size={12} color="#16A34A" />}
                      </span>
                      <span style={{ fontSize: '10px', color: isSelected ? cfg.badgeColor : '#94A3B8', fontWeight: 600 }}>
                        {diff === 'easy' ? 'Foundations' : diff === 'moderate' ? 'Standard' : 'Advanced'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Primary Action Button */}
            <button
              onClick={() => handleStartAssessment(selectedDifficulty)}
              disabled={statusLoading || isGenerating}
              style={{
                width: '100%',
                padding: '14px 20px',
                borderRadius: '8px',
                border: 'none',
                background: selectedDifficulty === 'easy' ? '#16A34A' : selectedDifficulty === 'moderate' ? '#4F46E5' : '#DC2626',
                color: '#FFFFFF',
                fontWeight: 800,
                fontSize: '15px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: '0 3px 10px rgba(0,0,0,0.12)',
                transition: 'opacity 0.15s ease'
              }}
            >
              <span>Start {selectedCfg.title} Assessment (7 Questions)</span>
              <ChevronRight size={18} />
            </button>

            {/* Expandable Assessment Details */}
            <details
              style={{
                marginTop: '18px',
                background: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                padding: '12px 16px',
                fontSize: '12px',
                color: '#475569'
              }}
            >
              <summary style={{ fontWeight: 700, color: '#1E293B', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', listStyle: 'none' }}>
                <ChevronDown size={14} color="#6366F1" />
                <span>Assessment Structure, Quality & Scoring Guidelines</span>
              </summary>
              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #E2E8F0', lineHeight: 1.6 }}>
                <div style={{ marginBottom: '10px' }}>
                  <strong style={{ color: '#0F172A' }}>Section 1 (Questions 1–4): Multiple Choice Questions</strong>
                  <div>Tests conceptual recognition, mechanism identification, and application. Distractors reflect common misconceptions to diagnose learning gaps accurately.</div>
                </div>
                <div style={{ marginBottom: '10px' }}>
                  <strong style={{ color: '#0F172A' }}>Section 2 (Questions 5–7): Conceptual Short Answers</strong>
                  <div>Explain principles in your own words. Answers are evaluated with semantic rubric analysis. Partial understanding is rewarded with proportional partial credit.</div>
                </div>
                <div>
                  <strong style={{ color: '#0F172A' }}>Difficulty Coverage:</strong>
                  <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px' }}>
                    <li><strong>Easy:</strong> Foundational terminology, core definitions, and direct recall.</li>
                    <li><strong>Moderate:</strong> Operational mechanisms, comparing related ideas, and practical use cases.</li>
                    <li><strong>Hard:</strong> Edge cases, high-throughput scenarios, and system-level trade-offs.</li>
                  </ul>
                </div>
              </div>
            </details>
          </div>
        </div>

        {/* Past Attempts History Table */}
        {statusData?.attempts && statusData.attempts.length > 0 && (
          <div style={{ background: '#FFFFFF', borderRadius: '10px', border: '1px solid #E2E8F0', padding: '16px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 800, color: '#1E293B', margin: 0 }}>
                Previous Assessment Attempts ({statusData.attempts.length})
              </h4>
              <span style={{ fontSize: '11px', color: '#64748B' }}>
                All attempts are saved for progress tracking
              </span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #E2E8F0', color: '#64748B' }}>
                    <th style={{ padding: '6px 10px' }}>Attempt #</th>
                    <th style={{ padding: '6px 10px' }}>Difficulty</th>
                    <th style={{ padding: '6px 10px' }}>Status</th>
                    <th style={{ padding: '6px 10px' }}>Score</th>
                    <th style={{ padding: '6px 10px' }}>Score %</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {statusData.attempts.map((att) => (
                    <tr key={att.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 700, color: '#64748B' }}>
                        #{att.attempt_number ?? 1}
                      </td>
                      <td style={{ padding: '8px 10px', fontWeight: 700, textTransform: 'capitalize' }}>
                        {att.difficulty}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: 700,
                          background: att.status === 'submitted' ? '#DCFCE7' : '#FEF3C7',
                          color: att.status === 'submitted' ? '#15803D' : '#B45309'
                        }}>
                          {att.status === 'submitted' ? 'Completed' : 'Draft'}
                        </span>
                      </td>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>
                        {att.status === 'submitted' ? `${att.total_score} / ${att.max_score}` : '—'}
                      </td>
                      <td style={{ padding: '8px 10px', fontWeight: 700, color: att.percentage >= 70 ? '#16A34A' : '#D97706' }}>
                        {att.status === 'submitted' ? `${att.percentage}%` : '—'}
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                        {att.status === 'submitted' ? (
                          <button
                            onClick={() => handleViewPastAttempt(att.id)}
                            style={{
                              background: '#EEF2FF',
                              color: '#4F46E5',
                              border: 'none',
                              padding: '4px 10px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            View Results
                          </button>
                        ) : (
                          <button
                            onClick={() => handleStartAssessment(att.difficulty)}
                            style={{
                              background: '#FEF3C7',
                              color: '#B45309',
                              border: 'none',
                              padding: '4px 10px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            Resume
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: SCREEN 2 - EXAM INTERFACE (DIRECT & CLEAN)
  // ─────────────────────────────────────────────────────────────────────────────
  if (screen === 'exam' && activeAssessment) {
    const questions = activeAssessment.questions || [];
    const mcqs = questions.filter(q => q.type === 'mcq');
    const shorts = questions.filter(q => q.type === 'short_answer');

    const answeredCount = questions.filter(q => {
      const a = answers[q.id];
      return a && a.trim().length > 0;
    }).length;
    const unansweredCount = questions.length - answeredCount;
    const progressPct = Math.round((answeredCount / questions.length) * 100);
    const config = DIFFICULTY_CONFIG[selectedDifficulty];

    return (
      <div style={{ maxWidth: '840px', margin: '0 auto', padding: '16px 12px', fontFamily: 'inherit' }}>
        {/* Top Control Bar */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: '10px',
            border: '1px solid #E2E8F0',
            padding: '14px 18px',
            marginBottom: '20px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
            position: 'sticky',
            top: '8px',
            zIndex: 10
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    background: config.badgeBg,
                    color: config.badgeColor,
                    padding: '2px 8px',
                    borderRadius: '10px',
                    fontSize: '11px',
                    fontWeight: 800,
                    textTransform: 'uppercase'
                  }}
                >
                  {selectedDifficulty}
                </span>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
                  {lectureTitle} • Final Assessment
                </h3>
              </div>
              <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
                7 Questions Grounded in Lecture • 4 MCQs + 3 Short Answers • 35 Marks Total
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={handleSaveProgress}
                disabled={isSaving}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  background: '#F1F5F9',
                  color: '#334155',
                  border: '1px solid #CBD5E1',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                <Save size={13} />
                {isSaving ? 'Saving…' : 'Save Draft'}
              </button>

              <button
                onClick={() => setShowExitModal(true)}
                style={{
                  background: 'transparent',
                  color: '#64748B',
                  border: 'none',
                  fontSize: '11px',
                  cursor: 'pointer',
                  padding: '4px 8px'
                }}
              >
                Exit to Overview
              </button>
            </div>
          </div>

          {/* Simple Clean Progress Bar */}
          <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #F1F5F9' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', fontSize: '11px' }}>
              <span style={{ fontWeight: 700, color: '#475569' }}>
                Progress: {answeredCount} of {questions.length} answered ({progressPct}%)
              </span>
              {saveMessage ? (
                <span style={{ color: '#16A34A', fontWeight: 700 }}>✓ {saveMessage}</span>
              ) : unansweredCount > 0 ? (
                <span style={{ color: '#D97706', fontWeight: 600 }}>{unansweredCount} remaining</span>
              ) : (
                <span style={{ color: '#16A34A', fontWeight: 700 }}>All answered</span>
              )}
            </div>

            <div style={{ height: '5px', width: '100%', background: '#E2E8F0', borderRadius: '3px', overflow: 'hidden', marginBottom: '8px' }}>
              <div style={{ height: '100%', width: `${progressPct}%`, background: '#4F46E5', transition: 'width 0.25s ease' }} />
            </div>

            {/* Quick Question Jump Navigator */}
            <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
              {questions.map((q, idx) => {
                const isAns = answers[q.id] && answers[q.id].trim().length > 0;
                return (
                  <a
                    key={q.id}
                    href={`#question-${q.id}`}
                    style={{
                      width: '26px',
                      height: '26px',
                      borderRadius: '5px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '11px',
                      fontWeight: 700,
                      textDecoration: 'none',
                      background: isAns ? '#DCFCE7' : '#F1F5F9',
                      color: isAns ? '#15803D' : '#64748B',
                      border: isAns ? '1px solid #86EFAC' : '1px solid #CBD5E1'
                    }}
                  >
                    {idx + 1}
                  </a>
                );
              })}
            </div>
          </div>
        </div>

        {errorMessage && (
          <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#DC2626', padding: '10px 14px', borderRadius: '8px', marginBottom: '16px', fontSize: '13px' }}>
            {errorMessage}
          </div>
        )}

        {/* ── SECTION 1: MULTIPLE CHOICE QUESTIONS (1-4) ── */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span style={{ background: '#EEF2FF', color: '#4F46E5', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 800 }}>
              SECTION 1
            </span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
              Multiple Choice Questions (4 Questions • 5 Marks Each)
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {mcqs.map((q, idx) => {
              const currentAns = answers[q.id] || '';
              return (
                <div
                  key={q.id}
                  id={`question-${q.id}`}
                  style={{
                    background: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px solid #E2E8F0',
                    padding: '18px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ background: '#0F172A', color: '#FFFFFF', width: '22px', height: '22px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 800 }}>
                        {idx + 1}
                      </span>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: '#64748B' }}>
                        {q.concept_title ? `Concept: ${q.concept_title}` : 'Lecture Concept'}
                      </span>
                    </div>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#4F46E5', background: '#EEF2FF', padding: '2px 6px', borderRadius: '4px' }}>
                      5.0 Marks
                    </span>
                  </div>

                  <p style={{ fontSize: '14px', fontWeight: 600, color: '#1E293B', lineHeight: 1.5, margin: '0 0 14px 0' }}>
                    {q.question_text}
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {(q.options || []).map((opt, oIdx) => {
                      const isSelected = currentAns === opt || currentAns === opt[0];
                      return (
                        <label
                          key={oIdx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '10px 12px',
                            borderRadius: '6px',
                            border: isSelected ? '2px solid #4F46E5' : '1px solid #E2E8F0',
                            background: isSelected ? '#EEF2FF' : '#F8FAFC',
                            cursor: 'pointer',
                            transition: 'all 0.12s ease'
                          }}
                        >
                          <input
                            type="radio"
                            name={`q_${q.id}`}
                            value={opt}
                            checked={isSelected}
                            onChange={() => handleAnswerChange(q.id, opt)}
                            style={{ accentColor: '#4F46E5', width: '15px', height: '15px' }}
                          />
                          <span style={{ fontSize: '13px', color: isSelected ? '#1E1B4B' : '#334155', fontWeight: isSelected ? 700 : 500 }}>
                            {opt}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── SECTION 2: SHORT ANSWER QUESTIONS (5-7) ── */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span style={{ background: '#FEF3C7', color: '#B45309', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 800 }}>
              SECTION 2
            </span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
              Conceptual Short Answer Questions (3 Questions • 5 Marks Each)
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {shorts.map((q, idx) => {
              const currentAns = answers[q.id] || '';
              const wordCount = currentAns.trim() ? currentAns.trim().split(/\s+/).length : 0;

              return (
                <div
                  key={q.id}
                  id={`question-${q.id}`}
                  style={{
                    background: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px solid #E2E8F0',
                    padding: '18px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ background: '#0F172A', color: '#FFFFFF', width: '22px', height: '22px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 800 }}>
                        {idx + 5}
                      </span>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: '#64748B' }}>
                        {q.concept_title ? `Concept: ${q.concept_title}` : 'Lecture Concept'}
                      </span>
                    </div>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#B45309', background: '#FEF3C7', padding: '2px 6px', borderRadius: '4px' }}>
                      5.0 Marks (Rubric Evaluated)
                    </span>
                  </div>

                  <p style={{ fontSize: '14px', fontWeight: 600, color: '#1E293B', lineHeight: 1.5, margin: '0 0 10px 0' }}>
                    {q.question_text}
                  </p>

                  <div style={{ fontSize: '11px', color: '#64748B', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <Sparkles size={12} color="#6366F1" />
                    Explain in your own words. The semantic evaluator recognizes valid analogies, alternative terms, and awards partial credit.
                  </div>

                  <textarea
                    rows={4}
                    value={currentAns}
                    onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                    placeholder="Write your explanation here..."
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      padding: '10px 12px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '13px',
                      lineHeight: 1.5,
                      fontFamily: 'inherit',
                      outline: 'none',
                      resize: 'vertical',
                      background: '#F8FAFC'
                    }}
                  />

                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px', fontSize: '11px', color: '#94A3B8' }}>
                    {wordCount} words
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Sticky Submit Bar */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: '10px',
            border: '1px solid #E2E8F0',
            padding: '14px 18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 3px 10px rgba(0,0,0,0.05)'
          }}
        >
          <div>
            <div style={{ fontWeight: 700, color: '#0F172A', fontSize: '13px' }}>
              Ready to submit your assessment?
            </div>
            <div style={{ fontSize: '11px', color: unansweredCount > 0 ? '#D97706' : '#16A34A' }}>
              {unansweredCount > 0
                ? `${unansweredCount} question(s) remaining. Unanswered questions receive 0 points.`
                : 'All 7 questions answered! Click submit to calculate rubric score.'}
            </div>
          </div>

          <button
            onClick={handlePreSubmit}
            disabled={isSubmitting}
            style={{
              background: '#4F46E5',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '6px',
              padding: '10px 20px',
              fontWeight: 800,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 6px rgba(79, 70, 229, 0.25)'
            }}
          >
            {isSubmitting ? 'Evaluating…' : 'Submit Assessment'}
            <Send size={14} />
          </button>
        </div>

        {/* Confirmation Modal */}
        {showConfirmModal && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
            <div style={{ background: '#FFFFFF', borderRadius: '10px', padding: '22px', maxWidth: '420px', width: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#D97706', marginBottom: '10px' }}>
                <AlertTriangle size={20} />
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
                  Unanswered Questions
                </h3>
              </div>
              <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.5, margin: '0 0 18px 0' }}>
                You have <strong>{unansweredCount} unanswered question(s)</strong> out of 7. Would you like to review them or submit now?
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  onClick={() => setShowConfirmModal(false)}
                  style={{ background: '#F1F5F9', color: '#334155', border: 'none', padding: '7px 14px', borderRadius: '6px', fontWeight: 600, fontSize: '12px', cursor: 'pointer' }}
                >
                  Return to Questions
                </button>
                <button
                  onClick={executeSubmit}
                  style={{ background: '#4F46E5', color: '#FFFFFF', border: 'none', padding: '7px 14px', borderRadius: '6px', fontWeight: 700, fontSize: '12px', cursor: 'pointer' }}
                >
                  Submit Anyway
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Exit to Overview Modal */}
        {showExitModal && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
            <div style={{ background: '#FFFFFF', borderRadius: '10px', padding: '22px', maxWidth: '400px', width: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
                Exit Assessment?
              </h3>
              <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                Your current draft answers are safely stored. You can resume this attempt anytime.
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  onClick={() => setShowExitModal(false)}
                  style={{ background: '#F1F5F9', color: '#334155', border: 'none', padding: '7px 14px', borderRadius: '6px', fontWeight: 600, fontSize: '12px', cursor: 'pointer' }}
                >
                  Stay in Exam
                </button>
                <button
                  onClick={() => {
                    handleSaveProgress();
                    setShowExitModal(false);
                    setScreen('select');
                  }}
                  style={{ background: '#0F172A', color: '#FFFFFF', border: 'none', padding: '7px 14px', borderRadius: '6px', fontWeight: 700, fontSize: '12px', cursor: 'pointer' }}
                >
                  Save & Exit
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: SCREEN 3 - RESULTS AND COMPREHENSIVE FEEDBACK
  // ─────────────────────────────────────────────────────────────────────────────
  if (screen === 'results' && results) {
    const isPassed = results.percentage >= 70;
    const config = DIFFICULTY_CONFIG[results.difficulty as AssessmentDifficulty] || DIFFICULTY_CONFIG.moderate;

    return (
      <div style={{ maxWidth: '840px', margin: '0 auto', padding: '16px 12px', fontFamily: 'inherit' }}>
        {/* Top Header Card */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: '10px',
            border: '1px solid #E2E8F0',
            padding: '20px',
            marginBottom: '20px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.03)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span
                  style={{
                    background: config.badgeBg,
                    color: config.badgeColor,
                    padding: '3px 10px',
                    borderRadius: '10px',
                    fontSize: '11px',
                    fontWeight: 800,
                    textTransform: 'uppercase'
                  }}
                >
                  {results.difficulty} Assessment
                </span>
                {results.attempt_number && results.attempt_number > 1 && (
                  <span style={{
                    fontSize: '11px',
                    color: '#64748B',
                    background: '#F1F5F9',
                    padding: '2px 8px',
                    borderRadius: '8px',
                    fontWeight: 700
                  }}>
                    Attempt #{results.attempt_number}
                  </span>
                )}
                <span style={{ fontSize: '12px', color: '#64748B' }}>
                  Submitted {results.submitted_at ? new Date(results.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}
                </span>
              </div>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: '#0F172A' }}>
                Final Assessment Evaluation Report
              </h2>
              <div style={{ fontSize: '13px', color: '#64748B', marginTop: '2px' }}>
                {lectureTitle}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {/* 1. Retake Assessment */}
              <button
                onClick={handleRetakeAssessment}
                disabled={isRetaking}
                style={{
                  background: config.badgeColor,
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '7px 14px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: isRetaking ? 'wait' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  opacity: isRetaking ? 0.7 : 1
                }}
              >
                <RotateCcw size={13} />
                {isRetaking ? 'Generating…' : `Retake ${config.title} Assessment`}
              </button>

              {/* 2. Review Weak Topics */}
              {results.recommended_revision.length > 0 && (
                <button
                  onClick={() => {
                    const el = document.getElementById('revision-topics');
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }}
                  style={{
                    background: '#FEF3C7',
                    color: '#92400E',
                    border: '1px solid #FCD34D',
                    borderRadius: '6px',
                    padding: '7px 14px',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <BookOpen size={13} />
                  Review Weak Topics ({results.recommended_revision.length})
                </button>
              )}

              {/* 3. Back to Lecture */}
              {onBackToLecture && (
                <button
                  onClick={onBackToLecture}
                  style={{
                    background: '#F1F5F9',
                    color: '#334155',
                    border: '1px solid #CBD5E1',
                    borderRadius: '6px',
                    padding: '7px 12px',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <ChevronRight size={13} />
                  Back to Lecture
                </button>
              )}

              {/* 4. Practice Another Level (change difficulty) */}
              <button
                onClick={() => setScreen('select')}
                style={{
                  background: '#F8FAFC',
                  color: '#64748B',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  padding: '7px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                Practice Another Level
              </button>
            </div>
          </div>

          {/* Score Summary Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px' }}>
            <div style={{ background: isPassed ? '#F0FDF4' : '#FEF3C7', border: `1px solid ${isPassed ? '#86EFAC' : '#FCD34D'}`, borderRadius: '8px', padding: '14px', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: isPassed ? '#166534' : '#92400E', textTransform: 'uppercase', marginBottom: '2px' }}>
                Total Score
              </div>
              <div style={{ fontSize: '24px', fontWeight: 900, color: isPassed ? '#16A34A' : '#D97706' }}>
                {results.total_score} <span style={{ fontSize: '14px', fontWeight: 600 }}>/ {results.max_score}</span>
              </div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: isPassed ? '#15803D' : '#B45309', marginTop: '2px' }}>
                {results.percentage}% ({isPassed ? 'Passed' : 'Needs Review'})
              </div>
            </div>

            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '14px', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', marginBottom: '2px' }}>
                Section 1 (MCQs)
              </div>
              <div style={{ fontSize: '24px', fontWeight: 900, color: '#1E293B' }}>
                {results.mcq_correct_count} <span style={{ fontSize: '14px', fontWeight: 600 }}>/ {results.mcq_total_count}</span>
              </div>
              <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                {Math.round((results.mcq_correct_count / (results.mcq_total_count || 1)) * 100)}% accuracy
              </div>
            </div>

            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '14px', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', marginBottom: '2px' }}>
                Section 2 (Short Answers)
              </div>
              <div style={{ fontSize: '24px', fontWeight: 900, color: '#1E293B' }}>
                {results.short_score} <span style={{ fontSize: '14px', fontWeight: 600 }}>/ {results.short_max_score}</span>
              </div>
              <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                Rubric graded with partial marks
              </div>
            </div>
          </div>
        </div>

        {/* Concepts Understood vs Partially Understood vs Needing Improvement */}
        {(() => {
          const partiallyUnderstoodList = results.concepts_partially_understood ?? Array.from(
            new Set(
              results.question_results
                .filter(qr => qr.verdict === 'partial' || (qr.percentage >= 35 && qr.percentage < 70))
                .map(qr => qr.concept_title)
                .filter(title => title && !results.concepts_understood.includes(title))
            )
          );

          return (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', marginBottom: '20px' }}>
              {/* Understood Card */}
              <div style={{ background: '#FFFFFF', borderRadius: '8px', border: '1px solid #DCFCE7', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <CheckCircle2 size={16} color="#16A34A" />
                  <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 800, color: '#166534' }}>
                    Concepts Understood ({results.concepts_understood.length})
                  </h4>
                </div>
                {results.concepts_understood.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {results.concepts_understood.map((c, i) => (
                      <span key={i} style={{ background: '#DCFCE7', color: '#166534', padding: '3px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 700 }}>
                        ✓ {c}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: '#64748B' }}>None fully mastered (&ge;70%). Review sections below.</div>
                )}
              </div>

              {/* Partially Understood Card */}
              <div style={{ background: '#FFFFFF', borderRadius: '8px', border: '1px solid #FEF3C7', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <Sparkles size={16} color="#D97706" />
                  <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 800, color: '#92400E' }}>
                    Partially Understood ({partiallyUnderstoodList.length})
                  </h4>
                </div>
                {partiallyUnderstoodList.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {partiallyUnderstoodList.map((c, i) => (
                      <span key={i} style={{ background: '#FEF3C7', color: '#92400E', padding: '3px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 700 }}>
                        ◐ {c}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: '#64748B' }}>No concepts in partial range (35%–69%).</div>
                )}
              </div>

              {/* Needs Improvement Card */}
              <div style={{ background: '#FFFFFF', borderRadius: '8px', border: '1px solid #FEE2E2', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <AlertTriangle size={16} color="#DC2626" />
                  <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 800, color: '#991B1B' }}>
                    Needs Improvement ({results.concepts_needing_improvement.length})
                  </h4>
                </div>
                {results.concepts_needing_improvement.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {results.concepts_needing_improvement.map((c, i) => (
                      <span key={i} style={{ background: '#FEE2E2', color: '#991B1B', padding: '3px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 700 }}>
                        ⚠ {c}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: '#16A34A', fontWeight: 600 }}>All concepts met baseline understanding!</div>
                )}
              </div>
            </div>
          );
        })()}

        {/* Recommended Revision Topics with Video Seeker */}
        {results.recommended_revision.length > 0 && (
          <div id="revision-topics" style={{ background: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0', padding: '16px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
              <BookOpen size={16} color="#4F46E5" />
              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 800, color: '#0F172A' }}>
                Recommended Lecture Revision Topics
              </h4>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {results.recommended_revision.map((rev, rIdx) => {
                const mins = Math.floor(rev.timestamp / 60);
                const secs = Math.floor(rev.timestamp % 60);
                const tsStr = `${mins}:${secs < 10 ? '0' : ''}${secs}`;

                return (
                  <div key={rIdx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F8FAFC', padding: '10px 14px', borderRadius: '6px', border: '1px solid #E2E8F0', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '13px', color: '#1E293B' }}>
                        {rev.concept_title}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>
                        {rev.reason}
                      </div>
                    </div>
                    {onSeekToTimestamp && (
                      <button
                        onClick={() => onSeekToTimestamp(rev.timestamp)}
                        style={{
                          background: '#4F46E5',
                          color: '#FFFFFF',
                          border: 'none',
                          padding: '5px 10px',
                          borderRadius: '5px',
                          fontSize: '11px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        Watch at {tsStr}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Question-by-Question Detailed Review */}
        <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', margin: '0 0 14px 0' }}>
          Detailed Question-by-Question Review
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {results.question_results.map((qr, idx) => {
            const isMcq = qr.type === 'mcq';
            const isCorrect = qr.is_correct;
            const isPartial = qr.verdict === 'partial';

            return (
              <div
                key={qr.question_id}
                style={{
                  background: '#FFFFFF',
                  borderRadius: '8px',
                  border: isCorrect ? '1px solid #86EFAC' : isPartial ? '1px solid #FCD34D' : '1px solid #FCA5A5',
                  padding: '16px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                      background: isCorrect ? '#16A34A' : isPartial ? '#D97706' : '#DC2626',
                      color: '#FFFFFF',
                      width: '22px', height: '22px', borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '11px', fontWeight: 800
                    }}>
                      {idx + 1}
                    </span>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                      {isMcq ? 'Multiple Choice' : 'Short Answer'} • Concept: {qr.concept_title}
                    </span>
                  </div>

                  <span style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: isCorrect ? '#DCFCE7' : isPartial ? '#FEF3C7' : '#FEE2E2',
                    color: isCorrect ? '#166534' : isPartial ? '#92400E' : '#991B1B'
                  }}>
                    {qr.score} / {qr.max_score} Marks ({qr.verdict.toUpperCase()})
                  </span>
                </div>

                <p style={{ fontSize: '14px', fontWeight: 600, color: '#0F172A', margin: '0 0 10px 0' }}>
                  {qr.question_text}
                </p>

                {/* Student Answer */}
                <div style={{ background: '#F8FAFC', padding: '10px 12px', borderRadius: '6px', marginBottom: '10px', fontSize: '13px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', marginBottom: '3px' }}>
                    Your Answer:
                  </div>
                  <div style={{
                    color: isCorrect ? '#166534' : '#1E293B',
                    fontWeight: isCorrect ? 600 : 400,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    lineHeight: 1.5
                  }}>
                    {qr.student_answer}
                  </div>
                </div>

                {/* Correct Answer & Explanation */}
                <div style={{ background: '#F0FDF4', border: '1px solid #DCFCE7', padding: '10px 12px', borderRadius: '6px', marginBottom: '10px', fontSize: '13px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#166534', marginBottom: '3px' }}>
                    Reference / Correct Answer:
                  </div>
                  <div style={{ color: '#14532D', fontWeight: 600, whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.5 }}>
                    {qr.correct_answer}
                  </div>
                  {qr.explanation && (
                    <div style={{ color: '#166534', fontSize: '12px', marginTop: '6px', lineHeight: 1.45, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      <strong>Explanation:</strong> {qr.explanation}
                    </div>
                  )}
                </div>

                {/* Rubric Breakdown for Short Answers */}
                {!isMcq && qr.rubric_breakdown && qr.rubric_breakdown.length > 0 && (
                  <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', fontWeight: 800, color: '#334155', textTransform: 'uppercase', marginBottom: '6px' }}>
                      Assessment Criteria & Rubric Breakdown:
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                      <thead>
                        <tr style={{ background: '#F1F5F9', color: '#475569', textAlign: 'left' }}>
                          <th style={{ padding: '6px 8px' }}>Criterion</th>
                          <th style={{ padding: '6px 8px' }}>Status</th>
                          <th style={{ padding: '6px 8px', textAlign: 'right' }}>Points</th>
                        </tr>
                      </thead>
                      <tbody>
                        {qr.rubric_breakdown.map((r, rIdx) => {
                          const earned = typeof r.points_awarded === 'number' ? r.points_awarded : 0;
                          const maxPts = r.max_points || (r as any).points_possible || 2.5;
                          return (
                            <tr key={rIdx} style={{ borderBottom: '1px solid #F1F5F9' }}>
                              <td style={{ padding: '6px 8px', color: '#1E293B' }}>
                                <div style={{ fontWeight: 600 }}>{r.criterion}</div>
                                {r.notes && (
                                  <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px', lineHeight: 1.35 }}>
                                    {r.notes}
                                  </div>
                                )}
                              </td>
                              <td style={{ padding: '6px 8px', verticalAlign: 'top' }}>
                                <span style={{
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  background: r.status === 'correct' ? '#DCFCE7' : r.status === 'partial' ? '#FEF3C7' : '#FEE2E2',
                                  color: r.status === 'correct' ? '#166534' : r.status === 'partial' ? '#92400E' : '#991B1B'
                                }}>
                                  {r.status.toUpperCase()}
                                </span>
                              </td>
                              <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700, color: '#0F172A', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                                {earned} / {maxPts}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Structured Feedback Cards for Short Answer */}
                {!isMcq && (qr.what_understood || qr.what_missing || qr.how_to_improve) && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px', marginTop: '10px' }}>
                    {qr.what_understood && (
                      <div style={{ background: '#F0FDF4', border: '1px solid #DCFCE7', borderRadius: '6px', padding: '8px 10px', fontSize: '11px' }}>
                        <strong style={{ color: '#166534' }}>✓ What You Understood:</strong>
                        <div style={{ color: '#14532D', marginTop: '2px' }}>{qr.what_understood}</div>
                      </div>
                    )}
                    {qr.what_missing && (
                      <div style={{ background: '#FEF3C7', border: '1px solid #FCD34D', borderRadius: '6px', padding: '8px 10px', fontSize: '11px' }}>
                        <strong style={{ color: '#92400E' }}>⚠ What Was Missing:</strong>
                        <div style={{ color: '#78350F', marginTop: '2px' }}>{qr.what_missing}</div>
                      </div>
                    )}
                    {qr.how_to_improve && (
                      <div style={{ background: '#EEF2FF', border: '1px solid #C7D2FE', borderRadius: '6px', padding: '8px 10px', fontSize: '11px' }}>
                        <strong style={{ color: '#4338CA' }}>💡 How to Improve:</strong>
                        <div style={{ color: '#312E81', marginTop: '2px' }}>{qr.how_to_improve}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return null;
};

export default AssessmentPanel;
