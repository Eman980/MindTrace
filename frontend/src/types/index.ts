export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
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
  grade?: 'correct' | 'partial' | 'incorrect';
  attempt_number?: number;
  created_at: string;
  correct_answer?: string;
  explanation?: string;
}

export interface Checkpoint {
  id: number;
  concept_id: number;
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
  misconception_created_or_updated: boolean;
  new_severity_level?: string;
  grade?: 'correct' | 'partial' | 'incorrect';
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
  course_code: string;
  description?: string;
  duration_seconds: number;
  media_type: 'video' | 'audio';
  status: 'processing' | 'ready' | 'failed';
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
  lecture_id: number;
  lecture_title?: string;
  concept_id: number;
  concept_name: string;
  title: string;
  summary?: string;
  incorrect_understanding?: string;
  correct_explanation?: string;
  concept_start_time?: number;
  concept_end_time?: number;
  severity_score: number;
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

export interface LedgerAttempt {
  id: number;
  checkpoint_id: number;
  is_correct: boolean;
  confidence_level?: number;
  explanation_text?: string;
  explanation_verdict?: string;
  created_at: string;
}

export interface MisconceptionLedgerItem extends Misconception {
  remediation_start_time?: number;
  remediation_end_time?: number;
  attempts: LedgerAttempt[];
}
