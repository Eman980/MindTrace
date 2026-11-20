export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'student' | 'teacher' | string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TranscriptSegment {
  id: number;
  start_time: number;
  end_time: number;
  text: string;
  speaker: string;
  segment_index: number;
}

export interface Transcript {
  id: number;
  full_text: string;
  word_count: number;
  provider: string;
  segments: TranscriptSegment[];
}

export interface CheckpointAttemptDetail {
  id: number;
  checkpoint_id: number;
  student_answer: string;
  is_correct: boolean;
  confidence_score?: number;
  feedback_reason?: string;
  detected_misconception_note?: string;
  confidence_level?: number;
  explanation_text?: string;
  explanation_verdict?: string;
  grade?: 'correct' | 'partial' | 'incorrect' | 'unanswered';
  verdict?: 'correct' | 'partial' | 'incorrect' | 'unanswered';
  feedback?: string;
  attempt_number?: number;
  created_at: string;
  correct_answer?: string;
  explanation?: string;
}

export interface Checkpoint {
  id: number;
  concept_id: number;
  lecture_id?: number;
  lecture_title?: string;
  question_type: 'mcq' | 'short' | 'short_answer' | 'scenario';
  difficulty?: 'easy' | 'moderate';
  scenario_text?: string;
  question_text: string;
  options: string[];
  explanation?: string;
  correct_answer?: string;
  order_index: number;
  is_review_checkpoint: boolean;
  item_family_role?: 'original' | 'variant' | 'transfer';
  target_misconception?: string;
  source_excerpt?: string;
  source_timestamp?: number;
  source_start_timestamp?: number;
  source_end_timestamp?: number;
  attempts?: CheckpointAttemptDetail[];
  latest_attempt?: CheckpointAttemptDetail | null;
}

export interface CheckpointEvaluation {
  checkpoint_id: number;
  student_answer: string;
  is_correct: boolean;
  confidence: number;
  feedback_reason: string;
  detected_misconception_note?: string;
  conceptual_trap?: string;
  correct_mental_model?: string;
  remediation_timestamp?: number;
  concept_id?: number;
  concept_title?: string;
  correct_answer?: string;
  explanation?: string;
  points_awarded: number;
  score?: number;
  max_score?: number;
  percentage?: number;
  rubric_breakdown?: Array<{
    criterion: string;
    status: 'correct' | 'partial' | 'missing' | 'incorrect';
    points_awarded: number;
    max_points: number;
    notes?: string;
  }>;
  what_understood?: string;
  what_missing?: string;
  what_needs_correction?: string;
  how_to_improve?: string;
  misconception_created_or_updated: boolean;
  new_severity_level?: string;
  grade?: 'correct' | 'partial' | 'incorrect' | 'unanswered';
  verdict?: 'correct' | 'partial' | 'incorrect' | 'unanswered';
  feedback?: string;
  missing_point?: string;
  explanation_verdict?: string;
  verdict_reason?: string;
  needs_followup?: boolean;
  evidence_status?: string;
  attempt_id?: number;
  attempt_number?: number;
  total_attempts?: number;
  attempts?: CheckpointAttemptDetail[];
  source_excerpt?: string;
  source_timestamp?: number;
  source_start_timestamp?: number;
  source_end_timestamp?: number;
  lecture_id?: number;
  lecture_title?: string;
}

export interface Concept {
  id: number;
  lecture_id: number;
  title: string;
  description: string;
  start_time: number;
  end_time: number;
  order_index: number;
  confidence_score: number;
  transcript_text?: string;
  core_concepts?: string[];
  confusing_topics?: string[];
  checkpoints_count: number;
  checkpoints?: Checkpoint[];
  replay_count: number;
  understanding_percentage: number;
  status: 'Not Started' | 'In Progress' | 'Needs Attention' | 'Improving' | 'Mastered';
}

export interface MediaFile {
  id: number;
  original_filename: string;
  file_size: number;
  mime_type: string;
  file_path: string;
}

export interface Lecture {
  id: number;
  title: string;
  course_code?: string | null;
  course_id?: number | null;
  description?: string;
  duration_seconds: number;
  media_type: 'video' | 'audio';
  status: 'processing' | 'ready' | 'failed';
  processing_status?: 'uploaded' | 'transcribing' | 'segmenting' | 'generating' | 'ready' | 'failed' | string;
  progress?: number;
  error_message?: string | null;
  processing_error?: string;
  is_demo: boolean;
  prerequisite_lecture_id?: number | null;
  prerequisite_lecture_title?: string | null;
  created_at: string;
  concepts_count: number;
  unresolved_count: number;
  progress_percentage: number;
  media_url?: string;
  media_file?: MediaFile;
  transcript?: Transcript;
  concepts?: Concept[];
}

