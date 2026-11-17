export function normalizeStatus(raw?: string | null): 'Unresolved' | 'Needs Review' | 'Improving' | 'Resolved' {
  const s = (raw || '').trim().toLowerCase();
  if (s === 'resolved') return 'Resolved';
  if (s === 'improving') return 'Improving';
  if (s === 'needs review' || s === 'needs_review') return 'Needs Review';
  return 'Unresolved'; // covers "open", "new", "unresolved", empty
}
