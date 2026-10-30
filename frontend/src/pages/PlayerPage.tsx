import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import type { Lecture, Concept, Checkpoint, CheckpointEvaluation } from '../types';
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  HelpCircle,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Brain,
  FileQuestion,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  ArrowLeft,
  Send,
  BookOpen,
  ArrowRight,
  RefreshCw,
  Trophy,
  Award,
  CheckCircle,
  XCircle
} from 'lucide-react';

interface PlayerPageProps {
  lectureId: number;
  onBack: () => void;
  onNavigateToMisconceptions: () => void;
}

interface QuestionItem extends Checkpoint {
  conceptTitle: string;
  conceptStartTime: number;
  conceptEndTime: number;
}

interface QuestionState {
  selectedOption: string;
  shortAnswerText: string;
  confidenceLevel: number | null;
  explanationText: string;
  evaluation: CheckpointEvaluation | null;
  isAnswered: boolean;
  isRetrying: boolean;
}

export const PlayerPage: React.FC<PlayerPageProps> = ({
  lectureId,
  onBack,
  onNavigateToMisconceptions,
}) => {
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Media Player State
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [volume, setVolume] = useState<number>(0.8);
  const [isMuted, setIsMuted] = useState<boolean>(false);

  // Active Concept State & Notes State
  const [activeConceptIndex, setActiveConceptIndex] = useState<number>(0);
  const [selectedNotesConceptIndex, setSelectedNotesConceptIndex] = useState<number>(0);

  // Behavioral Telemetry
  const [conceptReplays, setConceptReplays] = useState<Record<number, number>>({});
  const [subtleWarning, setSubtleWarning] = useState<string | null>(null);

  // Unresolved Modal State
  const [showUnresolvedModal, setShowUnresolvedModal] = useState<boolean>(false);
  const [unresolvedReason, setUnresolvedReason] = useState<string>('');
  const [unresolvedSubmitting, setUnresolvedSubmitting] = useState<boolean>(false);

  // MCQ & Question State
  const [activeQIndex, setActiveQIndex] = useState<number>(0);
  const [questionStates, setQuestionStates] = useState<Record<number, QuestionState>>({});
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [showCompletionSummary, setShowCompletionSummary] = useState<boolean>(false);

  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement | null>(null);

  const loadLecture = async () => {
    setLoading(true);
    try {
      const data = await api.lectures.get(lectureId);
      setLecture(data);
      if (data.duration_seconds) {
        setDuration(data.duration_seconds);
      }
      initializeQuestionsFromLecture(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load lecture details.');
    } finally {
      setLoading(false);
    }
  };

  const loadLectureSilently = async () => {
    try {
      const data = await api.lectures.get(lectureId);
      setLecture(data);
    } catch {
      // Ignore background sync errors
    }
  };

  const initializeQuestionsFromLecture = (data: Lecture) => {
    const questions: QuestionItem[] = (data.concepts || []).flatMap((c) =>
      (c.checkpoints || []).map((chk) => ({
        ...chk,
        conceptTitle: c.title,
        conceptStartTime: c.start_time,
        conceptEndTime: c.end_time,
      }))
    );

    setQuestionStates((prev) => {
      const updated = { ...prev };
      questions.forEach((q) => {
        // If question already answered in backend, restore it unless user is currently retrying locally
        if (q.latest_attempt && !updated[q.id]?.isRetrying) {
          updated[q.id] = {
            selectedOption: q.latest_attempt.student_answer,
            shortAnswerText: q.question_type === 'short_answer' ? q.latest_attempt.student_answer : '',
            confidenceLevel: q.latest_attempt.confidence_level ?? null,
            explanationText: q.latest_attempt.explanation_text ?? '',
            evaluation: {
              checkpoint_id: q.id,
              student_answer: q.latest_attempt.student_answer,
              is_correct: q.latest_attempt.is_correct,
              confidence: q.latest_attempt.confidence_score ?? 1.0,
              feedback_reason:
                q.latest_attempt.feedback_reason ||
                (q.latest_attempt.is_correct
                  ? 'Correct understanding verified.'
                  : 'Conceptual trap detected in previous attempt.'),
              detected_misconception_note:
                q.latest_attempt.detected_misconception_note || q.target_misconception,
              correct_answer: q.correct_answer || q.latest_attempt.correct_answer,
              explanation: q.explanation || q.latest_attempt.explanation,
              attempt_number: q.latest_attempt.attempt_number ?? 1,
              concept_id: q.concept_id,
              concept_title: q.conceptTitle,
              remediation_timestamp: q.source_timestamp ?? q.conceptStartTime,
              points_awarded: q.latest_attempt.is_correct ? 10 : 0,
              misconception_created_or_updated: false,
              source_excerpt: q.source_excerpt,
              source_timestamp: q.source_timestamp,
              attempts: q.attempts,
            },
            isAnswered: true,
            isRetrying: false,
          };
        } else if (!updated[q.id]) {
          updated[q.id] = {
            selectedOption: '',
            shortAnswerText: '',
            confidenceLevel: null,
            explanationText: '',
            evaluation: null,
            isAnswered: false,
            isRetrying: false,
          };
        }
      });
      return updated;
    });
  };

  useEffect(() => {
    setActiveConceptIndex(0);
    setSelectedNotesConceptIndex(0);
    setActiveQIndex(0);
    setCurrentTime(0);
    setIsPlaying(false);
    setShowCompletionSummary(false);
    setSubtleWarning(null);
    setError(null);
    loadLecture();
  }, [lectureId]);

  const concepts = lecture?.concepts || [];
  const activeConcept = concepts[activeConceptIndex] || null;

  // Gather flattened question set across the lecture
  const allQuestions: QuestionItem[] = concepts.flatMap((c) =>
    (c.checkpoints || []).map((chk) => ({
      ...chk,
      conceptTitle: c.title,
      conceptStartTime: c.start_time,
      conceptEndTime: c.end_time,
    }))
  );

  const currentQ: QuestionItem | undefined = allQuestions[activeQIndex];
  const currentQState: QuestionState | undefined = currentQ ? questionStates[currentQ.id] : undefined;

  // Sync active concept during playback without wiping quiz question states!
  useEffect(() => {
    if (!concepts || concepts.length === 0) return;
    const foundIndex = concepts.findIndex(
      (c, idx) =>
        (currentTime >= c.start_time && currentTime < c.end_time) ||
        (idx === concepts.length - 1 && currentTime >= c.start_time)
    );
    if (foundIndex !== -1 && foundIndex !== activeConceptIndex) {
      setActiveConceptIndex(foundIndex);
      setSelectedNotesConceptIndex(foundIndex);
    }
  }, [currentTime, concepts]);

  // Telemetry handlers
  const handleSeek = (newTime: number) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const jumpToConcept = (conceptIndex: number) => {
    const target = concepts[conceptIndex];
    if (!target) return;

    setActiveConceptIndex(conceptIndex);
    setSelectedNotesConceptIndex(conceptIndex);

    handleSeek(target.start_time);
    if (mediaRef.current && mediaRef.current.paused) {
      mediaRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleReplayConcept = async () => {
    if (!activeConcept) return;

    const currentReplays = (conceptReplays[activeConcept.id] || 0) + 1;
    setConceptReplays({ ...conceptReplays, [activeConcept.id]: currentReplays });

    try {
      const res = await api.playback.recordEvent({
        lecture_id: lectureId,
        concept_id: activeConcept.id,
        event_type: 'replay',
        timestamp_in_media: activeConcept.start_time,
        details: { replay_count: currentReplays },
      });

      if (res.replay_signal_triggered) {
        setSubtleWarning(res.message || 'This concept may need another review.');
      }
    } catch (e) {
      console.error('Failed to log replay event', e);
    }

    handleSeek(activeConcept.start_time);
    if (mediaRef.current && mediaRef.current.paused) {
      mediaRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleReviewConcept = async (timestamp?: number) => {
    const targetTime = timestamp !== undefined ? timestamp : (currentQ?.conceptStartTime ?? 0);
    handleSeek(targetTime);
    if (mediaRef.current && mediaRef.current.paused) {
      mediaRef.current.play().catch(() => {});
      setIsPlaying(true);
    }

    if (currentQ?.concept_id) {
      try {
        await api.playback.recordEvent({
          lecture_id: lectureId,
          concept_id: currentQ.concept_id,
          event_type: 'remediation_replay',
          timestamp_in_media: targetTime,
          details: { question_id: currentQ.id, reason: 'review_concept_click' },
        });
      } catch (e) {
        console.error('Failed to log review event', e);
      }
    }

    setSubtleWarning(
      `Replaying lecture section for '${currentQ?.conceptTitle || 'concept'}' at ${formatTime(targetTime)}.`
    );
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleMarkUnresolved = async () => {
    if (!activeConcept) return;
    setUnresolvedSubmitting(true);
    try {
      await api.playback.markUnresolved({
        lecture_id: lectureId,
        concept_id: activeConcept.id,
        timestamp_in_media: currentTime,
        reason: unresolvedReason,
      });
      setShowUnresolvedModal(false);
      setUnresolvedReason('');
      setSubtleWarning(`Concept flagged as unresolved (+3 severity points recorded).`);
      loadLectureSilently();
    } catch (err: any) {
      alert(`Could not mark concept: ${err.message}`);
    } finally {
      setUnresolvedSubmitting(false);
    }
  };

  // MCQ Option selection & answer handling
  const handleSelectOption = (opt: string) => {
    if (!currentQ) return;
    setQuestionStates((prev) => ({
      ...prev,
      [currentQ.id]: {
        ...(prev[currentQ.id] || {
          shortAnswerText: '',
          confidenceLevel: null,
          explanationText: '',
          evaluation: null,
          isAnswered: false,
          isRetrying: false,
        }),
        selectedOption: opt,
      },
    }));
  };

  const handleShortAnswerChange = (val: string) => {
    if (!currentQ) return;
    setQuestionStates((prev) => ({
      ...prev,
      [currentQ.id]: {
        ...(prev[currentQ.id] || {
          selectedOption: '',
          confidenceLevel: null,
          explanationText: '',
          evaluation: null,
          isAnswered: false,
          isRetrying: false,
        }),
        shortAnswerText: val,
      },
    }));
  };

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentQ) return;

    const qState = questionStates[currentQ.id];
    const answer = currentQ.question_type === 'mcq' ? qState?.selectedOption : qState?.shortAnswerText;

    if (!answer || !answer.trim()) {
      alert('Please select an option before submitting.');
      return;
    }

    setEvaluating(true);
    try {
      const result = await api.checkpoints.submitAnswer({
        checkpoint_id: currentQ.id,
        student_answer: answer.trim(),
        confidence_level: qState?.confidenceLevel ?? undefined,
        explanation_text: qState?.explanationText ?? undefined,
      });

      setQuestionStates((prev) => ({
        ...prev,
        [currentQ.id]: {
          ...(prev[currentQ.id] || {}),
          selectedOption: currentQ.question_type === 'mcq' ? answer.trim() : '',
          shortAnswerText: currentQ.question_type === 'short_answer' ? answer.trim() : '',
          evaluation: {
            ...result,
            correct_answer: result.correct_answer || currentQ.correct_answer,
            explanation: result.explanation || currentQ.explanation,
            concept_title: currentQ.conceptTitle,
            remediation_timestamp:
              result.remediation_timestamp ?? currentQ.source_timestamp ?? currentQ.conceptStartTime,
          },
          isAnswered: true,
          isRetrying: false,
        },
      }));

      if (result.misconception_created_or_updated) {
        setSubtleWarning(
          `Misconception logged in persistent tracking (${result.new_severity_level} priority). Saved in database.`
        );
      }
      loadLectureSilently();
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  const handleTryAgain = (qId: number) => {
    setQuestionStates((prev) => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || {}),
        selectedOption: '',
        shortAnswerText: '',
        isRetrying: true,
      },
    }));
  };

  const handleCancelRetry = (qId: number) => {
    setQuestionStates((prev) => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || {}),
        isRetrying: false,
      },
    }));
  };

  const handlePrevQuestion = () => {
    if (activeQIndex > 0) {
      setActiveQIndex(activeQIndex - 1);
      setShowCompletionSummary(false);
    }
  };

  const handleNextQuestion = () => {
    if (activeQIndex < allQuestions.length - 1) {
      setActiveQIndex(activeQIndex + 1);
      setShowCompletionSummary(false);
    } else {
      setShowCompletionSummary(true);
    }
  };

  const handleJumpToQuestion = (idx: number) => {
    setActiveQIndex(idx);
    setShowCompletionSummary(false);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // Completion metrics calculation
  const totalQCount = allQuestions.length;
  const answeredQuestions = allQuestions.filter((q) => questionStates[q.id]?.isAnswered);
  const correctQuestions = allQuestions.filter(
    (q) => questionStates[q.id]?.isAnswered && questionStates[q.id]?.evaluation?.is_correct
  );
  const incorrectQuestions = allQuestions.filter(
    (q) => questionStates[q.id]?.isAnswered && !questionStates[q.id]?.evaluation?.is_correct
  );

  const answeredQCount = answeredQuestions.length;
  const correctQCount = correctQuestions.length;
  const incorrectQCount = incorrectQuestions.length;
  const accuracyPct = totalQCount > 0 ? Math.round((correctQCount / totalQCount) * 100) : 0;

  // Concepts status breakdown
  const conceptSummaries = concepts.map((c) => {
    const cQuestions = allQuestions.filter((q) => q.concept_id === c.id);
    const cAnswered = cQuestions.filter((q) => questionStates[q.id]?.isAnswered);
    const cCorrect = cQuestions.filter(
      (q) => questionStates[q.id]?.isAnswered && questionStates[q.id]?.evaluation?.is_correct
    );
    const isMastered = cQuestions.length > 0 && cCorrect.length === cQuestions.length;
    const hasMistakes = cQuestions.some(
      (q) => questionStates[q.id]?.isAnswered && !questionStates[q.id]?.evaluation?.is_correct
    );
    return {
      concept: c,
      total: cQuestions.length,
      answered: cAnswered.length,
      correct: cCorrect.length,
      isMastered,
      hasMistakes,
    };
  });

  const masteredConcepts = conceptSummaries.filter((cs) => cs.isMastered);
  const weakConcepts = conceptSummaries.filter((cs) => cs.hasMistakes || cs.answered < cs.total);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Brain size={36} className="spin-animation" style={{ color: 'var(--accent-purple)' }} />
        <div style={{ marginTop: '16px', fontSize: '16px', fontWeight: 600, color: 'var(--primary-navy)' }}>
          Loading lecture content & restoring saved questions...
        </div>
      </div>
    );
  }

  if (error || !lecture) {
    return (
      <div className="card" style={{ maxWidth: '600px', margin: '40px auto', textAlign: 'center' }}>
        <AlertCircle size={36} color="#DC2626" style={{ margin: '0 auto 12px' }} />
        <h2 style={{ fontSize: '20px', fontWeight: 800 }}>Error Loading Lecture</h2>
        <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>{error || 'Lecture not found.'}</p>
        <button className="btn btn-primary btn-sm" style={{ marginTop: '20px' }} onClick={onBack}>
          <ArrowLeft size={14} />
          <span>Return to Dashboard</span>
        </button>
      </div>
    );
  }

  // If lecture processing failed in backend
  if (lecture.status === 'failed') {
    return (
      <div className="card" style={{ maxWidth: '640px', margin: '40px auto', textAlign: 'center', padding: '36px' }}>
        <AlertTriangle size={42} color="#DC2626" style={{ margin: '0 auto 16px' }} />
        <h2 style={{ fontSize: '22px', fontWeight: 800, color: '#991B1B' }}>Lecture Processing Failed</h2>
        <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: '8px', padding: '16px', margin: '16px 0', textAlign: 'left', fontSize: '13px', color: '#7F1D1D', lineHeight: 1.5 }}>
          {lecture.processing_error || 'MindTrace could not transcribe speech or extract genuine concepts from this lecture recording.'}
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
          MindTrace transcribes speech locally using Faster-Whisper on CPU with zero external APIs. If transcription failed, please ensure the audio contains clear spoken lecture dialogue, or provide an accompanying transcript file (.srt, .vtt, or text notes).
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
          <button className="btn btn-secondary btn-sm" onClick={onBack}>
            <ArrowLeft size={14} />
            <span>Back to Lectures</span>
          </button>
        </div>
      </div>
    );
  }

  const notesConcept = concepts[selectedNotesConceptIndex] || activeConcept;
  const coreConceptsList =
    notesConcept?.core_concepts && notesConcept.core_concepts.length > 0
      ? notesConcept.core_concepts
      : [
          `Fundamental rule and deterministic operations of ${notesConcept?.title || 'this concept'}`,
          `Core structural invariants and input/output contracts`,
          `Predictable transformation dynamics verified across canonical test cases`,
        ];

  const confusingTopicsList =
    notesConcept?.confusing_topics && notesConcept.confusing_topics.length > 0
      ? notesConcept.confusing_topics
      : [
          `Conflating intermediate states or display side-effects with actual return values`,
          `Overlooking domain constraints or boundary edge-cases`,
          `Superficial pattern-matching without checking underlying semantic invariants`,
        ];

  const isCurrentQAnswered = Boolean(currentQState?.isAnswered && !currentQState?.isRetrying);
  const currentEvaluation = currentQState?.evaluation;

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* Top Breadcrumb & Action bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
        <button id="btn-back-dashboard" className="btn btn-secondary btn-sm" onClick={onBack}>
          <ArrowLeft size={14} />
          <span>Back to Lectures</span>
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button className="btn btn-secondary btn-sm" onClick={onNavigateToMisconceptions}>
            <AlertTriangle size={14} color="var(--priority-high-text)" />
            <span>Misconceptions ({lecture.unresolved_count} Unresolved)</span>
          </button>
        </div>
      </div>

      {subtleWarning && (
        <div
          style={{
            background: 'var(--accent-soft)',
            border: '1px solid var(--accent-purple)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 16px',
            marginBottom: '16px',
            fontSize: '13px',
            color: 'var(--primary-navy)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="var(--accent-purple)" />
            <span>{subtleWarning}</span>
          </div>
          <button
            type="button"
            onClick={() => setSubtleWarning(null)}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Grid: Player on Left, Checkpoint on Right */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: '24px', alignItems: 'start' }}>
        {/* LEFT AREA: Video/Audio Player, Concept Notes & Summary Cards, Timeline */}
        <div>
          {/* Media Player Card */}
          <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '20px' }}>
            <div style={{ position: 'relative', background: '#000000', minHeight: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {lecture.media_type === 'video' ? (
                <video
                  ref={mediaRef as React.RefObject<HTMLVideoElement>}
                  src={`${api.lectures.getMediaUrl(lectureId)}`}
                  style={{ width: '100%', maxHeight: '420px', display: 'block' }}
                  onTimeUpdate={() => {
                    if (mediaRef.current) setCurrentTime(mediaRef.current.currentTime);
                  }}
                  onLoadedMetadata={() => {
                    if (mediaRef.current && mediaRef.current.duration) {
                      setDuration(mediaRef.current.duration);
                    }
                  }}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
              ) : (
                <div style={{ padding: '40px 20px', textAlign: 'center', width: '100%', background: 'linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%)' }}>
                  <Brain size={56} color="#A78BFA" style={{ margin: '0 auto 16px' }} />
                  <div style={{ color: '#FFFFFF', fontSize: '18px', fontWeight: 800 }}>{lecture.title}</div>
                  <div style={{ color: '#94A3B8', fontSize: '13px', marginTop: '4px' }}>
                    {lecture.course_code} • Audio Lecture
                  </div>
                  <audio
                    ref={mediaRef as React.RefObject<HTMLAudioElement>}
                    src={`${api.lectures.getMediaUrl(lectureId)}`}
                    onTimeUpdate={() => {
                      if (mediaRef.current) setCurrentTime(mediaRef.current.currentTime);
                    }}
                    onLoadedMetadata={() => {
                      if (mediaRef.current && mediaRef.current.duration) {
                        setDuration(mediaRef.current.duration);
                      }
                    }}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                  />
                </div>
              )}
            </div>

            {/* Custom Control Bar */}
            <div style={{ padding: '16px 20px', background: '#090D1A', borderTop: '1px solid #1E293B' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <span style={{ fontSize: '12px', color: '#94A3B8', fontFamily: 'JetBrains Mono', minWidth: '40px' }}>
                  {formatTime(currentTime)}
                </span>
                <input
                  id="media-time-scrubber"
                  type="range"
                  min={0}
                  max={duration || 100}
                  step={0.1}
                  value={currentTime}
                  onChange={(e) => handleSeek(parseFloat(e.target.value))}
                  style={{ flex: 1, accentColor: 'var(--accent-purple)', cursor: 'pointer' }}
                />
                <span style={{ fontSize: '12px', color: '#94A3B8', fontFamily: 'JetBrains Mono', minWidth: '40px' }}>
                  {formatTime(duration)}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <button
                    id="btn-play-pause"
                    className="btn btn-accent btn-sm"
                    onClick={() => {
                      if (!mediaRef.current) return;
                      if (isPlaying) {
                        mediaRef.current.pause();
                      } else {
                        mediaRef.current.play().catch(() => {});
                      }
                    }}
                  >
                    {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                    <span>{isPlaying ? 'Pause' : 'Play'}</span>
                  </button>

                  <button
                    id="btn-replay-concept"
                    className="btn btn-secondary btn-sm"
                    style={{ background: '#1E293B', color: '#E2E8F0', borderColor: '#334155' }}
                    onClick={handleReplayConcept}
                    title="Replay this concept from beginning"
                  >
                    <RotateCcw size={14} />
                    <span>Replay Concept</span>
                    {(conceptReplays[activeConcept?.id || 0] || 0) > 0 && (
                      <span style={{ fontSize: '11px', color: 'var(--accent-purple)', fontWeight: 700 }}>
                        ({conceptReplays[activeConcept?.id || 0]})
                      </span>
                    )}
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <button
                    style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer' }}
                    onClick={() => {
                      if (!mediaRef.current) return;
                      mediaRef.current.muted = !isMuted;
                      setIsMuted(!isMuted);
                    }}
                  >
                    {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
                  </button>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={isMuted ? 0 : volume}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setVolume(val);
                      if (mediaRef.current) {
                        mediaRef.current.volume = val;
                        mediaRef.current.muted = false;
                        setIsMuted(false);
                      }
                    }}
                    style={{ width: '70px', accentColor: 'var(--accent-purple)' }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Concept Notes & Summary Cards */}
          <div className="card" style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BookOpen size={18} color="var(--accent-purple)" />
                <h3 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--primary-navy)', margin: 0 }}>
                  Concept Notes & Summary Cards
                </h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-purple)', background: 'var(--accent-soft)', padding: '2px 8px', borderRadius: 'var(--radius-full)' }}>
                  Segment {selectedNotesConceptIndex + 1} of {concepts.length}
                </span>
                {notesConcept && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '11px', padding: '3px 8px', height: '26px' }}
                    onClick={() => jumpToConcept(selectedNotesConceptIndex)}
                  >
                    <Play size={10} />
                    <span>Seek to {formatTime(notesConcept.start_time)}</span>
                  </button>
                )}
              </div>
            </div>

            {/* Segment Selector Tabs */}
            {concepts.length > 1 && (
              <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '8px', marginBottom: '14px' }}>
                {concepts.map((c, idx) => {
                  const isSelected = idx === selectedNotesConceptIndex;
                  const isPlayingThis = idx === activeConceptIndex;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setSelectedNotesConceptIndex(idx)}
                      style={{
                        padding: '5px 12px',
                        borderRadius: 'var(--radius-full)',
                        fontSize: '12px',
                        fontWeight: isSelected ? 800 : 500,
                        border: isSelected ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
                        background: isSelected ? 'var(--accent-purple)' : 'var(--bg-subtle)',
                        color: isSelected ? '#FFFFFF' : 'var(--text-muted)',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <span>{idx + 1}. {c.title.length > 22 ? c.title.slice(0, 20) + '...' : c.title}</span>
                      {isPlayingThis && (
                        <span
                          title="Now Playing"
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            background: isSelected ? '#FFFFFF' : 'var(--accent-purple)',
                            display: 'inline-block',
                          }}
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            )}

            {notesConcept && (
              <div style={{ marginBottom: '14px', paddingBottom: '12px', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                    {notesConcept.title}
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--text-light)', fontFamily: 'JetBrains Mono' }}>
                    {formatTime(notesConcept.start_time)} - {formatTime(notesConcept.end_time)}
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px', lineHeight: 1.45 }}>
                  {notesConcept.description}
                </div>
              </div>
            )}

            {/* Core Concepts vs Confusing Topics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 'var(--radius-md)', padding: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <div style={{ width: '22px', height: '22px', borderRadius: '50%', background: '#ECFDF5', border: '1px solid #A7F3D0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#059669', fontSize: '11px', fontWeight: 800 }}>
                    ✓
                  </div>
                  <div>
                    <h4 style={{ fontSize: '12px', fontWeight: 800, color: '#0F172A', margin: 0, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                      1. Core Essential Concepts
                    </h4>
                    <span style={{ fontSize: '11px', color: '#64748B' }}>Key definitions & rules</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {coreConceptsList.map((pt, pIdx) => (
                    <div key={pIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12px', color: '#334155', lineHeight: 1.45, background: '#FFFFFF', border: '1px solid #F1F5F9', borderRadius: '6px', padding: '8px 10px' }}>
                      <span style={{ color: '#10B981', fontWeight: 800, flexShrink: 0, marginTop: '1px' }}>•</span>
                      <span>{pt}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: '#FFFBEB', border: '1px solid #FEF3C7', borderRadius: 'var(--radius-md)', padding: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <div style={{ width: '22px', height: '22px', borderRadius: '50%', background: '#FEF3C7', border: '1px solid #FDE68A', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#D97706', fontSize: '11px', fontWeight: 800 }}>
                    !
                  </div>
                  <div>
                    <h4 style={{ fontSize: '12px', fontWeight: 800, color: '#92400E', margin: 0, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                      2. Common Confusing Topics
                    </h4>
                    <span style={{ fontSize: '11px', color: '#B45309' }}>Cognitive traps & pitfalls</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {confusingTopicsList.map((tr, tIdx) => (
                    <div key={tIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12px', color: '#78350F', lineHeight: 1.45, background: '#FFFFFF', border: '1px solid #FEF3C7', borderRadius: '6px', padding: '8px 10px' }}>
                      <span style={{ color: '#F59E0B', fontWeight: 800, flexShrink: 0, marginTop: '1px' }}>▲</span>
                      <span>{tr}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Concept Timeline */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                  Lecture Concept Timeline
                </h3>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  Click any concept block to jump playback and view concept notes.
                </p>
              </div>
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-purple)', background: 'var(--accent-soft)', padding: '2px 8px', borderRadius: 'var(--radius-full)' }}>
                {concepts.length} Concepts Segmented
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {concepts.map((concept, idx) => {
                const isActive = idx === activeConceptIndex;
                return (
                  <div
                    key={concept.id}
                    id={`timeline-concept-${concept.id}`}
                    className={`timeline-block ${isActive ? 'active' : ''}`}
                    onClick={() => jumpToConcept(idx)}
                  >
                    <div className="timeline-time">{formatTime(concept.start_time)}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '14px', fontWeight: 700, color: isActive ? 'var(--accent-purple)' : 'var(--primary-navy)' }}>
                          {concept.title}
                        </span>
                        {isActive && (
                          <span style={{ fontSize: '11px', background: 'var(--accent-purple)', color: 'white', padding: '1px 6px', borderRadius: '4px', fontWeight: 700 }}>
                            NOW PLAYING
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {concept.description}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-light)', fontFamily: 'JetBrains Mono' }}>
                        {formatTime(concept.end_time - concept.start_time)}
                      </span>
                      <ChevronRight size={16} color={isActive ? 'var(--accent-purple)' : 'var(--text-light)'} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT AREA: Active Concept, Mark Unresolved, MCQ Workflow & Learning Summary */}
        <div>
          {/* Active Concept Details Card */}
          <div className="card" style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-purple)', textTransform: 'uppercase' }}>
                  Current Concept ({activeConceptIndex + 1} of {concepts.length})
                </span>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)', marginTop: '2px' }}>
                  {activeConcept ? activeConcept.title : 'Loading concept...'}
                </h3>
              </div>
              <span
                className={`badge ${
                  activeConcept?.status === 'Mastered'
                    ? 'badge-resolved'
                    : activeConcept?.status === 'Needs Attention'
                    ? 'badge-high'
                    : 'badge-low'
                }`}
              >
                {activeConcept?.status || 'In Progress'}
              </span>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '16px' }}>
              {activeConcept?.description}
            </p>

            {/* Unresolved Signal Button */}
            <div
              style={{
                background: 'var(--priority-high-bg)',
                border: '1px solid var(--priority-high-border)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '10px',
              }}
            >
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--priority-high-text)' }}>
                  Feeling confused by this concept?
                </div>
                <div style={{ fontSize: '11px', color: '#991B1B' }}>
                  Records explicit misconception signal (+3 severity) in persistent database.
                </div>
              </div>
              <button
                id="btn-mark-unresolved"
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => setShowUnresolvedModal(true)}
              >
                <HelpCircle size={14} />
                <span>Mark Unresolved</span>
              </button>
            </div>
          </div>

          {/* CHECKPOINT AREA: Toggle between Question View and Completion Summary */}
          {showCompletionSummary ? (
            /* ==============================================================
               MCQ Completion & Learning Summary Screen (Section 9)
               ============================================================== */
            <div className="card" style={{ border: '2px solid var(--accent-purple)', background: '#FAFAFF' }}>
              {/* Summary Header */}
              <div style={{ textAlign: 'center', paddingBottom: '18px', borderBottom: '1px solid #E2E8F0', marginBottom: '20px' }}>
                <div
                  style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    background: accuracyPct >= 80 && answeredQCount === totalQCount ? '#DCFCE7' : '#EDE9FE',
                    color: accuracyPct >= 80 && answeredQCount === totalQCount ? '#16A34A' : 'var(--accent-purple)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '12px',
                  }}
                >
                  {accuracyPct >= 80 && answeredQCount === totalQCount ? <Trophy size={28} /> : <Award size={28} />}
                </div>
                <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary-navy)', margin: 0 }}>
                  {answeredQCount === totalQCount
                    ? accuracyPct >= 80
                      ? 'Checkpoints Mastered!'
                      : 'All Checkpoints Completed!'
                    : 'MCQ Assessment Summary'}
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px' }}>
                  {answeredQCount === totalQCount
                    ? `You have answered all ${totalQCount} diagnostic questions for '${lecture.title}'.`
                    : `Answered ${answeredQCount} of ${totalQCount} questions in this lecture.`}
                </p>
              </div>

              {/* Real Metrics Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '20px' }}>
                <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                  <div style={{ fontSize: '22px', fontWeight: 900, color: 'var(--primary-navy)' }}>{totalQCount}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Total MCQs</div>
                </div>
                <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                  <div style={{ fontSize: '22px', fontWeight: 900, color: '#16A34A' }}>{correctQCount}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Correct</div>
                </div>
                <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                  <div style={{ fontSize: '22px', fontWeight: 900, color: '#DC2626' }}>{incorrectQCount}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Incorrect</div>
                </div>
                <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                  <div style={{ fontSize: '22px', fontWeight: 900, color: 'var(--accent-purple)' }}>{accuracyPct}%</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Accuracy</div>
                </div>
              </div>

              {/* Concepts Performance Breakdown */}
              <div style={{ marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {masteredConcepts.length > 0 && (
                  <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#166534', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                      <CheckCircle size={15} color="#16A34A" />
                      <span>Concepts Answered Correctly ({masteredConcepts.length})</span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {masteredConcepts.map((cs) => (
                        <span key={cs.concept.id} style={{ background: '#DCFCE7', color: '#15803D', fontSize: '11px', padding: '3px 8px', borderRadius: '4px', fontWeight: 600 }}>
                          {cs.concept.title} ({cs.correct}/{cs.total})
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {weakConcepts.length > 0 && (
                  <div style={{ background: '#FFF1F2', border: '1px solid #FECDD3', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#9F1239', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                      <AlertTriangle size={15} color="#E11D48" />
                      <span>Concepts Needing Revision ({weakConcepts.length})</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {weakConcepts.map((cs) => (
                        <div key={cs.concept.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#FFFFFF', padding: '6px 10px', borderRadius: '6px', border: '1px solid #FFE4E6' }}>
                          <span style={{ fontSize: '12px', color: '#881337', fontWeight: 600 }}>
                            {cs.concept.title}
                          </span>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: '11px', padding: '2px 8px', height: '24px' }}
                            onClick={() => {
                              jumpToConcept(concepts.findIndex((c) => c.id === cs.concept.id));
                              setShowCompletionSummary(false);
                            }}
                          >
                            <Play size={10} />
                            <span>Seek to {formatTime(cs.concept.start_time)}</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Detailed Incorrect Questions Review List */}
              {incorrectQuestions.length > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--primary-navy)', marginBottom: '8px' }}>
                    Review Questions with Incorrect Answers ({incorrectQuestions.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
                    {incorrectQuestions.map((q) => {
                      const qIndex = allQuestions.findIndex((item) => item.id === q.id);
                      const qEval = questionStates[q.id]?.evaluation;
                      return (
                        <div key={q.id} style={{ background: '#FFFFFF', border: '1px solid #F1F5F9', borderRadius: '6px', padding: '10px 12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary-navy)' }}>
                              Q{qIndex + 1}: {q.question_text}
                            </div>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              style={{ fontSize: '11px', padding: '2px 8px', height: '24px', flexShrink: 0 }}
                              onClick={() => {
                                setActiveQIndex(qIndex);
                                setShowCompletionSummary(false);
                              }}
                            >
                              <span>Review</span>
                              <ChevronRight size={12} />
                            </button>
                          </div>
                          <div style={{ fontSize: '11px', color: '#DC2626', marginTop: '4px' }}>
                            <strong>Your Answer:</strong> {questionStates[q.id]?.selectedOption}
                          </div>
                          {qEval?.correct_answer && (
                            <div style={{ fontSize: '11px', color: '#16A34A', marginTop: '2px' }}>
                              <strong>Correct:</strong> {qEval.correct_answer}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 5 Distinct Summary Actions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', paddingTop: '14px', borderTop: '1px solid #E2E8F0' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {incorrectQuestions.length > 0 && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1, fontSize: '12px' }}
                      onClick={() => {
                        const firstIncorrectIdx = allQuestions.findIndex(
                          (q) => questionStates[q.id]?.isAnswered && !questionStates[q.id]?.evaluation?.is_correct
                        );
                        if (firstIncorrectIdx !== -1) {
                          setActiveQIndex(firstIncorrectIdx);
                          setShowCompletionSummary(false);
                        }
                      }}
                    >
                      <span>Review Incorrect Answers</span>
                    </button>
                  )}

                  {incorrectQuestions.length > 0 && (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      style={{ flex: 1, fontSize: '12px' }}
                      onClick={() => {
                        incorrectQuestions.forEach((q) => handleTryAgain(q.id));
                        const firstIncorrectIdx = allQuestions.findIndex(
                          (q) => questionStates[q.id]?.isAnswered && !questionStates[q.id]?.evaluation?.is_correct
                        );
                        if (firstIncorrectIdx !== -1) {
                          setActiveQIndex(firstIncorrectIdx);
                        }
                        setShowCompletionSummary(false);
                      }}
                    >
                      <RefreshCw size={12} />
                      <span>Retry Incorrect Questions</span>
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ flex: 1, fontSize: '12px' }}
                    onClick={() => setShowCompletionSummary(false)}
                  >
                    <span>Return to Lecture & Questions</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ flex: 1, fontSize: '12px' }}
                    onClick={onNavigateToMisconceptions}
                  >
                    <AlertTriangle size={12} color="var(--priority-high-text)" />
                    <span>View Learning Progress</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* ==============================================================
               Standard Checkpoint Question / Feedback Card
               ============================================================== */
            <div className="card">
              {/* Question Header & Navigation Pills */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileQuestion size={18} color="var(--accent-purple)" />
                  <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--primary-navy)', margin: 0 }}>
                    Concept Checkpoint
                  </h3>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-purple)', background: 'var(--accent-soft)', padding: '2px 8px', borderRadius: 'var(--radius-full)' }}>
                    Question {activeQIndex + 1} of {allQuestions.length}
                  </span>
                  {currentQ?.item_family_role && (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                        background:
                          currentQ.item_family_role === 'transfer'
                            ? '#FDF4FF'
                            : currentQ.item_family_role === 'variant'
                            ? '#F0F9FF'
                            : '#F1F5F9',
                        color:
                          currentQ.item_family_role === 'transfer'
                            ? '#A21CAF'
                            : currentQ.item_family_role === 'variant'
                            ? '#0369A1'
                            : '#475569',
                        border: `1px solid ${
                          currentQ.item_family_role === 'transfer'
                            ? '#F5D0FE'
                            : currentQ.item_family_role === 'variant'
                            ? '#BAE6FD'
                            : '#E2E8F0'
                        }`,
                      }}
                    >
                      {currentQ.item_family_role === 'transfer'
                        ? 'Near-Transfer Probe'
                        : currentQ.item_family_role === 'variant'
                        ? 'Isomorphic Variant'
                        : 'Diagnostic Original'}
                    </span>
                  )}
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '11px', padding: '2px 8px', height: '24px' }}
                    onClick={() => setShowCompletionSummary(true)}
                    title="View overall quiz summary"
                  >
                    <span>Summary</span>
                  </button>
                </div>
              </div>

              {/* Question Navigation Pills (Q1, Q2... QN) with Real Saved Status Icons */}
              {allQuestions.length > 1 && (
                <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '8px', marginBottom: '14px' }}>
                  {allQuestions.map((q, idx) => {
                    const isCurrent = activeQIndex === idx;
                    const st = questionStates[q.id];
                    const isAns = Boolean(st?.isAnswered);
                    const isCorrect = Boolean(st?.evaluation?.is_correct);

                    return (
                      <button
                        key={q.id}
                        type="button"
                        onClick={() => handleJumpToQuestion(idx)}
                        style={{
                          padding: '4px 10px',
                          borderRadius: 'var(--radius-full)',
                          fontSize: '11px',
                          fontWeight: isCurrent ? 800 : 600,
                          background: isCurrent
                            ? 'var(--accent-purple)'
                            : isAns
                            ? isCorrect
                              ? '#ECFDF5'
                              : '#FFF1F2'
                            : 'var(--bg-subtle)',
                          color: isCurrent
                            ? '#FFFFFF'
                            : isAns
                            ? isCorrect
                              ? '#059669'
                              : '#E11D48'
                            : 'var(--text-muted)',
                          border: isCurrent
                            ? '1px solid var(--accent-purple)'
                            : isAns
                            ? isCorrect
                              ? '1px solid #A7F3D0'
                              : '1px solid #FECDD3'
                            : '1px solid var(--border-subtle)',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          whiteSpace: 'nowrap',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {isAns ? (
                          isCorrect ? (
                            <CheckCircle2 size={12} color={isCurrent ? '#FFFFFF' : '#10B981'} />
                          ) : (
                            <AlertCircle size={12} color={isCurrent ? '#FFFFFF' : '#EF4444'} />
                          )
                        ) : (
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: isCurrent ? '#FFFFFF' : '#94A3B8' }} />
                        )}
                        <span>Q{idx + 1}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Concept Association Banner */}
              {currentQ && (
                <div style={{ marginBottom: '12px', fontSize: '11px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>
                    Associated Concept: <strong>{currentQ.conceptTitle}</strong>
                  </span>
                  <button
                    type="button"
                    style={{ background: 'none', border: 'none', color: 'var(--accent-purple)', fontSize: '11px', fontWeight: 600, cursor: 'pointer', padding: 0 }}
                    onClick={() => handleReviewConcept(currentQ.source_timestamp ?? currentQ.conceptStartTime)}
                  >
                    Seek to {formatTime(currentQ.source_timestamp ?? currentQ.conceptStartTime)}
                  </button>
                </div>
              )}

              {currentQ ? (
                <div>
                  {/* Question Prompt Stem */}
                  <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '14px', lineHeight: 1.45 }}>
                    {currentQ.question_text}
                  </div>

                  {/* ========================================================
                      STATE 1: Question Already Answered (Restore Saved Result)
                      ======================================================== */}
                  {isCurrentQAnswered && currentEvaluation ? (
                    <div>
                      {/* Immediate Feedback Banner */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: 'var(--radius-md)',
                          marginBottom: '16px',
                          background: currentEvaluation.is_correct ? '#F0FDF4' : '#FFF1F2',
                          border: `1px solid ${currentEvaluation.is_correct ? '#BBF7D0' : '#FECDD3'}`,
                        }}
                      >
                        {/* Status Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {currentEvaluation.is_correct ? (
                              <CheckCircle2 size={18} color="#16A34A" />
                            ) : (
                              <AlertCircle size={18} color="#E11D48" />
                            )}
                            <span style={{ fontSize: '14px', fontWeight: 800, color: currentEvaluation.is_correct ? '#16A34A' : '#E11D48' }}>
                              {currentEvaluation.is_correct ? 'Correct Answer!' : 'Incorrect Answer — Misconception Detected'}
                            </span>
                          </div>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              background: currentEvaluation.is_correct ? '#DCFCE7' : '#FFE4E6',
                              color: currentEvaluation.is_correct ? '#15803D' : '#BE123C',
                              padding: '2px 8px',
                              borderRadius: '4px',
                            }}
                          >
                            {currentEvaluation.is_correct
                              ? '+10 Points • Verified'
                              : 'Logged in Database'}
                          </span>
                        </div>

                        {/* Selected vs Correct Comparison */}
                        <div style={{ background: '#FFFFFF', borderRadius: '6px', padding: '10px 12px', marginBottom: '12px', border: '1px solid #F1F5F9' }}>
                          <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Your Selected Answer: </span>
                            <span style={{ fontWeight: 700, color: currentEvaluation.is_correct ? '#16A34A' : '#DC2626' }}>
                              {currentQState?.selectedOption || currentEvaluation.student_answer}
                            </span>
                          </div>
                          <div style={{ fontSize: '12px' }}>
                            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Correct Answer: </span>
                            <span style={{ fontWeight: 700, color: '#16A34A' }}>
                              {currentEvaluation.correct_answer || currentQ.correct_answer}
                            </span>
                          </div>
                        </div>

                        {/* Simple Explanation Grounded in Lecture */}
                        <div style={{ fontSize: '13px', color: currentEvaluation.is_correct ? '#166534' : '#881337', lineHeight: 1.5, marginBottom: '10px' }}>
                          <strong>Explanation: </strong>
                          {currentEvaluation.explanation || currentEvaluation.feedback_reason || currentQ.explanation}
                        </div>

                        {/* Source Evidence Quote */}
                        {(currentQ.source_excerpt || currentEvaluation.source_excerpt) && (
                          <div style={{ fontSize: '11px', background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px dashed #CBD5E1', color: '#475569', marginBottom: '12px' }}>
                            <strong>Source Lecture Excerpt: </strong>
                            <em>"{currentQ.source_excerpt || currentEvaluation.source_excerpt}"</em>
                          </div>
                        )}

                        {/* Deep Conceptual Trap Treatment (if incorrect) */}
                        {!currentEvaluation.is_correct && (
                          <div style={{ marginBottom: '12px' }}>
                            {currentEvaluation.conceptual_trap && (
                              <div style={{ background: '#FFFFFF', border: '1px solid #FDA4AF', borderRadius: '6px', padding: '10px', marginBottom: '8px', fontSize: '12px', color: '#881337' }}>
                                <div style={{ fontWeight: 800, color: '#BE123C', textTransform: 'uppercase', fontSize: '10px', marginBottom: '2px' }}>
                                  Part 1: The Conceptual Trap
                                </div>
                                {currentEvaluation.conceptual_trap}
                              </div>
                            )}
                            {currentEvaluation.correct_mental_model && (
                              <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '6px', padding: '10px', fontSize: '12px', color: '#1E3A8A' }}>
                                <div style={{ fontWeight: 800, color: '#1D4ED8', textTransform: 'uppercase', fontSize: '10px', marginBottom: '2px' }}>
                                  Part 2: Authoritative Mental Model
                                </div>
                                {currentEvaluation.correct_mental_model}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Action Buttons inside feedback: Review Concept & Try Again */}
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                          <button
                            id="btn-review-this-concept"
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: '12px' }}
                            onClick={() => handleReviewConcept(currentEvaluation.remediation_timestamp ?? currentQ.conceptStartTime)}
                          >
                            <RotateCcw size={13} />
                            <span>Review This Concept</span>
                          </button>

                          <button
                            id="btn-try-again-checkpoint"
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: '12px' }}
                            onClick={() => handleTryAgain(currentQ.id)}
                          >
                            <RefreshCw size={13} />
                            <span>Try Again</span>
                          </button>
                        </div>
                      </div>

                      {/* Navigation Buttons */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={activeQIndex === 0}
                          onClick={handlePrevQuestion}
                        >
                          <ChevronLeft size={14} />
                          <span>Previous Question</span>
                        </button>

                        <button
                          id="btn-next-question"
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={handleNextQuestion}
                        >
                          <span>{activeQIndex < allQuestions.length - 1 ? 'Next Question' : 'Finish & View Summary'}</span>
                          <ArrowRight size={14} />
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* ========================================================
                       STATE 2: Unanswered Question Form (or Active Retry)
                       ======================================================== */
                    <form onSubmit={handleSubmitAnswer}>
                      {currentQState?.isRetrying && (
                        <div style={{ background: '#FEF3C7', border: '1px solid #FDE68A', padding: '8px 12px', borderRadius: '6px', fontSize: '12px', color: '#92400E', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span><strong>Retry Mode:</strong> Submitting will record a new attempt while preserving your previous attempt history.</span>
                          <button
                            type="button"
                            onClick={() => handleCancelRetry(currentQ.id)}
                            style={{ background: 'none', border: 'none', color: '#B45309', fontSize: '11px', cursor: 'pointer', textDecoration: 'underline' }}
                          >
                            Cancel
                          </button>
                        </div>
                      )}

                      {/* Multiple Choice Options List */}
                      {currentQ.question_type === 'mcq' ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '18px' }}>
                          {currentQ.options.map((opt, oIdx) => {
                            const isSelected = currentQState?.selectedOption === opt;
                            return (
                              <label
                                key={oIdx}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '10px',
                                  padding: '10px 14px',
                                  borderRadius: 'var(--radius-md)',
                                  background: isSelected ? 'var(--accent-soft)' : 'var(--bg-subtle)',
                                  border: `1px solid ${isSelected ? 'var(--accent-purple)' : 'var(--border-subtle)'}`,
                                  fontSize: '13px',
                                  cursor: 'pointer',
                                  transition: 'all 0.15s ease',
                                }}
                              >
                                <input
                                  type="radio"
                                  name={`checkpoint-${currentQ.id}-option`}
                                  value={opt}
                                  checked={isSelected}
                                  onChange={() => handleSelectOption(opt)}
                                  style={{ accentColor: 'var(--accent-purple)' }}
                                />
                                <span>{opt}</span>
                              </label>
                            );
                          })}
                        </div>
                      ) : (
                        /* Short Answer Input */
                        <div className="form-group" style={{ marginBottom: '18px' }}>
                          <textarea
                            id="checkpoint-short-answer-input"
                            className="form-textarea"
                            rows={3}
                            placeholder="Type your explanation in 1-2 sentences..."
                            value={currentQState?.shortAnswerText || ''}
                            onChange={(e) => handleShortAnswerChange(e.target.value)}
                          />
                        </div>
                      )}

                      {/* Submit & Navigation Bar */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={activeQIndex === 0}
                          onClick={handlePrevQuestion}
                        >
                          <ChevronLeft size={14} />
                          <span>Previous</span>
                        </button>

                        <button
                          id="btn-submit-checkpoint"
                          type="submit"
                          className="btn btn-primary btn-sm"
                          disabled={
                            evaluating ||
                            (currentQ.question_type === 'mcq'
                              ? !currentQState?.selectedOption
                              : !currentQState?.shortAnswerText?.trim())
                          }
                        >
                          <Send size={14} />
                          <span>{evaluating ? 'Evaluating...' : 'Submit Answer'}</span>
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
                  No questions found for this lecture.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Unresolved Reason Modal */}
      {showUnresolvedModal && (
        <div className="modal-overlay" onClick={() => setShowUnresolvedModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <HelpCircle size={22} color="var(--priority-high-text)" />
              <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                Mark Concept as Unresolved
              </h3>
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '18px' }}>
              Tagging <strong>'{activeConcept?.title}'</strong> at {formatTime(currentTime)}.
              This records explicit evidence in your persistent misconception profile.
            </p>

            <div className="form-group">
              <label className="form-label">What is confusing? (Optional note)</label>
              <textarea
                id="unresolved-reason-input"
                className="form-textarea"
                rows={3}
                placeholder="e.g. I don't understand why the output set changes when the domain is restricted..."
                value={unresolvedReason}
                onChange={(e) => setUnresolvedReason(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setShowUnresolvedModal(false)}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-mark-unresolved"
                type="button"
                className="btn btn-danger btn-sm"
                onClick={handleMarkUnresolved}
                disabled={unresolvedSubmitting}
              >
                {unresolvedSubmitting ? 'Recording...' : 'Record Misconception Signal'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