export interface MisconceptionEvidence {
  id: number;
  signal_type: 'explicit_checkpoint' | 'behavioural_replay' | 'manual_unresolved' | 'conversational_pattern' | 'checkpoint_resolved';
  evidence_text: string;
  points_added: number;
  created_at: string;
}

export interface Misconception {
  id: number;
  user_id: number;
  lecture_id?: number | null;
  lecture_title?: string;
  concept_id?: number | null;
  concept_name: string;
  title: string;
  summary?: string;
  incorrect_understanding?: string;
  correct_explanation?: string;
  concept_start_time?: number;
  concept_end_time?: number;
  severity_score: number;
  current_score?: number;
  peak_score?: number;
  severity_level: 'Low' | 'Medium' | 'High';
  occurrence_count: number;
  status: 'Unresolved' | 'Needs Review' | 'In Progress' | 'Resolved' | string;
  first_detected: string;
  last_detected: string;
  evidence: MisconceptionEvidence[];
  evidence_status?: 'Suspected' | 'Confirmed' | 'Memorized' | 'Resolved' | 'Recurred';
  memorized_flag?: boolean;
  recurrence_count?: number;
  remediation_segment_id?: number;
  resolved_at?: string;
  improving_at?: string;
  recheck_due?: string;
  relapse_count?: number;
  is_archived?: boolean;
  root_cause_concept?: string;
  root_cause_lecture_title?: string;
  root_cause_lecture_id?: number;
}

export interface MisconceptionStats {
  total_detected: number;
  high_priority: number;
  medium_priority: number;
  low_priority: number;
  unresolved: number;
  improving: number;
  resolved: number;
}

export interface DashboardStats {
  total_lectures: number;
  concepts_identified: number;
  misconceptions_detected: number;
  unresolved_concepts: number;
  concepts_improved: number;
  recent_lectures: Lecture[];
  misconception_summary: MisconceptionStats;
}

export interface MisconceptionReviewData {
  misconception: Misconception;
  concept_title: string;
  concept_start_time: number;
  concept_end_time: number;
  transcript_snippet: string;
  previous_bad_answer?: string;
  why_problematic: string;
  clarification_explanation: string;
  review_checkpoint?: Checkpoint;
}

export interface ReprobeItem {
  misconception_id: number;
  concept_id: number;
  concept_name: string;
  lecture_id: number;
  lecture_title?: string;
  title: string;
  evidence_status?: string;
  severity_level: string;
  severity_score: number;
  last_detected: string;
  hours_since_last_seen: number;
  required_delay_hours: number;
  is_due: boolean;
  reprobe_checkpoint?: Checkpoint;
}

export interface PrerequisiteRecheckQuestion {
  id: number;
  concept_id: number;
  question_type: string;
  question_text: string;
  options: string[];
  explanation?: string;
  item_family_role?: string;
}

export interface PrerequisiteRecheck {
  misconception_id: number;
  misconception_title: string;
  earlier_lecture_id: number;
  earlier_lecture_title: string;
  earlier_concept_id: number;
  earlier_concept_name: string;
  dependent_concept_name: string;
  question: PrerequisiteRecheckQuestion;
}

export interface PrerequisiteRecheckSubmitResult {
  is_correct: boolean;
  correct_answer?: string;
  explanation?: string;
  new_status: string;
  new_severity_level: string;
  new_severity_score: number;
  message: string;
}

export interface MisconceptionAttemptHistoryItem {
  question: string;
  student_answer: string;
  correct_answer?: string;
  is_correct: boolean;
  context_type: string;
  explanation?: string;
  created_at?: string;
}

export interface MisconceptionDetail {
  id: number;
  concept_id?: number | null;
  concept_name: string;
  lecture_id?: number | null;
  lecture_title?: string;
  why_detected: string;
  original_question: string;
  student_wrong_answer: string;
  correct_answer: string;
  detection_evidence: string;
  lecture_evidence: string;
  concept_start_time?: number;
  concept_end_time?: number;
  marked_unresolved: boolean;
  marked_unresolved_reason: string;
  status: string;
  severity_level: string;
  severity_score: number;
  current_score?: number;
  peak_score?: number;
  improving_at?: string;
  recheck_due?: string;
  next_reassessment_info?: string;
  relapse_count: number;
  is_archived?: boolean;
  resolved_at?: string;
  assessment_history: MisconceptionAttemptHistoryItem[];
}

// ─── Concept-wise progress (canonical concepts across videos) ────────────────
export interface CanonicalVideoProgress {
  lecture_id: number;
  lecture_title: string;
  concept_id: number;
  start_time: number;
  end_time: number;
  questions_attempted: number;
  questions_correct: number;
}

export interface CanonicalConceptProgress {
  id: number;
  name: string;
  questions_attempted: number;
  questions_correct: number;
  open_misconceptions: number;
  understanding_percentage: number;
  status: 'Not Started' | 'Needs Attention' | 'Improving' | 'Mastered';
  videos: CanonicalVideoProgress[];
}

