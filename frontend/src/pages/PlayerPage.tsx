import React, { useState, useEffect, useRef, useMemo } from 'react';
import { api } from '../services/api';
import type {
  Lecture,
  Concept,
  Checkpoint,
  CheckpointEvaluation,
  PrerequisiteRecheck,
  PrerequisiteRecheckSubmitResult,
} from '../types';
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
  XCircle,
  Edit3,
  X
} from 'lucide-react';
import { McqSourceSection } from '../components/McqSourceSection';

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

interface QuestionResult {
  selectedAnswer: string;
  isCorrect?: boolean;
  evaluation?: CheckpointEvaluation | null;
  submitted: boolean;
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

  // MCQ & Question State (Per-Question Keyed State)
  const [activeQIndex, setActiveQIndex] = useState<number>(0);
  const [questionResults, setQuestionResults] = useState<Record<number, QuestionResult>>({});
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [showCompletionSummary, setShowCompletionSummary] = useState<boolean>(false);
  const [reviewMode, setReviewMode] = useState<boolean>(false);
  const [reviewIndex, setReviewIndex] = useState<number>(0);
  const checkpointCardRef = useRef<HTMLDivElement | null>(null);

  // Cross-Topic Prerequisite Re-Check State
  const [rechecks, setRechecks] = useState<PrerequisiteRecheck[]>([]);
  const [activeRecheckIndex, setActiveRecheckIndex] = useState<number>(0);
  const [recheckSkipped, setRecheckSkipped] = useState<boolean>(false);
  const [recheckAnswers, setRecheckAnswers] = useState<Record<number, {
    selectedAnswer: string;
    submitted: boolean;
    isCorrect?: boolean;
    result?: PrerequisiteRecheckSubmitResult;
    submitting?: boolean;
  }>>({});

  const loadRechecks = async (id: number) => {
    try {
      const data = await api.lectures.getRechecks(id);
      setRechecks(Array.isArray(data) ? data : []);
      setActiveRecheckIndex(0);
      setRecheckSkipped(false);
      setRecheckAnswers({});
    } catch {
      setRechecks([]);
    }
  };

  const handleSelectRecheckOption = (miscId: number, opt: string) => {
    if (recheckAnswers[miscId]?.submitted) return;
    setRecheckAnswers((prev) => ({
      ...prev,
      [miscId]: {
        ...prev[miscId],
        selectedAnswer: opt,
        submitted: false,
      },
    }));
  };

  const handleSubmitRecheck = async (item: PrerequisiteRecheck) => {
    const current = recheckAnswers[item.misconception_id];
    if (!current?.selectedAnswer || current.submitted || current.submitting || !lecture) return;

    setRecheckAnswers((prev) => ({
      ...prev,
      [item.misconception_id]: {
        ...prev[item.misconception_id],
        submitting: true,
      },
    }));

    try {
      const res = await api.lectures.submitRecheck(lecture.id, {
        misconception_id: item.misconception_id,
        checkpoint_id: item.question.id,
        student_answer: current.selectedAnswer,
      });

      setRecheckAnswers((prev) => ({
        ...prev,
        [item.misconception_id]: {
          selectedAnswer: current.selectedAnswer,
          submitted: true,
          submitting: false,
          isCorrect: res.is_correct,
          result: res,
        },
      }));
    } catch (err: any) {
      setRecheckAnswers((prev) => ({
        ...prev,
        [item.misconception_id]: {
          ...prev[item.misconception_id],
          submitting: false,
        },
      }));
    }
  };

  const handleSkipRecheck = () => {
    setRecheckSkipped(true);
  };

  // Rename modal state
  const [showRenameModal, setShowRenameModal] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>('');
  const [renameSaving, setRenameSaving] = useState<boolean>(false);
  const [renameError, setRenameError] = useState<string | null>(null);

  const handleOpenRename = () => {
    if (!lecture) return;
    setNewTitle(lecture.title);
    setRenameError(null);
    setShowRenameModal(true);
  };

  const handleSaveRename = async () => {
    if (!lecture || !newTitle.trim()) return;
    setRenameSaving(true);
    setRenameError(null);
    try {
      await api.lectures.rename(lecture.id, newTitle.trim());
      setLecture({ ...lecture, title: newTitle.trim() });
      setShowRenameModal(false);
    } catch (err: any) {
      setRenameError(err.message || 'Failed to rename lecture');
    } finally {
      setRenameSaving(false);
    }
  };

  // Prerequisite edit control state
  const [isEditingPrereq, setIsEditingPrereq] = useState<boolean>(false);
  const [selectedPrereqId, setSelectedPrereqId] = useState<string>('');
  const [availablePrereqs, setAvailablePrereqs] = useState<Lecture[]>([]);
  const [savingPrereq, setSavingPrereq] = useState<boolean>(false);

  const handleStartEditPrereq = async () => {
    if (!lecture) return;
    setSelectedPrereqId(
      lecture.prerequisite_lecture_id ? String(lecture.prerequisite_lecture_id) : ''
    );
    setIsEditingPrereq(true);
    try {
      const allLecs = await api.lectures.list();
      // Exclude current lecture to prevent self-prerequisite selection
      const filtered = Array.isArray(allLecs)
        ? allLecs.filter((l) => l.id !== lecture.id)
        : [];
      setAvailablePrereqs(filtered);
    } catch (e) {
      console.error('Failed to load lecture list for prerequisite selection', e);
    }
  };

  const handleSavePrereq = async () => {
    if (!lecture) return;
    setSavingPrereq(true);
    try {
      const prereqId = selectedPrereqId ? parseInt(selectedPrereqId, 10) : null;
      const res = await api.lectures.update(lecture.id, {
        prerequisite_lecture_id: prereqId,
      });
      setLecture({
        ...lecture,
        prerequisite_lecture_id: res.prerequisite_lecture_id,
        prerequisite_lecture_title: res.prerequisite_lecture_title,
      });
      setIsEditingPrereq(false);
      // Reload re-checks immediately for this new prerequisite
      await loadRechecks(lecture.id);
    } catch (err: any) {
      alert(`Could not update prerequisite: ${err.message || 'Validation error'}`);
    } finally {
      setSavingPrereq(false);
    }
  };

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
      await loadRechecks(lectureId);
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

