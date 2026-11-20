import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

/* ------------------------------------------------------------------ */
/* Types (local to this page, so nothing else in the project is touched) */
/* ------------------------------------------------------------------ */
interface VideoItem {
  lectureId: number;
  title: string;
  date: string | null;
  hadProblem: boolean;
}

interface ConceptItem {
  id: number;
  name: string;
  status: string;
  mastery: number | null;
  attemptsTotal: number;
  attemptsCorrect: number;
  videos: VideoItem[];
  lastActivity: string | null;
}

interface HistEvidence {
  text: string;
  at: string | null;
}

interface HistMisconception {
  id: number;
  title: string;
  status: string;
  evidence: HistEvidence[];
}

interface HistAttempt {
  question: string;
  answer: string;
  correct: boolean;
  at: string | null;
}

interface HistVideo {
  lectureId: number;
  title: string;
  date: string | null;
  misconceptions: HistMisconception[];
  attempts: HistAttempt[];
}

interface HistoryState {
  loading: boolean;
  error: string | null;
  videos: HistVideo[];
}

/* ------------------------------------------------------------------ */
/* Safe readers: a bad response can never crash the page              */
/* ------------------------------------------------------------------ */
function asRecord(x: unknown): Record<string, unknown> | null {
  return x !== null && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : null;
}
function asArray(x: unknown): unknown[] {
  return Array.isArray(x) ? x : [];
}
function num(x: unknown, fallback = 0): number {
  return typeof x === 'number' && Number.isFinite(x) ? x : fallback;
}
function numOrNull(x: unknown): number | null {
  return typeof x === 'number' && Number.isFinite(x) ? x : null;
}
function str(x: unknown, fallback = ''): string {
  return typeof x === 'string' ? x : fallback;
}
function strOrNull(x: unknown): string | null {
  return typeof x === 'string' && x ? x : null;
}

const LEGACY_STATUS: Record<string, string> = {
  Mastered: 'resolved',
  'Needs Attention': 'needs_attention',
  Improving: 'improving',
  'In Progress': 'improving',
  'Not Started': 'not_started',
};

function normalizeStatus(x: unknown): string {
  const s = str(x, 'not_started');
  return LEGACY_STATUS[s] ?? s;
}

function normalizeConcept(raw: unknown): ConceptItem | null {
  const r = asRecord(raw);
  if (!r) return null;
  const videos: VideoItem[] = asArray(r.videos)
    .map((v): VideoItem | null => {
      const vr = asRecord(v);
      if (!vr) return null;
      return {
        lectureId: num(vr.lecture_id ?? vr.concept_id),
        title: str(vr.title ?? vr.lecture_title, 'Untitled video'),
        date: strOrNull(vr.date),
        hadProblem: vr.had_problem === undefined ? true : Boolean(vr.had_problem),
      };
    })
    .filter((v): v is VideoItem => v !== null);

  return {
    id: num(r.canonical_concept_id ?? r.id),
    name: str(r.concept_name ?? r.name, 'Untitled concept'),
    status: normalizeStatus(r.status),
    mastery: numOrNull(r.mastery ?? r.understanding_percentage),
    attemptsTotal: num(r.attempts_total ?? r.questions_attempted),
    attemptsCorrect: num(r.attempts_correct ?? r.questions_correct),
    videos,
    lastActivity: strOrNull(r.last_activity),
  };
}

function normalizeProgress(raw: unknown): ConceptItem[] {
  const root = asRecord(raw);
  const list = Array.isArray(raw) ? raw : asArray(root ? root.concepts : null);
  return list.map(normalizeConcept).filter((c): c is ConceptItem => c !== null);
}

function normalizeHistory(raw: unknown): HistVideo[] {
  const root = asRecord(raw);
  return asArray(root ? root.videos : null)
    .map((v): HistVideo | null => {
      const vr = asRecord(v);
      if (!vr) return null;
      const misconceptions: HistMisconception[] = asArray(vr.misconceptions)
        .map((m): HistMisconception | null => {
          const mr = asRecord(m);
          if (!mr) return null;
          return {
            id: num(mr.id),
            title: str(mr.title, 'Misconception'),
            status: str(mr.status, 'open'),
            evidence: asArray(mr.evidence).map((e) => {
              const er = asRecord(e);
              return { text: str(er ? er.evidence_text : '', ''), at: strOrNull(er ? er.created_at : null) };
            }),
          };
        })
        .filter((m): m is HistMisconception => m !== null);
      // backend sends attempts oldest first; show newest first
      const attempts: HistAttempt[] = asArray(vr.attempts)
        .map((a) => {
          const ar = asRecord(a);
          return {
            question: str(ar ? ar.question_text : '', ''),
            answer: str(ar ? ar.student_answer : '', ''),
            correct: Boolean(ar && ar.is_correct),
            at: strOrNull(ar ? ar.created_at : null),
          };
        })
        .reverse();
      return {
        lectureId: num(vr.lecture_id),
        title: str(vr.lecture_title, 'Untitled video'),
        date: strOrNull(vr.lecture_date),
        misconceptions,
        attempts,
      };
    })
    .filter((v): v is HistVideo => v !== null);
}

