import type {
  AuthResponse,
  DashboardStats,
  Lecture,
  Misconception,
  MisconceptionEvidence,
  MisconceptionReviewData,
  MisconceptionStats,
  CheckpointEvaluation,
  Concept,
  User,
  ReprobeItem,
  MisconceptionLedgerItem,
  PrerequisiteRecheck,
  PrerequisiteRecheckSubmitResult,
  MisconceptionDetail,
} from '../types';

const API_BASE = 'http://127.0.0.1:8000/api/v1';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('mindtrace_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...getAuthHeader(),
    ...(options.headers as Record<string, string> || {}),
  };

  // Only set Content-Type to application/json if body is not FormData
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (networkErr: any) {
    console.error('[API Network Error]', networkErr);
    throw new Error('Server connection error. Unable to connect to the MindTrace backend. Please ensure the backend is running at http://127.0.0.1:8000.');
  }

  if (!response.ok) {
    let errorDetail = 'An unexpected error occurred.';
    try {
      const errJson = await response.json();
      if (Array.isArray(errJson.detail)) {
        errorDetail = errJson.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
      } else if (typeof errJson.detail === 'string') {
        errorDetail = errJson.detail;
      } else if (errJson.message) {
        errorDetail = errJson.message;
      }
    } catch {
      errorDetail = await response.text() || response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  auth: {
    signup: (data: { email: string; password: string; full_name: string }) =>
      request<AuthResponse>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    login: (data: { email: string; password: string }) =>
      request<AuthResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    forgotPassword: (data: { email: string }) =>
      request<{
        success: boolean;
        message: string;
        email_sent: boolean;
        reset_token?: string | null;
        note?: string | null;
      }>('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    resetPassword: (data: { token: string; new_password: string; confirm_password: string }) =>
      request<{
        success: boolean;
        message: string;
      }>('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getMe: () => request<User>('/auth/me'),
  },

  dashboard: {
    getStats: () => request<DashboardStats>('/dashboard/stats'),
  },

  lectures: {
    list: () => request<Lecture[]>('/lectures'),
    get: (id: number) => request<Lecture>(`/lectures/${id}`),
    update: (
      id: number,
      data: {
        title?: string;
        description?: string;
        course_code?: string;
        prerequisite_lecture_id?: number | null;
      }
    ) =>
      request<{
        success: boolean;
        message: string;
        id: number;
        title: string;
        course_code?: string;
        description?: string;
        prerequisite_lecture_id?: number | null;
        prerequisite_lecture_title?: string | null;
      }>(`/lectures/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    rename: (id: number, data: string | { title: string; description?: string; course_code?: string }) => {
      const payload = typeof data === 'string' ? { title: data } : data;
      return request<{ success: boolean; message: string; id: number; title: string; course_code?: string; description?: string }>(
        `/lectures/${id}/rename`,
        {
          method: 'PATCH',
          body: JSON.stringify(payload),
        }
      );
    },
    upload: (formData: FormData) =>
      request<{
        success: boolean;
        lecture_id: number;
        recording_id: number;
        title: string;
        status: string;
        duration_seconds: number;
        concepts_count: number;
        is_duplicate?: boolean;
        quality_warning?: string | null;
        message?: string;
      }>(
        '/lectures/upload',
        {
          method: 'POST',
          body: formData,
        }
      ),
    delete: (id: number) =>
      request<{ success: boolean; message: string }>(`/lectures/${id}`, {
        method: 'DELETE',
      }),
    deleteAll: () =>
      request<{ success: boolean; message: string; deleted_count: number }>('/lectures/all', {
        method: 'DELETE',
      }),
    getMediaUrl: (lectureId: number) => `${API_BASE}/lectures/${lectureId}/media`,
    getRechecks: (lectureId: number) =>
      request<PrerequisiteRecheck[]>(`/lectures/${lectureId}/rechecks`),
    submitRecheck: (
      lectureId: number,
      data: { misconception_id: number; checkpoint_id: number; student_answer: string }
    ) =>
      request<PrerequisiteRecheckSubmitResult>(`/lectures/${lectureId}/rechecks/submit`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  concepts: {
    getProgress: () => request<Concept[]>('/concepts/progress'),
    getDetail: (id: number) => request<Concept>(`/concepts/${id}`),
  },

  checkpoints: {
    submitAnswer: (data: {
      checkpoint_id: number;
      student_answer: string;
      confidence_level?: number;
      explanation_text?: string;
    }) =>
      request<CheckpointEvaluation>('/checkpoints/answer', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  playback: {
    recordEvent: (data: {
      lecture_id: number;
      concept_id?: number | null;
      event_type: string;
      timestamp_in_media: number;
      details?: Record<string, any>;
    }) =>
      request<{ recorded: boolean; replay_signal_triggered: boolean; message: string }>('/playback/event', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    markUnresolved: (data: {
      lecture_id: number;
      concept_id: number;
      timestamp_in_media: number;
      reason?: string;
    }) =>
      request<{
        success: boolean;
        message: string;
        misconception_id: number;
        severity_level: string;
        severity_score: number;
      }>('/playback/unresolved', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  misconceptions: {
    list: (params?: { priority?: string; status_filter?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.priority && params.priority !== 'All') {
        searchParams.append('priority', params.priority);
      }
      if (params?.status_filter && params.status_filter !== 'All') {
        searchParams.append('status_filter', params.status_filter);
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
      return request<Misconception[]>(`/misconceptions${query}`);
    },
    stats: () => request<MisconceptionStats>('/misconceptions/stats'),
    getLedger: () => request<MisconceptionLedgerItem[]>('/misconceptions/ledger'),
    getReprobe: () => request<ReprobeItem[]>('/misconceptions/reprobe'),
    getReview: (id: number) => request<MisconceptionReviewData>(`/misconceptions/${id}/review`),
    getDetails: (id: number) => request<MisconceptionDetail>(`/misconceptions/${id}/details`),
    resolve: (id: number, data: { checkpoint_id: number; student_answer: string }) =>
      request<{
        is_correct: boolean;
        feedback_reason: string;
        new_status: string;
        new_severity_level: string;
        new_severity_score: number;
        message: string;
      }>(`/misconceptions/${id}/resolve`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateStatus: (id: number, status: string) =>
      request<{
        success: boolean;
        message: string;
        misconception_id: number;
        status: string;
        severity_level: string;
        severity_score: number;
        resolved_at?: string | null;
        evidence_entry?: MisconceptionEvidence;
      }>(`/misconceptions/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
    downloadEvidenceCsv: async () => {
      const headers = getAuthHeader();
      const response = await fetch(`${API_BASE}/misconceptions/export-evidence`, {
        headers,
      });
      if (!response.ok) {
        throw new Error('Failed to download evidence CSV');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mindtrace_evidence_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    },
  },

  demo: {
    seed: () =>
      request<{ success: boolean; message: string; lecture_id: number; title: string }>('/demo/seed', {
        method: 'POST',
      }),
    resetSample: () =>
      request<{ success: boolean; message: string; lecture_id: number; title: string }>('/demo/reset-sample', {
        method: 'POST',
      }),
  },
};