  const sortQuestions = (items: QuestionItem[]): QuestionItem[] => {
    return [...items].sort((a, b) => {
      const typeRankA = (a.question_type || 'mcq') === 'mcq' ? 0 : 1;
      const typeRankB = (b.question_type || 'mcq') === 'mcq' ? 0 : 1;
      if (typeRankA !== typeRankB) return typeRankA - typeRankB;

      const diffRankA = (a.difficulty || 'easy').toLowerCase() === 'easy' ? 0 : 1;
      const diffRankB = (b.difficulty || 'easy').toLowerCase() === 'easy' ? 0 : 1;
      if (diffRankA !== diffRankB) return diffRankA - diffRankB;

      return (a.order_index ?? 0) - (b.order_index ?? 0);
    });
  };

  const initializeQuestionsFromLecture = (data: Lecture) => {
    const rawQuestions: QuestionItem[] = (data.concepts || []).flatMap((c) =>
      (c.checkpoints || []).map((chk) => ({
        ...chk,
        conceptTitle: c.title,
        conceptStartTime: c.start_time,
        conceptEndTime: c.end_time,
      }))
    );
    const questions = sortQuestions(rawQuestions);

    setQuestionResults((prev) => {
      const updated = { ...prev };
      questions.forEach((q) => {
        // Only mark submitted if question has an existing attempt in DB and no local answer yet
        if (q.latest_attempt && !updated[q.id]) {
          const attVerdict = q.latest_attempt.grade || q.latest_attempt.verdict || (q.latest_attempt.explanation_verdict as any) || (q.latest_attempt.is_correct ? 'correct' : 'incorrect');
          updated[q.id] = {
            selectedAnswer: q.latest_attempt.student_answer,
            isCorrect: q.latest_attempt.is_correct,
            submitted: true,
            evaluation: {
              checkpoint_id: q.id,
              student_answer: q.latest_attempt.student_answer,
              is_correct: q.latest_attempt.is_correct,
              verdict: attVerdict,
              grade: attVerdict,
              feedback: q.latest_attempt.feedback || q.latest_attempt.feedback_reason,
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
              conceptual_trap: q.target_misconception,
              correct_mental_model: q.explanation,
            },
          };
        } else if (!updated[q.id]) {
          updated[q.id] = {
            selectedAnswer: '',
            isCorrect: undefined,
            evaluation: null,
            submitted: false,
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
    setReviewMode(false);
    setReviewIndex(0);
    setQuestionResults({});
    setSubtleWarning(null);
    setError(null);
    loadLecture();
  }, [lectureId]);

  const concepts = lecture?.concepts || [];
  const activeConcept = concepts[activeConceptIndex] || null;

  // Gather flattened question set across the lecture: all MCQs first, short-answer questions at the end
  const allQuestions: QuestionItem[] = useMemo(() => {
    const raw = concepts.flatMap((c) =>
      (c.checkpoints || []).map((chk) => ({
        ...chk,
        conceptTitle: c.title,
        conceptStartTime: c.start_time,
        conceptEndTime: c.end_time,
      }))
    );
    return sortQuestions(raw);
  }, [concepts]);

  const currentQ: QuestionItem | undefined = allQuestions[activeQIndex];
  const currentResult: QuestionResult | undefined = currentQ ? questionResults[currentQ.id] : undefined;

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

  const handleWatchSourcePart = (timestamp: number) => {
    handleSeek(timestamp);
    if (mediaRef.current) {
      mediaRef.current.currentTime = timestamp;
      mediaRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
    const playerCard = document.getElementById('media-player-card');
    if (playerCard) {
      playerCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
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
    if (!currentQ || questionResults[currentQ.id]?.submitted) return;
    setQuestionResults((prev) => ({
      ...prev,
      [currentQ.id]: {
        ...(prev[currentQ.id] || { evaluation: null, submitted: false }),
        selectedAnswer: opt,
      },
    }));
  };

  const handleTextAnswerChange = (val: string) => {
    if (!currentQ || questionResults[currentQ.id]?.submitted) return;
    setQuestionResults((prev) => ({
      ...prev,
      [currentQ.id]: {
        ...(prev[currentQ.id] || { evaluation: null, submitted: false }),
        selectedAnswer: val,
      },
    }));
  };

  const handleSubmitAnswer = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!currentQ || evaluating || questionResults[currentQ.id]?.submitted) return;

    const res = questionResults[currentQ.id];
    const answer = res?.selectedAnswer;

    if (!answer || !answer.trim()) {
      alert('Please select or type an answer before submitting.');
      return;
    }

    setEvaluating(true);
    try {
      const result = await api.checkpoints.submitAnswer({
        checkpoint_id: currentQ.id,
        student_answer: answer.trim(),
      });

      setQuestionResults((prev) => ({
        ...prev,
        [currentQ.id]: {
          selectedAnswer: answer.trim(),
          isCorrect: result.is_correct,
          submitted: true,
          evaluation: {
            ...result,
            correct_answer: result.correct_answer || currentQ.correct_answer,
            explanation: result.explanation || currentQ.explanation,
            concept_title: currentQ.conceptTitle,
            remediation_timestamp:
              result.remediation_timestamp ?? currentQ.source_timestamp ?? currentQ.conceptStartTime,
          },
        },
      }));

      if (result.misconception_created_or_updated) {
        setSubtleWarning(
          `Misconception logged in persistent tracking (${result.new_severity_level} priority). Saved in database.`
        );
      }
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  const handleTryAgain = (qId: number) => {
    setQuestionResults((prev) => ({
      ...prev,
      [qId]: {
        selectedAnswer: '',
        submitted: false,
        isCorrect: undefined,
        evaluation: null,
      },
    }));
  };

  const scrollToCheckpoint = () => {
    if (checkpointCardRef.current) {
      checkpointCardRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handlePrevQuestion = () => {
    if (activeQIndex > 0) {
      setActiveQIndex(activeQIndex - 1);
      setShowCompletionSummary(false);
      setReviewMode(false);
      setSubtleWarning(null);
      scrollToCheckpoint();
    }
  };

  const handleNextQuestion = () => {
    if (activeQIndex < allQuestions.length - 1) {
      setActiveQIndex(activeQIndex + 1);
      setShowCompletionSummary(false);
      setReviewMode(false);
      setSubtleWarning(null);
      scrollToCheckpoint();
    } else {
      setShowCompletionSummary(true);
      scrollToCheckpoint();
    }
  };

  const handleJumpToQuestion = (idx: number) => {
    setActiveQIndex(idx);
    setShowCompletionSummary(false);
    setReviewMode(false);
    setSubtleWarning(null);
    scrollToCheckpoint();
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // Completion metrics calculation
  const totalQCount = allQuestions.length;
  const answeredQuestions = allQuestions.filter((q) => questionResults[q.id]?.submitted);
  const correctQuestions = allQuestions.filter(
    (q) => questionResults[q.id]?.submitted && questionResults[q.id]?.isCorrect
  );
  const incorrectQuestions = allQuestions.filter(
    (q) => questionResults[q.id]?.submitted && !questionResults[q.id]?.isCorrect
  );
  const safeReviewIndex = Math.min(reviewIndex, Math.max(0, incorrectQuestions.length - 1));

  const answeredQCount = answeredQuestions.length;
  const correctQCount = correctQuestions.length;
  const incorrectQCount = incorrectQuestions.length;
  const accuracyPct = totalQCount > 0 ? Math.round((correctQCount / totalQCount) * 100) : 0;

  // Concepts status breakdown
  const conceptSummaries = concepts.map((c) => {
    const cQuestions = allQuestions.filter((q) => q.concept_id === c.id);
    const cAnswered = cQuestions.filter((q) => questionResults[q.id]?.submitted);
    const cCorrect = cQuestions.filter(
      (q) => questionResults[q.id]?.submitted && questionResults[q.id]?.isCorrect
    );
    const isMastered = cQuestions.length > 0 && cCorrect.length === cQuestions.length;
    const hasMistakes = cQuestions.some(
      (q) => questionResults[q.id]?.submitted && !questionResults[q.id]?.isCorrect
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


  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* Top Breadcrumb & Action bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <button id="btn-back-dashboard" className="btn btn-secondary btn-sm" onClick={onBack}>
            <ArrowLeft size={14} />
            <span>Back to Lectures</span>
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--primary-navy)' }}>
              {lecture.title}
            </span>
            <button
              onClick={handleOpenRename}
              className="btn btn-secondary btn-sm"
              style={{ padding: '3px 8px', fontSize: '12px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title="Rename this lecture"
            >
              <Edit3 size={12} color="var(--accent-purple)" />
              <span>Rename</span>
            </button>

            {/* Prerequisite Lecture Control */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                paddingLeft: '8px',
                borderLeft: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Prerequisite:</span>
              {!isEditingPrereq ? (
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      fontWeight: 700,
                      color: lecture.prerequisite_lecture_title ? 'var(--primary-navy)' : 'var(--text-muted)',
                      background: 'var(--bg-subtle)',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-subtle)',
                      maxWidth: '180px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={lecture.prerequisite_lecture_title || 'None'}
                  >
                    {lecture.prerequisite_lecture_title || 'None'}
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '2px 8px', fontSize: '11px', height: '22px' }}
                    onClick={handleStartEditPrereq}
                    title="Change prerequisite lecture"
                  >
                    <span>Change</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <select
                    id="select-change-prerequisite"
                    value={selectedPrereqId}
                    disabled={savingPrereq}
                    onChange={(e) => setSelectedPrereqId(e.target.value)}
                    style={{
                      fontSize: '12px',
                      padding: '2px 6px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--accent-purple)',
                      background: '#FFFFFF',
                      color: 'var(--primary-navy)',
                      maxWidth: '180px',
                    }}
                  >
                    <option value="">None</option>
                    {availablePrereqs.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.title} {l.course_code ? `(${l.course_code})` : ''}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    style={{ padding: '2px 8px', fontSize: '11px', height: '22px' }}
                    disabled={savingPrereq}
                    onClick={handleSavePrereq}
                  >
                    <span>{savingPrereq ? 'Saving...' : 'Save'}</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '2px 6px', fontSize: '11px', height: '22px' }}
                    disabled={savingPrereq}
                    onClick={() => setIsEditingPrereq(false)}
                  >
                    <span>Cancel</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
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
      <div className="player-layout-grid">
        {/* LEFT AREA: Video/Audio Player, Concept Notes & Summary Cards, Timeline */}
        <div>
          {/* Media Player Card */}
          <div id="media-player-card" className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '20px' }}>
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

        {/* RIGHT AREA: Concept Checkpoint & Diagnostic Assessment */}
        <div style={{ flex: '1 1 380px', minWidth: '340px' }}>
          {/* Top checkpoint toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--primary-navy)' }}>
              Interactive Diagnostic Assessment
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '11px', padding: '2px 8px', height: '24px' }}
                onClick={() => {
                  setReviewMode(false);
                  setShowCompletionSummary(!showCompletionSummary);
                }}
              >
                <span>{showCompletionSummary ? 'Return to Quiz' : 'View Summary'}</span>
              </button>
            </div>
          </div>

          {/* CHECKPOINT AREA: Toggle between Question View and Completion Summary */}
          {showCompletionSummary ? (
            reviewMode ? (
              /* ==============================================================
                 Dedicated Incorrect Answers Review Mode
                 ============================================================== */
              <div className="card" style={{ border: '2px solid var(--accent-purple)', background: '#FAFAFF' }}>
                {/* Header with counter and close button */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileQuestion size={18} color="var(--accent-purple)" />
                    <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--primary-navy)', margin: 0 }}>
                      Review Incorrect Answers
                    </h3>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {incorrectQuestions.length > 0 && (
                      <span style={{ fontSize: '11px', fontWeight: 700, color: '#DC2626', background: '#FEE2E2', padding: '2px 8px', borderRadius: 'var(--radius-full)' }}>
                        {safeReviewIndex + 1} of {incorrectQuestions.length}
                      </span>
                    )}
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '11px', padding: '2px 8px', height: '24px' }}
                      onClick={() => setReviewMode(false)}
                      title="Close review and return to summary"
                    >
                      <X size={12} />
                      <span>Close</span>
                    </button>
                  </div>
                </div>

                {incorrectQuestions.length === 0 ? (
                  /* Friendly empty state if 0 incorrect answers */
                  <div style={{ textAlign: 'center', padding: '28px 16px' }}>
                    <div
                      style={{
                        width: '52px',
                        height: '52px',
                        borderRadius: '50%',
                        background: '#DCFCE7',
                        color: '#16A34A',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginBottom: '14px',
                      }}
                    >
                      <CheckCircle2 size={28} />
                    </div>
                    <h4 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--primary-navy)', margin: '0 0 6px 0' }}>
                      No incorrect answers
                    </h4>
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '0 0 16px 0' }}>
                      Great job! You answered all questions correctly in this lecture.
                    </p>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setReviewMode(false)}
                    >
                      <span>Return to Summary</span>
                    </button>
                  </div>
                ) : (
                  /* Single Incorrect Question Review Card */
                  (() => {
                    const currentReviewQ = incorrectQuestions[safeReviewIndex];
                    if (!currentReviewQ) return null;
                    const qOriginalIdx = allQuestions.findIndex((item) => item.id === currentReviewQ.id);
                    const qReviewResult = questionResults[currentReviewQ.id];
                    const qReviewEval = qReviewResult?.evaluation;
                    const conceptTargetTime =
                      qReviewEval?.remediation_timestamp ?? currentReviewQ.source_timestamp ?? currentReviewQ.conceptStartTime ?? 0;

                    return (
                      <div>
                        {/* Concept & Seek to concept button */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0', marginBottom: '12px' }}>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                            Concept: <strong style={{ color: 'var(--primary-navy)' }}>{currentReviewQ.conceptTitle}</strong>
                          </span>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: '11px', padding: '2px 8px', height: '24px', flexShrink: 0 }}
                            onClick={() => handleReviewConcept(conceptTargetTime)}
                            title={`Seek lecture video to ${formatTime(conceptTargetTime)}`}
                          >
                            <Play size={10} />
                            <span>Seek to concept ({formatTime(conceptTargetTime)})</span>
                          </button>
                        </div>

                        {/* Question Text */}
                        <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '12px', lineHeight: 1.45 }}>
                          {qOriginalIdx !== -1 ? `Q${qOriginalIdx + 1}: ` : ''}{currentReviewQ.question_text}
                        </div>

                        {/* User's Answer (Red) & Correct Answer (Green) */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                          <div style={{ background: '#FFF1F2', border: '1px solid #FECDD3', borderRadius: '6px', padding: '10px 12px' }}>
                            <div style={{ fontSize: '11px', fontWeight: 700, color: '#9F1239', textTransform: 'uppercase', marginBottom: '2px' }}>
                              Your Answer
                            </div>
                            <div style={{ fontSize: '13px', fontWeight: 700, color: '#DC2626' }}>
                              {qReviewResult?.selectedAnswer || qReviewEval?.student_answer || 'No answer recorded'}
                            </div>
                          </div>

                          <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '6px', padding: '10px 12px' }}>
                            <div style={{ fontSize: '11px', fontWeight: 700, color: '#166534', textTransform: 'uppercase', marginBottom: '2px' }}>
                              Correct Answer
                            </div>
                            <div style={{ fontSize: '13px', fontWeight: 700, color: '#16A34A' }}>
                              {qReviewEval?.correct_answer || currentReviewQ.correct_answer || 'Not specified'}
                            </div>
                          </div>
                        </div>

                        {/* Explanation (if data has one) */}
                        {(qReviewEval?.explanation || qReviewEval?.feedback_reason || currentReviewQ.explanation) && (
                          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '6px', padding: '10px 12px', marginBottom: '12px', fontSize: '12px', color: 'var(--text-main)', lineHeight: 1.5 }}>
                            <strong style={{ color: 'var(--primary-navy)' }}>Explanation: </strong>
                            {qReviewEval?.explanation || qReviewEval?.feedback_reason || currentReviewQ.explanation}
                          </div>
                        )}

                        {/* Source from Lecture */}
                        {currentReviewQ.question_type === 'mcq' ? (
                          <div style={{ marginBottom: '12px' }}>
                            <McqSourceSection
                              lectureTitle={lecture?.title || currentReviewQ.lecture_title}
                              sourceExcerpt={currentReviewQ.source_excerpt || qReviewEval?.source_excerpt}
                              sourceTimestamp={currentReviewQ.source_timestamp ?? qReviewEval?.source_timestamp}
                              sourceEndTimestamp={currentReviewQ.source_end_timestamp ?? qReviewEval?.source_end_timestamp}
                              lectureDuration={duration || lecture?.duration_seconds}
                              onWatchThisPart={handleWatchSourcePart}
                            />
                          </div>
                        ) : (
                          (currentReviewQ.source_excerpt || qReviewEval?.source_excerpt) && (
                            <div style={{ fontSize: '11px', background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px dashed #CBD5E1', color: '#475569', marginBottom: '12px' }}>
                              <strong>Source Lecture Excerpt: </strong>
                              <em>"{currentReviewQ.source_excerpt || qReviewEval?.source_excerpt}"</em>
                            </div>
                          )
                        )}

                        {/* Previous / Close / Next Navigation */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #E2E8F0', marginTop: '12px' }}>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            disabled={safeReviewIndex === 0}
                            onClick={() => setReviewIndex((prev) => Math.max(0, prev - 1))}
                          >
                            <ChevronLeft size={14} />
                            <span>Previous</span>
                          </button>

                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => setReviewMode(false)}
                          >
                            <span>Close</span>
                          </button>

                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            disabled={safeReviewIndex >= incorrectQuestions.length - 1}
                            onClick={() => setReviewIndex((prev) => Math.min(incorrectQuestions.length - 1, prev + 1))}
                          >
                            <span>Next</span>
                            <ChevronRight size={14} />
                          </button>
                        </div>
                      </div>
                    );
                  })()
                )}
              </div>
            ) : (
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
                        const qRes = questionResults[q.id];
                        const qEval = qRes?.evaluation;
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
                                  const incIndex = incorrectQuestions.findIndex((item) => item.id === q.id);
                                  setReviewIndex(incIndex !== -1 ? incIndex : 0);
                                  setReviewMode(true);
                                }}
                              >
                                <span>Review</span>
                                <ChevronRight size={12} />
                              </button>
                            </div>
                            <div style={{ fontSize: '11px', color: '#DC2626', marginTop: '4px' }}>
                              <strong>Your Answer:</strong> {qRes?.selectedAnswer}
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

                {/* 4 Distinct Summary Actions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', paddingTop: '14px', borderTop: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1, fontSize: '12px' }}
                      onClick={() => {
                        setReviewIndex(0);
                        setReviewMode(true);
                      }}
                    >
                      <span>Review Incorrect Answers</span>
                    </button>

                    {incorrectQuestions.length > 0 && (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        style={{ flex: 1, fontSize: '12px' }}
                        onClick={() => {
                          incorrectQuestions.forEach((q) => handleTryAgain(q.id));
                          const firstIncorrectIdx = allQuestions.findIndex(
                            (q) => questionResults[q.id]?.submitted && !questionResults[q.id]?.isCorrect
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
                      onClick={() => {
                        setShowCompletionSummary(false);
                        setReviewMode(false);
                      }}
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
            )
          ) : !recheckSkipped && rechecks.length > 0 && activeRecheckIndex < rechecks.length ? (
            /* ==============================================================
               Prerequisite Cross-Topic Re-Check Card
               ============================================================== */
            (() => {
              const currentRecheck = rechecks[activeRecheckIndex];
              const qState = recheckAnswers[currentRecheck.misconception_id] || {
                selectedAnswer: '',
                submitted: false,
                submitting: false,
              };
              const isSubmitted = Boolean(qState.submitted);
              const isCorrect = Boolean(qState.isCorrect);

              return (
                <div
                  className="card"
                  style={{
                    border: '2px solid var(--accent-purple)',
                    background: '#FFFFFF',
                    boxShadow: 'var(--shadow-md)',
                  }}
                >
                  {/* Card Header */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '14px',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 800,
                          textTransform: 'uppercase',
                          background: 'var(--accent-purple)',
                          color: '#FFFFFF',
                          padding: '3px 10px',
                          borderRadius: 'var(--radius-full)',
                          letterSpacing: '0.5px',
                        }}
                      >
                        Prerequisite Re-Check
                      </span>
                      {rechecks.length > 1 && (
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            color: 'var(--text-muted)',
                            background: 'var(--bg-subtle)',
                            padding: '3px 8px',
                            borderRadius: 'var(--radius-full)',
                          }}
                        >
                          Check {activeRecheckIndex + 1} of {rechecks.length}
                        </span>
                      )}
                    </div>

                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '12px', padding: '3px 10px' }}
                      onClick={handleSkipRecheck}
                      title="Skip re-checking and continue to lecture checkpoints"
                    >
                      <span>Skip for now</span>
                      <ChevronRight size={13} />
                    </button>
                  </div>