async function callConceptsApi(name: string, ...args: unknown[]): Promise<unknown> {
  const group = api.concepts as unknown as Record<string, unknown>;
  const fn = group ? group[name] : undefined;
  if (typeof fn !== 'function') {
    throw new Error(`api.concepts.${name} is missing in src/services/api.ts`);
  }
  return (fn as (...a: unknown[]) => Promise<unknown>).apply(group, args);
}

/* ------------------------------------------------------------------ */
/* Display helpers                                                    */
/* ------------------------------------------------------------------ */
const STATUS_META: Record<string, { label: string; bg: string; fg: string; border: string }> = {
  needs_attention: { label: 'Needs attention', bg: '#FFF1F2', fg: '#BE123C', border: '#FECDD3' },
  improving: { label: 'Improving', bg: '#FFFBEB', fg: '#B45309', border: '#FDE68A' },
  resolved: { label: 'Resolved', bg: '#F0FDF4', fg: '#166534', border: '#BBF7D0' },
  no_issue: { label: 'No issues', bg: '#F1F5F9', fg: '#475569', border: '#E2E8F0' },
  not_started: { label: 'Not started', bg: '#F1F5F9', fg: '#475569', border: '#E2E8F0' },
};
const STATUS_ORDER: Record<string, number> = {
  needs_attention: 0,
  improving: 1,
  resolved: 2,
  no_issue: 3,
  not_started: 4,
};

function statusMeta(status: string) {
  return STATUS_META[status] ?? STATUS_META.not_started;
}

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString();
}

function masteryColor(m: number): string {
  if (m >= 80) return '#16A34A';
  if (m >= 50) return '#D97706';
  return '#DC2626';
}

