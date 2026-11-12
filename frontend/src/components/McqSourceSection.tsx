import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, Play, Clock, FileText } from 'lucide-react';

export interface McqSourceSectionProps {
  lectureTitle?: string | null;
  sourceExcerpt?: string | null;
  sourceTimestamp?: number | null;
  sourceEndTimestamp?: number | null;
  lectureDuration?: number | null;
  onWatchThisPart?: (timestamp: number) => void;
  defaultExpanded?: boolean;
}

export const formatLectureTimestamp = (seconds?: number | null): string => {
  if (seconds === undefined || seconds === null || isNaN(seconds) || seconds < 0) {
    return '';
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

export const McqSourceSection: React.FC<McqSourceSectionProps> = ({
  lectureTitle,
  sourceExcerpt,
  sourceTimestamp,
  sourceEndTimestamp,
  lectureDuration,
  onWatchThisPart,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);

  // Validation rules according to specifications:
  // 1. Must have a real transcript excerpt.
  // 2. Never display fake source or invent an excerpt/timestamp.
  // 3. Ensure timestamp falls within actual lecture duration if duration is available.
  const hasValidExcerpt = Boolean(sourceExcerpt && sourceExcerpt.trim().length > 0);
  const hasValidTimestamp =
    sourceTimestamp !== undefined &&
    sourceTimestamp !== null &&
    !isNaN(sourceTimestamp) &&
    sourceTimestamp >= 0 &&
    (lectureDuration && lectureDuration > 0 ? sourceTimestamp <= lectureDuration + 10 : true);

  const formattedStartTime = hasValidTimestamp ? formatLectureTimestamp(sourceTimestamp) : '';
  const formattedEndTime =
    sourceEndTimestamp !== undefined &&
    sourceEndTimestamp !== null &&
    !isNaN(sourceEndTimestamp) &&
    sourceEndTimestamp > (sourceTimestamp ?? 0)
      ? formatLectureTimestamp(sourceEndTimestamp)
      : '';

  const timeDisplay = formattedStartTime
    ? formattedEndTime
      ? `${formattedStartTime} - ${formattedEndTime}`
      : formattedStartTime
    : null;

  return (
    <div
      className="mcq-source-from-lecture"
      style={{
        marginTop: '10px',
        marginBottom: '10px',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        background: isExpanded ? '#FAFAFF' : 'var(--bg-subtle)',
        transition: 'all 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Subtle Expandable Header Button */}
      <button
        type="button"
        className="mcq-source-toggle-btn"
        onClick={() => setIsExpanded((prev) => !prev)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          fontSize: '12px',
          fontWeight: 600,
          color: 'var(--primary-navy)',
          textAlign: 'left',
        }}
        aria-expanded={isExpanded}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <BookOpen size={13} color="var(--accent-purple)" />
          <span>Source from Lecture</span>
        </span>
        {isExpanded ? (
          <ChevronUp size={14} color="var(--text-muted)" />
        ) : (
          <ChevronDown size={14} color="var(--text-muted)" />
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div
          style={{
            padding: '12px 14px',
            borderTop: '1px solid var(--border-subtle)',
            background: '#FFFFFF',
            fontSize: '12px',
            lineHeight: 1.5,
          }}
        >
          {!hasValidExcerpt ? (
            /* Fallback when no reliable source exists (Requirement 5) */
            <div
              style={{
                color: 'var(--text-muted)',
                fontStyle: 'italic',
                padding: '4px 0',
              }}
            >
              Lecture source unavailable.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* Lecture Name */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Lecture:</span>
                <strong style={{ color: 'var(--primary-navy)' }}>
                  {lectureTitle || 'Lecture'}
                </strong>
              </div>

              {/* Lecture Timestamp */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={12} color="var(--accent-purple)" />
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Timestamp:</span>
                <span
                  style={{
                    fontFamily: 'monospace',
                    fontWeight: 700,
                    color: timeDisplay ? 'var(--accent-purple)' : 'var(--text-muted)',
                  }}
                >
                  {timeDisplay ? timeDisplay : 'Unavailable'}
                </span>
              </div>

              {/* Supporting Transcript Excerpt */}
              <div
                style={{
                  background: 'var(--bg-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 12px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    marginBottom: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <FileText size={11} />
                  <span>Supporting Transcript</span>
                </div>
                <div
                  style={{
                    color: '#334155',
                    fontStyle: 'italic',
                    lineHeight: 1.5,
                    fontSize: '12px',
                  }}
                >
                  "{sourceExcerpt?.trim()}"
                </div>
              </div>

              {/* Action Button: Watch This Part */}
              {hasValidTimestamp && onWatchThisPart && (
                <div style={{ marginTop: '4px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => onWatchThisPart(sourceTimestamp as number)}
                    style={{
                      fontSize: '12px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '5px 12px',
                      height: '30px',
                      color: 'var(--accent-purple)',
                      borderColor: 'var(--accent-purple)',
                      background: '#F5F3FF',
                      fontWeight: 600,
                    }}
                    title={`Jump lecture player to ${formattedStartTime}`}
                  >
                    <Play size={11} fill="currentColor" />
                    <span>Watch This Part</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