                  {/* Context Banner */}
                  <div
                    style={{
                      padding: '10px 14px',
                      background: 'var(--accent-soft)',
                      borderRadius: 'var(--radius-md)',
                      marginBottom: '16px',
                      fontSize: '13px',
                      color: 'var(--primary-navy)',
                      lineHeight: 1.45,
                    }}
                  >
                    Before this lecture, let's re-check:{' '}
                    <strong>{currentRecheck.earlier_concept_name}</strong>{' '}
                    (from <em>{currentRecheck.earlier_lecture_title}</em>)
                  </div>

                  {/* Question Prompt */}
                  <div
                    style={{
                      fontSize: '14px',
                      fontWeight: 700,
                      color: 'var(--primary-navy)',
                      marginBottom: '14px',
                      lineHeight: 1.45,
                    }}
                  >
                    {currentRecheck.question.question_text}
                  </div>

                  {/* MCQ Options */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
                    {currentRecheck.question.options.map((opt, optIdx) => {
                      const isSelected = qState.selectedAnswer === opt;
                      return (
                        <label
                          key={optIdx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '10px 14px',
                            borderRadius: 'var(--radius-md)',
                            background: isSelected ? 'var(--accent-soft)' : 'var(--bg-subtle)',
                            border: `1px solid ${isSelected ? 'var(--accent-purple)' : 'var(--border-subtle)'}`,
                            fontSize: '13px',
                            cursor: isSubmitted ? 'default' : 'pointer',
                            opacity: isSubmitted && !isSelected ? 0.75 : 1,
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <input
                            type="radio"
                            name={`recheck-${currentRecheck.misconception_id}-option`}
                            value={opt}
                            checked={isSelected}
                            disabled={isSubmitted}
                            onChange={() => handleSelectRecheckOption(currentRecheck.misconception_id, opt)}
                            style={{ accentColor: 'var(--accent-purple)' }}
                          />
                          <span style={{ fontWeight: isSelected ? 700 : 400 }}>{opt}</span>
                        </label>
                      );
                    })}
                  </div>

                  {/* Submit Button (Shown only before submitting) */}
                  {!isSubmitted && (
                    <div style={{ marginBottom: '14px' }}>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        style={{ width: '100%', height: '36px', fontSize: '13px' }}
                        disabled={!qState.selectedAnswer || qState.submitting}
                        onClick={() => handleSubmitRecheck(currentRecheck)}
                      >
                        <Send size={14} />
                        <span>{qState.submitting ? 'Submitting...' : 'Submit Re-Check'}</span>
                      </button>
                    </div>
                  )}

                  {/* Feedback Banner (Shown after submit) */}
                  {isSubmitted && (
                    <div
                      style={{
                        padding: '14px 16px',
                        borderRadius: 'var(--radius-md)',
                        marginBottom: '16px',
                        background: isCorrect ? '#F0FDF4' : '#FFF1F2',
                        border: `1px solid ${isCorrect ? '#BBF7D0' : '#FECDD3'}`,
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: '8px',
                          flexWrap: 'wrap',
                          gap: '6px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {isCorrect ? (
                            <CheckCircle2 size={18} color="#16A34A" />
                          ) : (
                            <AlertCircle size={18} color="#E11D48" />
                          )}
                          <span
                            style={{
                              fontSize: '14px',
                              fontWeight: 800,
                              color: isCorrect ? '#16A34A' : '#E11D48',
                            }}
                          >
                            {isCorrect
                              ? 'Correct! Prerequisite Gap Resolved'
                              : 'Incorrect — Prerequisite Gap Unresolved'}
                          </span>
                        </div>

                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            background: isCorrect ? '#DCFCE7' : '#FFE4E6',
                            color: isCorrect ? '#15803D' : '#BE123C',
                            padding: '2px 8px',
                            borderRadius: '4px',
                          }}
                        >
                          {isCorrect
                            ? 'Signal Trail: Cross-topic recheck passed'
                            : 'Signal Trail: Cross-topic recheck failed (+3 severity recorded)'}
                        </span>
                      </div>

                      {/* Explanation */}
                      {(qState.result?.explanation || currentRecheck.question.explanation) && (
                        <div
                          style={{
                            fontSize: '12px',
                            color: isCorrect ? '#166534' : '#881337',
                            lineHeight: 1.45,
                            marginTop: '8px',
                          }}
                        >
                          <strong>Explanation: </strong>
                          {qState.result?.explanation || currentRecheck.question.explanation}
                        </div>
                      )}

                      {/* Next / Proceed Button */}
                      <div style={{ marginTop: '14px', display: 'flex', justifyContent: 'flex-end' }}>
                        {activeRecheckIndex < rechecks.length - 1 ? (
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            style={{ fontSize: '12px' }}
                            onClick={() => setActiveRecheckIndex((prev) => prev + 1)}
                          >
                            <span>Next Re-Check</span>
                            <ArrowRight size={13} />
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            style={{ fontSize: '12px' }}
                            onClick={() => setRecheckSkipped(true)}
                          >
                            <span>Proceed to Checkpoints</span>
                            <ArrowRight size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()
          ) : (
            /* ==============================================================
               Concept Checkpoint: Professional Single Card Layout
               ============================================================== */
            <div className="card" ref={checkpointCardRef}>
              {/* Question Header & Role Pill */}
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
                  {currentQ && (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                        background: currentQ.question_type === 'mcq' ? '#EEF2FF' : '#FEF3C7',
                        color: currentQ.question_type === 'mcq' ? '#4F46E5' : '#D97706',
                        border: `1px solid ${currentQ.question_type === 'mcq' ? '#C7D2FE' : '#FDE68A'}`,
                      }}
                    >
                      {currentQ.question_type === 'mcq' ? 'MCQ' : 'Short Answer'}
                    </span>
                  )}
                  {/* Renamed to "Initial Check" instead of "DIAGNOSTIC ORIGINAL" */}
                  {currentQ && (
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
                        : 'Initial Check'}
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

              {/* Question Navigation Pills (Q1..Qn): grey dot = unanswered, green = correct, amber = partial, red = incorrect, purple = current */}
              {allQuestions.length > 1 && (
                <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '8px', marginBottom: '14px' }}>
                  {allQuestions.map((q, idx) => {
                    const isCurrent = activeQIndex === idx;
                    const res = questionResults[q.id];
                    const isSubmitted = Boolean(res?.submitted);
                    const verdict = res?.evaluation?.verdict || (res?.isCorrect ? 'correct' : 'incorrect');
                    const isCorrect = isSubmitted && verdict === 'correct';
                    const isPartial = isSubmitted && verdict === 'partial';
                    const isUnanswered = isSubmitted && verdict === 'unanswered';

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
                            : isSubmitted
                            ? isCorrect
                              ? '#ECFDF5'
                              : isPartial
                              ? '#FFFBEB'
                              : isUnanswered
                              ? '#F1F5F9'
                              : '#FFF1F2'
                            : 'var(--bg-subtle)',
                          color: isCurrent
                            ? '#FFFFFF'
                            : isSubmitted
                            ? isCorrect
                              ? '#059669'
                              : isPartial
                              ? '#D97706'
                              : isUnanswered
                              ? '#475569'
                              : '#E11D48'
                            : 'var(--text-muted)',
                          border: isCurrent
                            ? '1px solid var(--accent-purple)'
                            : isSubmitted
                            ? isCorrect
                              ? '1px solid #A7F3D0'
                              : isPartial
                              ? '1px solid #FDE68A'
                              : isUnanswered
                              ? '1px solid #CBD5E1'
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
                        {isSubmitted ? (
                          isCorrect ? (
                            <CheckCircle2 size={12} color={isCurrent ? '#FFFFFF' : '#10B981'} />
                          ) : isPartial ? (
                            <AlertTriangle size={12} color={isCurrent ? '#FFFFFF' : '#D97706'} />
                          ) : isUnanswered ? (
                            <HelpCircle size={12} color={isCurrent ? '#FFFFFF' : '#64748B'} />
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

              {/* Associated Concept Banner */}
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

                  {/* Options (MCQ) or Textarea (Open-ended): Options are locked when submitted */}
                  {currentQ.question_type === 'mcq' ? (
                    <>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '14px' }}>
                        {currentQ.options.map((opt, oIdx) => {
                          const isSelected = currentResult?.selectedAnswer === opt;
                          const isSubmitted = Boolean(currentResult?.submitted);
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
                                cursor: isSubmitted ? 'default' : 'pointer',
                                opacity: isSubmitted && !isSelected ? 0.75 : 1,
                                transition: 'all 0.15s ease',
                              }}
                            >
                              <input
                                type="radio"
                                name={`checkpoint-${currentQ.id}-option`}
                                value={opt}
                                checked={isSelected}
                                disabled={isSubmitted}
                                onChange={() => handleSelectOption(opt)}
                                style={{ accentColor: 'var(--accent-purple)' }}
                              />
                              <span style={{ fontWeight: isSelected ? 700 : 400 }}>{opt}</span>
                            </label>
                          );
                        })}
                      </div>

                      {/* Source from Lecture (Expandable Section for MCQs) */}
                      <div style={{ marginBottom: '16px' }}>
                        <McqSourceSection
                          lectureTitle={lecture?.title || currentQ.lecture_title}
                          sourceExcerpt={currentQ.source_excerpt}
                          sourceTimestamp={currentQ.source_timestamp}
                          sourceEndTimestamp={currentQ.source_end_timestamp}
                          lectureDuration={duration || lecture?.duration_seconds}
                          onWatchThisPart={handleWatchSourcePart}
                        />
                      </div>
                    </>
                  ) : (
                    /* Open-Ended Short Answer Input */
                    <div className="form-group" style={{ marginBottom: '16px' }}>
                      <textarea
                        id="checkpoint-short-answer-input"
                        className="form-textarea"
                        rows={3}
                        placeholder="Type your explanation in 1-2 sentences..."
                        value={currentResult?.selectedAnswer || ''}
                        disabled={Boolean(currentResult?.submitted)}
                        onChange={(e) => handleTextAnswerChange(e.target.value)}
                      />
                    </div>
                  )}

                  {/* Submit Button: Shown ONLY when question is NOT submitted yet */}
                  {!currentResult?.submitted && (
                    <div style={{ marginBottom: '18px' }}>
                      <button
                        id="btn-submit-checkpoint"
                        type="button"
                        className="btn btn-primary btn-sm"
                        style={{ width: '100%', height: '36px', fontSize: '13px' }}
                        disabled={evaluating}
                        onClick={handleSubmitAnswer}
                      >
                        <Send size={14} />
                        <span>{evaluating ? 'Evaluating...' : 'Submit Answer'}</span>
                      </button>
                    </div>
                  )}

                  {/* Feedback Block: INSIDE card, DIRECTLY BELOW options, ONLY when submitted */}
                  {currentResult?.submitted && currentResult?.evaluation && (() => {
                    const verdict = currentResult.evaluation?.verdict || (currentResult.isCorrect ? 'correct' : 'incorrect');
                    const isCorrect = verdict === 'correct';
                    const isPartial = verdict === 'partial';
                    const isUnanswered = verdict === 'unanswered';

                    const cardBg = isCorrect ? '#F0FDF4' : isPartial ? '#FFFBEB' : isUnanswered ? '#F8FAFC' : '#FFF1F2';
                    const cardBorder = isCorrect ? '#BBF7D0' : isPartial ? '#FDE68A' : isUnanswered ? '#E2E8F0' : '#FECDD3';
                    const textColor = isCorrect ? '#16A34A' : isPartial ? '#D97706' : isUnanswered ? '#475569' : '#E11D48';
                    const badgeBg = isCorrect ? '#DCFCE7' : isPartial ? '#FEF3C7' : isUnanswered ? '#F1F5F9' : '#FFE4E6';
                    const badgeColor = isCorrect ? '#15803D' : isPartial ? '#92400E' : isUnanswered ? '#475569' : '#BE123C';
                    const badgeText = isCorrect
                      ? '+10 Points • Verified'
                      : isPartial
                      ? '0 Points • Needs Clarification'
                      : isUnanswered
                      ? '0 Points • Unanswered'
                      : '0 Points • Incorrect';
                    const statusText = isCorrect
                      ? 'Correct Answer!'
                      : isPartial
                      ? 'Partially Correct — Needs Clarification'
                      : isUnanswered
                      ? 'Unanswered / Incomplete Response'
                      : 'Incorrect Answer — Misconception Detected';
                    const feedbackText =
                      currentResult.evaluation.feedback ||
                      currentResult.evaluation.feedback_reason ||
                      currentResult.evaluation.explanation ||
                      currentQ.explanation;

                    return (
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: 'var(--radius-md)',
                          marginBottom: '18px',
                          background: cardBg,
                          border: `1px solid ${cardBorder}`,
                        }}
                      >
                        {/* Status line: Incorrect red / Partial amber / Unanswered slate / Correct green */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {isCorrect ? (
                              <CheckCircle2 size={18} color="#16A34A" />
                            ) : isPartial ? (
                              <AlertTriangle size={18} color="#D97706" />
                            ) : isUnanswered ? (
                              <HelpCircle size={18} color="#64748B" />
                            ) : (
                              <AlertCircle size={18} color="#E11D48" />
                            )}
                            <span style={{ fontSize: '14px', fontWeight: 800, color: textColor }}>
                              {statusText}
                            </span>
                          </div>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              background: badgeBg,
                              color: badgeColor,
                              padding: '2px 8px',
                              borderRadius: '4px',
                            }}
                          >
                            {badgeText}
                          </span>
                        </div>

                        {/* Your Answer and Correct Answer */}
                        <div style={{ background: '#FFFFFF', borderRadius: '6px', padding: '10px 12px', marginBottom: '10px', border: '1px solid #F1F5F9' }}>
                          <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Your Answer: </span>
                            <span style={{ fontWeight: 700, color: isCorrect ? '#16A34A' : isPartial ? '#D97706' : isUnanswered ? '#64748B' : '#DC2626' }}>
                              {currentResult.selectedAnswer || '(No answer entered)'}
                            </span>
                          </div>
                          <div style={{ fontSize: '12px' }}>
                            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Correct Answer: </span>
                            <span style={{ fontWeight: 700, color: '#16A34A' }}>
                              {currentResult.evaluation.correct_answer || currentQ.correct_answer || 'Not specified'}
                            </span>
                          </div>
                        </div>

                        {/* One-line feedback / Explanation */}
                        {feedbackText && (
                          <div style={{ fontSize: '12px', color: isCorrect ? '#166534' : isPartial ? '#78350F' : isUnanswered ? '#334155' : '#881337', lineHeight: 1.45, marginBottom: '12px' }}>
                            <strong>Feedback: </strong>
                            <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                              {feedbackText}
                            </span>
                          </div>
                        )}

                      {/* Three collapsible sections, collapsed by default:
                          1. "Why this is a trap"
                          2. "Authoritative mental model"
                          3. "Source lecture excerpt" */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
                        {/* 1. Why this is a trap */}
                        {(currentResult.evaluation.conceptual_trap || currentQ.target_misconception) && (
                          <details
                            style={{
                              background: '#FFFFFF',
                              borderRadius: '6px',
                              border: '1px solid #FECDD3',
                              padding: '8px 12px',
                              fontSize: '12px',
                              color: '#881337',
                              cursor: 'pointer',
                            }}
                          >
                            <summary style={{ fontWeight: 700, color: '#BE123C', outline: 'none' }}>
                              Why this is a trap
                            </summary>
                            <div style={{ marginTop: '8px', lineHeight: 1.5, color: '#475569', fontSize: '12px' }}>
                              {currentResult.evaluation.conceptual_trap || currentQ.target_misconception}
                            </div>
                          </details>
                        )}

                        {/* 2. Authoritative mental model */}
                        {(currentResult.evaluation.correct_mental_model || currentQ.explanation) && (
                          <details
                            style={{
                              background: '#FFFFFF',
                              borderRadius: '6px',
                              border: '1px solid #BFDBFE',
                              padding: '8px 12px',
                              fontSize: '12px',
                              color: '#1E3A8A',
                              cursor: 'pointer',
                            }}
                          >
                            <summary style={{ fontWeight: 700, color: '#1D4ED8', outline: 'none' }}>
                              Authoritative mental model
                            </summary>
                            <div style={{ marginTop: '8px', lineHeight: 1.5, color: '#334155', fontSize: '12px' }}>
                              {currentResult.evaluation.correct_mental_model || currentQ.explanation}
                            </div>
                          </details>
                        )}

                        {/* 3. Source from Lecture */}
                        {currentQ.question_type === 'mcq' ? (
                          <McqSourceSection
                            lectureTitle={lecture?.title || currentQ.lecture_title}
                            sourceExcerpt={currentQ.source_excerpt || currentResult.evaluation.source_excerpt}
                            sourceTimestamp={currentQ.source_timestamp ?? currentResult.evaluation.source_timestamp}
                            sourceEndTimestamp={currentQ.source_end_timestamp ?? currentResult.evaluation.source_end_timestamp}
                            lectureDuration={duration || lecture?.duration_seconds}
                            onWatchThisPart={handleWatchSourcePart}
                          />
                        ) : (
                          (currentQ.source_excerpt || currentResult.evaluation.source_excerpt) && (
                            <details
                              style={{
                                background: '#FFFFFF',
                                borderRadius: '6px',
                                border: '1px solid #E2E8F0',
                                padding: '8px 12px',
                                fontSize: '12px',
                                color: '#334155',
                                cursor: 'pointer',
                              }}
                            >
                              <summary style={{ fontWeight: 700, color: 'var(--primary-navy)', outline: 'none' }}>
                                Source lecture excerpt
                              </summary>
                              <div style={{ marginTop: '8px', lineHeight: 1.5, color: '#475569', fontStyle: 'italic', fontSize: '12px' }}>
                                "{currentQ.source_excerpt || currentResult.evaluation.source_excerpt}"
                              </div>
                            </details>
                          )
                        )}
                      </div>

                      {/* Action buttons: "Replay Concept", "Mark Unresolved", "Try Again" */}
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', paddingTop: '10px', borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                        <button
                          id="btn-replay-this-concept"
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '12px' }}
                          onClick={() => handleReviewConcept(currentResult.evaluation?.remediation_timestamp ?? currentQ.conceptStartTime)}
                        >
                          <RotateCcw size={13} />
                          <span>Replay Concept</span>
                        </button>

                        <button
                          id="btn-mark-unresolved-checkpoint"
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '12px' }}
                          onClick={() => setShowUnresolvedModal(true)}
                        >
                          <HelpCircle size={13} color="var(--priority-high-text)" />
                          <span>Mark Unresolved</span>
                        </button>

                        <button
                          id="btn-try-again-checkpoint"
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '12px', marginLeft: 'auto' }}
                          onClick={() => handleTryAgain(currentQ.id)}
                        >
                          <RefreshCw size={13} />
                          <span>Try Again</span>
                        </button>
                      </div>
                    </div>
                  );
                })()}

                  {/* Navigation Buttons: ALWAYS visible at the bottom of the card */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '14px', borderTop: '1px solid #E2E8F0' }}>
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
                      <span>{activeQIndex < allQuestions.length - 1 ? 'Next Question' : 'View Summary'}</span>
                      <ArrowRight size={14} />
                    </button>
                  </div>
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
      {/* Rename Lecture Modal */}
      {showRenameModal && (
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
          onClick={() => !renameSaving && setShowRenameModal(false)}
        >
          <div
            className="card"
            style={{ maxWidth: '480px', width: '100%', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Edit3 size={18} color="var(--accent-purple)" />
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>Rename Lecture</h3>
              </div>
              <button
                onClick={() => setShowRenameModal(false)}
                disabled={renameSaving}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            {renameError && (
              <div style={{ padding: '8px 12px', background: '#FEE2E2', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '13px', marginBottom: '12px' }}>
                {renameError}
              </div>
            )}

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                Lecture Title
              </label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                disabled={renameSaving}
                placeholder="Enter lecture title..."
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-strong)',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveRename();
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowRenameModal(false)}
                disabled={renameSaving}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSaveRename}
                disabled={renameSaving || !newTitle.trim()}
              >
                {renameSaving ? 'Saving...' : 'Save Title'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};