/* ------------------------------------------------------------------ */
/* Page                                                               */
/* ------------------------------------------------------------------ */
export const ProgressPage: React.FC<Record<string, unknown>> = () => {
  const [concepts, setConcepts] = useState<ConceptItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [openId, setOpenId] = useState<number | null>(null);
  const [history, setHistory] = useState<Record<number, HistoryState>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const raw = await callConceptsApi('getCanonicalProgress');
      setConcepts(normalizeProgress(raw));
    } catch (err) {
      setConcepts([]);
      setError(err instanceof Error ? err.message : 'Failed to load concept progress.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadHistory = async (id: number) => {
    setHistory((prev) => ({ ...prev, [id]: { loading: true, error: null, videos: [] } }));
    try {
      const raw = await callConceptsApi('getConceptHistory', id);
      setHistory((prev) => ({ ...prev, [id]: { loading: false, error: null, videos: normalizeHistory(raw) } }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load history.';
      setHistory((prev) => ({ ...prev, [id]: { loading: false, error: msg, videos: [] } }));
    }
  };

  const toggleOpen = (id: number) => {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    if (!history[id]) loadHistory(id);
  };

  const counts = useMemo(
    () => ({
      total: concepts.length,
      needs: concepts.filter((c) => c.status === 'needs_attention').length,
      improving: concepts.filter((c) => c.status === 'improving').length,
      resolved: concepts.filter((c) => c.status === 'resolved').length,
    }),
    [concepts]
  );

  const visible = useMemo(() => {
    const list = filter === 'all' ? concepts : concepts.filter((c) => c.status === filter);
    return [...list].sort((a, b) => {
      const sa = STATUS_ORDER[a.status] ?? 9;
      const sb = STATUS_ORDER[b.status] ?? 9;
      if (sa !== sb) return sa - sb;
      const ma = a.mastery ?? 101;
      const mb = b.mastery ?? 101;
      if (ma !== mb) return ma - mb;
      return a.name.localeCompare(b.name);
    });
  }, [concepts, filter]);

  const summaryCard = (label: string, value: number, color: string) => (
    <div className="card" style={{ padding: '14px 16px', textAlign: 'center' }}>
      <div style={{ fontSize: '26px', fontWeight: 900, color }}>{value}</div>
      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>{label}</div>
    </div>
  );

  return (
    <div style={{ paddingBottom: '60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap', marginBottom: '18px' }}>
        <div>
          <h2 style={{ fontSize: '28px', fontWeight: 800, color: 'var(--primary-navy)', margin: 0 }}>Concept Progress</h2>
          <p style={{ fontSize: '15px', color: 'var(--text-muted)', marginTop: '6px' }}>
            Your understanding of each concept, based on your quiz answers across all videos.
          </p>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={14} />
          <span>{loading ? 'Loading...' : 'Refresh'}</span>
        </button>
      </div>

      {error && (
        <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', color: '#991B1B', borderRadius: 'var(--radius-md)', padding: '12px 16px', marginBottom: '16px', fontSize: '14px' }}>
          {error}
        </div>
      )}

      {loading && !error && (
        <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
          Loading your concept progress...
        </div>
      )}

      {!loading && !error && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '18px' }}>
            {summaryCard('Concepts', counts.total, 'var(--primary-navy)')}
            {summaryCard('Needs attention', counts.needs, '#BE123C')}
            {summaryCard('Improving', counts.improving, '#B45309')}
            {summaryCard('Resolved', counts.resolved, '#166534')}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <label htmlFor="progress-filter" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)' }}>
              Show:
            </label>
            <select
              id="progress-filter"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '13px' }}
            >
              <option value="all">All concepts</option>
              <option value="needs_attention">Needs attention</option>
              <option value="improving">Improving</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>

          {visible.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              {concepts.length === 0
                ? 'No concepts with problems yet. Keep studying!'
                : 'No concepts match this filter.'}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {visible.map((c) => {
                const meta = statusMeta(c.status);
                const isOpen = openId === c.id;
                const hist = history[c.id];
                return (
                  <div key={c.id} className="card" style={{ padding: '16px 18px' }}>
                    <button
                      type="button"
                      onClick={() => toggleOpen(c.id)}
                      aria-expanded={isOpen}
                      style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'space-between', gap: '10px', background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '17px', fontWeight: 800, color: 'var(--primary-navy)' }}>{c.name}</span>
                        <span style={{ fontSize: '11px', fontWeight: 800, padding: '3px 10px', borderRadius: '999px', background: meta.bg, color: meta.fg, border: `1px solid ${meta.border}` }}>
                          {meta.label}
                        </span>
                      </div>
                      {isOpen ? <ChevronDown size={18} color="var(--text-muted)" /> : <ChevronRight size={18} color="var(--text-muted)" />}
                    </button>

                    {/* Mastery bar */}
                    <div style={{ marginTop: '12px' }}>
                      {c.mastery === null ? (
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Not attempted yet</div>
                      ) : (
                        <>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                            <span>Understanding</span>
                            <span>{c.mastery}%</span>
                          </div>
                          <div style={{ height: '8px', background: '#E2E8F0', borderRadius: '999px', overflow: 'hidden' }}>
                            <div style={{ width: `${Math.max(0, Math.min(100, c.mastery))}%`, height: '100%', background: masteryColor(c.mastery) }} />
                          </div>
                        </>
                      )}
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
                        {c.attemptsCorrect} of {c.attemptsTotal} answers correct
                      </div>
                    </div>

                    {/* Video names */}
                    {c.videos.length > 0 && (
                      <div style={{ marginTop: '12px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                          Videos ({c.videos.length})
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {c.videos.map((v) => (
                            <span
                              key={`${c.id}-${v.lectureId}-${v.title}`}
                              title={v.hadProblem ? 'Had a problem here' : 'No problem in this video'}
                              style={{
                                fontSize: '12px',
                                padding: '3px 10px',
                                borderRadius: '6px',
                                background: v.hadProblem ? '#FFF1F2' : 'var(--bg-subtle)',
                                color: v.hadProblem ? '#9F1239' : 'var(--text-muted)',
                                border: `1px solid ${v.hadProblem ? '#FECDD3' : 'var(--border-subtle)'}`,
                              }}
                            >
                              {v.title}
                              {v.date ? ` · ${fmtDate(v.date)}` : ''}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* History (loads when opened) */}
                    {isOpen && (
                      <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
                        {!hist || hist.loading ? (
                          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Loading history...</div>
                        ) : hist.error ? (
                          <div style={{ fontSize: '13px', color: '#991B1B' }}>{hist.error}</div>
                        ) : hist.videos.length === 0 ? (
                          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No history yet.</div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            {hist.videos.map((hv) => (
                              <div key={`${c.id}-h-${hv.lectureId}`} style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                                <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                                  {hv.title}
                                  {hv.date ? <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}> · {fmtDate(hv.date)}</span> : null}
                                </div>

                                {hv.misconceptions.map((m) => (
                                  <div key={m.id} style={{ marginTop: '10px' }}>
                                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#9F1239' }}>
                                      {m.title} <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>({m.status})</span>
                                    </div>
                                    {m.evidence.slice(0, 5).map((e, i) => (
                                      <div key={i} style={{ fontSize: '12px', color: '#475569', marginTop: '4px', lineHeight: 1.45 }}>
                                        {e.text}
                                        {e.at ? <span style={{ color: 'var(--text-muted)' }}> ({fmtDate(e.at)})</span> : null}
                                      </div>
                                    ))}
                                  </div>
                                ))}

                                {hv.attempts.length > 0 && (
                                  <div style={{ marginTop: '10px' }}>
                                    <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                                      Your answers (newest first)
                                    </div>
                                    {hv.attempts.slice(0, 8).map((a, i) => (
                                      <div key={i} style={{ fontSize: '12px', marginTop: '4px', color: a.correct ? '#166534' : '#9F1239' }}>
                                        {a.correct ? 'Correct' : 'Incorrect'}: {a.question || 'Question'}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ProgressPage;