// ─── Teacher Courses (Teacher Insights Phase 2) ─────────────────────────────
export interface Course {
  id: number;
  teacher_id: number;
  title: string;
  course_code?: string | null;
  description?: string | null;
  join_code: string;
  created_at: string;
  updated_at: string;
}

export interface CourseCreateIn {
  title: string;
  course_code?: string;
  description?: string;
}

export interface CourseUpdateIn {
  title?: string;
  course_code?: string;
  description?: string;
}

// ─── Student Courses & Consent (Teacher Insights Phase 3) ───────────────────
export interface CoursePreviewIn {
  join_code: string;
}

export interface CoursePreview {
  course_id: number;
  title: string;
  course_code?: string | null;
  description?: string | null;
  teacher_name: string;
  already_enrolled: boolean;
  enrollment_status?: string | null;
}

export interface CourseJoinIn {
  join_code: string;
  consent_granted: boolean;
}

export interface StudentEnrollment {
  id: number;
  course_id: number;
  title: string;
  course_code?: string | null;
  description?: string | null;
  teacher_name: string;
  consent_granted: boolean;
  status: string;
  consent_at?: string | null;
  created_at: string;
  associated_lectures_count: number;
}

export interface AssociatedLecture {
  id: number;
  title: string;
  course_code?: string | null;
  created_at?: string;
  prerequisite_lecture_id?: number | null;
  prerequisite_lecture_title?: string | null;
}

// ══════════════════════════════════════════════════════════════════════════════
// Assessment Types (Complete Difficulty-Based Assessment System)
// ══════════════════════════════════════════════════════════════════════════════

export type AssessmentDifficulty = 'easy' | 'moderate' | 'hard';

export interface AssessmentQuestion {
  id: string;
  type: 'mcq' | 'short_answer';
  difficulty: AssessmentDifficulty;
  question_text: string;
  options?: string[] | null;
  max_points: number;
  concept_id?: number | null;
  concept_title?: string | null;
  source_timestamp?: number | null;
}

export interface Assessment {
  id: number;
  lecture_id: number;
  difficulty: AssessmentDifficulty;
  title: string;
  description: string;
  total_questions: number;
  mcq_count: number;
  short_answer_count: number;
  max_score: number;
  questions: AssessmentQuestion[];
}

export interface AssessmentStartResponse {
  attempt_id: number;
  attempt_number?: number;
  resumed: boolean;
  assessment: Assessment;
  in_progress_answers: Record<string, string>;
}

export interface AssessmentRubricItem {
  criterion: string;
  status: 'correct' | 'partial' | 'missing' | 'incorrect';
  points_awarded: number;
  max_points: number;
  notes?: string | null;
}

export interface AssessmentQuestionResult {
  question_id: string;
  question_text: string;
  type: 'mcq' | 'short_answer';
  difficulty: AssessmentDifficulty;
  student_answer: string;
  correct_answer: string;
  explanation?: string | null;
  is_correct: boolean;
  verdict: 'correct' | 'partial' | 'incorrect';
  score: number;
  max_score: number;
  percentage: number;
  feedback: string;
  rubric_breakdown?: AssessmentRubricItem[] | null;
  what_understood?: string | null;
  what_missing?: string | null;
  what_needs_correction?: string | null;
  how_to_improve?: string | null;
  concept_id?: number | null;
  concept_title?: string | null;
  remediation_timestamp?: number | null;
}

export interface AssessmentRecommendedRevision {
  concept_id?: number | null;
  concept_title: string;
  timestamp: number;
  reason: string;
}

export interface AssessmentResult {
  attempt_id: number;
  attempt_number?: number;
  assessment_id: number;
  lecture_id: number;
  difficulty: AssessmentDifficulty;
  status: string;
  total_score: number;
  max_score: number;
  percentage: number;
  mcq_correct_count: number;
  mcq_total_count: number;
  short_score: number;
  short_max_score: number;
  question_results: AssessmentQuestionResult[];
  concepts_understood: string[];
  concepts_partially_understood?: string[];
  concepts_needing_improvement: string[];
  recommended_revision: AssessmentRecommendedRevision[];
  submitted_at?: string | null;
}

export interface AssessmentAttemptSummary {
  id: number;
  attempt_number?: number;
  assessment_id: number;
  difficulty: AssessmentDifficulty;
  status: string;
  total_score: number;
  max_score: number;
  percentage: number;
  submitted_at?: string | null;
  started_at: string;
}

export interface AssessmentStatus {
  lecture_id: number;
  completed_difficulties: string[];
  in_progress_attempt?: {
    attempt_id: number;
    assessment_id: number;
    difficulty: AssessmentDifficulty;
    started_at: string;
    saved_answers: Record<string, string>;
    total_questions: number;
  } | null;
  attempts: AssessmentAttemptSummary[];
}

