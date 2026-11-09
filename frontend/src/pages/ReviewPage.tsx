import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { MisconceptionReviewData } from '../types';
import {
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Brain,
  FileQuestion,
  RefreshCw,
  Send,
  Clock,
  BookOpen
} from 'lucide-react';

interface ReviewPageProps {
  misconceptionId: number;
  onBack: () => void;
  onGoToLecture?: (lectureId: number) => void;
}

export const ReviewPage: React.FC<ReviewPageProps> = ({
  misconceptionId,
  onBack,
  onGoToLecture,
}) => {
  const [data, setData] = useState<MisconceptionReviewData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedOption, setSelectedOption] = useState<string>('');
  const [shortAnswer, setShortAnswer] = useState<string>('');
  const [resolving, setResolving] = useState<boolean>(false);
  const [result, setResult] = useState<{
    is_correct: boolean;
    feedback_reason: string;
    new_status: string;
    new_severity_level: string;
    new_severity_score: number;
  } | null>(null);

  const loadReview = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.misconceptions.getReview(misconceptionId);
      setData(resp);
    } catch (err: any) {
      setError(err.message || 'Failed to load misconception review data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReview();
  }, [misconceptionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data?.review_checkpoint) return;
    const answer =
      data.review_checkpoint.question_type === 'mcq' ? selectedOption : shortAnswer;
    if (!answer.trim()) return;

    setResolving(true);
    try {
      const resp = await api.misconceptions.resolve(misconceptionId, {
        checkpoint_id: data.review_checkpoint.id,
        student_answer: answer.trim(),
      });
      setResult(resp);
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setResolving(false);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Brain size={36} className="spin-animation" style={{ color: 'var(--accent-purple)' }} />
        <div style={{ marginTop: '16px', fontSize: '16px', fontWeight: 600 }}>
          Synthesizing targeted review explanation & diagnostic checkpoint...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card" style={{ maxWidth: '600px', margin: '40px auto', textAlign: 'center' }}>
        <AlertCircle size={36} color="#DC2626" style={{ margin: '0 auto 12px' }} />
        <h2 style={{ fontSize: '20px', fontWeight: 800 }}>Error Loading Review</h2>
        <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>{error || 'Review data missing.'}</p>
        <button className="btn btn-primary btn-sm" style={{ marginTop: '20px' }} onClick={onBack}>
          <ArrowLeft size={14} />
          <span>Return</span>
        </button>
      </div>
    );
  }

  const { misconception, concept_title, transcript_snippet, previous_bad_answer, why_problematic, clarification_explanation, review_checkpoint } = data;

  return (
    <div style={{ maxWidth: '840px', margin: '0 auto', paddingBottom: '60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <button
          id="btn-back-misconceptions"
          className="btn btn-secondary btn-sm"
          onClick={onBack}
        >
          <ArrowLeft size={14} />
          <span>Back to Misconceptions</span>
        </button>
        <span className={`badge ${misconception.severity_level === 'High' ? 'badge-high' : misconception.severity_level === 'Medium' ? 'badge-medium' : 'badge-low'}`}>
          Current Severity: {misconception.severity_level} ({misconception.severity_score}/100)
        </span>
      </div>

      {/* Header Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, var(--primary-navy) 0%, var(--navy-800) 100%)',
          color: 'white',
          borderRadius: 'var(--radius-xl)',
          padding: '32px',
          marginBottom: '28px',
        }}
      >
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(99, 102, 241, 0.25)', padding: '4px 12px', borderRadius: '9999px', fontSize: '12px', fontWeight: 700, marginBottom: '12px' }}>
          <Sparkles size={14} />
          <span>Active Cognitive Resolution Workflow</span>
        </div>
        <h1 style={{ fontSize: '26px', fontWeight: 800, marginBottom: '6px' }}>
          {misconception.title}
        </h1>
        <p style={{ fontSize: '14px', color: '#CBD5E1' }}>
          Concept: <strong>{concept_title}</strong> in {misconception.lecture_title}
        </p>
      </div>

      {/* Diagnosis: What happened? */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--primary-navy)', marginBottom: '14px' }}>
          Diagnostic Breakdown
        </h3>

        {previous_bad_answer && (
          <div style={{ marginBottom: '16px', background: '#FFF1F2', border: '1px solid #FECDD3', borderRadius: 'var(--radius-md)', padding: '14px' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#BE123C', textTransform: 'uppercase' }}>
              Your Previous Problematic Answer
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#9F1239', marginTop: '2px' }}>
              "{previous_bad_answer}"
            </div>
          </div>
        )}

        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '4px' }}>
            Why this is a conceptual friction point:
          </div>
          <div style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            {why_problematic}
          </div>
        </div>

        {/* Pedagogical Clarification */}
        <div
          style={{
            background: 'var(--accent-soft)',
            border: '1px solid #C7D2FE',
            borderRadius: 'var(--radius-md)',
            padding: '16px 20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 700, color: 'var(--accent-purple)', marginBottom: '4px' }}>
            <Brain size={18} />
            <span>Targeted Conceptual Clarification</span>
          </div>
          <p style={{ fontSize: '14px', color: '#1E1B4B', lineHeight: 1.6 }}>
            {clarification_explanation}
          </p>
        </div>
      </div>

      {/* Original Lecture Context Snippet */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={16} color="var(--accent-purple)" />
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--primary-navy)' }}>
              Original Lecture Segment ({formatTime(data.concept_start_time)} - {formatTime(data.concept_end_time)})
            </h3>
          </div>
          {onGoToLecture && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onGoToLecture(misconception.lecture_id)}
            >
              Open in Player
            </button>
          )}
        </div>
        <div
          style={{
            background: 'var(--bg-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 18px',
            fontSize: '14px',
            color: 'var(--text-muted)',
            fontStyle: 'italic',
            lineHeight: 1.6,
          }}
        >
          "{transcript_snippet}"
        </div>
      </div>

      {/* Fresh Verification Checkpoint */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <FileQuestion size={18} color="var(--accent-purple)" />
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>
            Verification Checkpoint
          </h3>
        </div>

        {review_checkpoint ? (
          <form onSubmit={handleSubmit}>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '16px' }}>
              {review_checkpoint.question_text}
            </div>

            {review_checkpoint.question_type === 'mcq' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                {review_checkpoint.options.map((opt, idx) => (
                  <label
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '12px 16px',
                      borderRadius: 'var(--radius-md)',
                      background: selectedOption === opt ? 'var(--accent-soft)' : 'var(--bg-subtle)',
                      border: `1px solid ${selectedOption === opt ? 'var(--accent-purple)' : 'var(--border-subtle)'}`,
                      fontSize: '14px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <input
                      type="radio"
                      name="review-opt"
                      value={opt}
                      checked={selectedOption === opt}
                      onChange={(e) => setSelectedOption(e.target.value)}
                      style={{ accentColor: 'var(--accent-purple)' }}
                    />
                    <span>{opt}</span>
                  </label>
                ))}
              </div>
            ) : (
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="Explain how you now understand this concept..."
                  value={shortAnswer}
                  onChange={(e) => setShortAnswer(e.target.value)}
                />
              </div>
            )}

            {/* Success Celebration or Follow-up */}
            {result && (
              <div
                style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '20px',
                  background: result.is_correct ? '#F0FDF4' : '#FFF1F2',
                  border: `1px solid ${result.is_correct ? '#BBF7D0' : '#FECDD3'}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  {result.is_correct ? (
                    <CheckCircle2 size={20} color="#16A34A" />
                  ) : (
                    <AlertCircle size={20} color="#E11D48" />
                  )}
                  <span
                    style={{
                      fontSize: '15px',
                      fontWeight: 800,
                      color: result.is_correct ? '#16A34A' : '#E11D48',
                    }}
                  >
                    {result.is_correct
                      ? `Misconception Status Updated to: ${result.new_status}!`
                      : 'Needs Further Review'}
                  </span>
                </div>
                <p style={{ fontSize: '14px', color: '#334155', lineHeight: 1.5 }}>
                  {result.feedback_reason}
                </p>
                <div style={{ marginTop: '8px', fontSize: '13px', color: '#166534', fontWeight: 600 }}>
                  Adjusted Severity: {result.new_severity_level} ({result.new_severity_score} points)
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onBack}
              >
                {result ? 'Back to Tracker' : 'Review Later'}
              </button>
              <button
                id="btn-submit-review-checkpoint"
                type="submit"
                className="btn btn-primary"
                disabled={
                  resolving ||
                  (review_checkpoint.question_type === 'mcq'
                    ? !selectedOption
                    : !shortAnswer.trim())
                }
              >
                <Send size={14} />
                <span>{resolving ? 'Evaluating...' : 'Verify Resolution'}</span>
              </button>
            </div>
          </form>
        ) : (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
            No verification checkpoint required.
          </div>
        )}
      </div>
    </div>
  );
};
