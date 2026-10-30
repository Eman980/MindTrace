import React from 'react';
import {
  Layers,
  FileText,
  GitFork,
  Sparkles,
  BookOpen,
  Network,
  Cpu,
  CheckCircle2,
  Lock
} from 'lucide-react';

export const FYP2RoadmapPage: React.FC = () => {
  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', paddingBottom: '60px' }}>
      <div className="section-header" style={{ textAlign: 'center', display: 'block', marginBottom: '36px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '4px 14px',
            background: 'var(--accent-soft)',
            borderRadius: '9999px',
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--accent-purple)',
            marginBottom: '12px',
          }}
        >
          <Layers size={16} />
          <span>University FYP Project Roadmap</span>
        </div>
        <h1 className="section-title">Scope Architecture: FYP-1 vs FYP-2</h1>
        <p className="section-subtitle" style={{ maxWidth: '720px', margin: '8px auto 0' }}>
          MindTrace is engineered with clean modular abstraction layers. FYP-1 delivers the complete multimedia
          lecture foundation, while FYP-2 expands into multi-modal documents and dependency graphs.
        </p>
      </div>

      {/* FYP-1 vs FYP-2 Scope Matrix */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px', marginBottom: '40px' }}>
        {/* FYP-1 Complete Card */}
        <div className="card" style={{ border: '2px solid #22C55E' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: '#DCFCE7', color: '#16A34A', padding: '8px', borderRadius: 'var(--radius-md)' }}>
                <CheckCircle2 size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary-navy)' }}>FYP-1 Scope</h3>
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#16A34A' }}>Current Complete Working System</div>
              </div>
            </div>
            <span className="badge badge-resolved">Delivered</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={16} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Lecture Media Ingestion:</strong> MP4, MOV, WEBM video and MP3, WAV, M4A, OGG audio.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={16} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Acoustic Speech Transcription:</strong> Timestamped utterance synthesis with mock fallback.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={16} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Concept-Level Segmentation:</strong> Pedagogy-aware section boundaries (not naive time intervals).</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={16} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Interactive Concept Timeline:</strong> Click-to-seek playback with live synchronized transcript.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={16} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Tri-Signal Misconception Engine:</strong> Explicit checkpoints, replay thresholds (≥ 3), and manual flags.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={16} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Persistent Relational Memory:</strong> Multi-session misconception tracking & resolution workflow.</span>
            </div>
          </div>
        </div>

        {/* FYP-2 Architecture Placeholders */}
        <div className="card" style={{ border: '2px solid #6366F1', background: '#FAFAFE' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: 'var(--accent-soft)', color: 'var(--accent-purple)', padding: '8px', borderRadius: 'var(--radius-md)' }}>
                <Sparkles size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary-navy)' }}>FYP-2 Architecture</h3>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-purple)' }}>Future Extension Roadmap</div>
              </div>
            </div>
            <span className="badge badge-improving">Architecture Ready</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <Lock size={16} color="var(--accent-purple)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Multi-Modal Document Learning:</strong> PDF lecture notes, textbook chapters, and PPT slides.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <Lock size={16} color="var(--accent-purple)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Concept Dependency Directed Acyclic Graph (DAG):</strong> Prerequisite relationships mapped visually.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <Lock size={16} color="var(--accent-purple)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Cross-Topic Re-Checking:</strong> Proactive diagnostic mini-quizzes assessing forgotten concepts.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <Lock size={16} color="var(--accent-purple)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Personalized Analogy Bank:</strong> Generates domain analogies customized to student interests.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <Lock size={16} color="var(--accent-purple)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Multi-Course Cohort Support:</strong> Cross-subject tracking across a whole university degree.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Architectural Schema Preview for Viva */}
      <div className="card" style={{ padding: '36px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary-navy)', marginBottom: '14px' }}>
          Viva-Friendly System Architecture Dataflow
        </h2>
        <div
          style={{
            background: 'var(--bg-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '24px',
            fontFamily: 'JetBrains Mono',
            fontSize: '13px',
            lineHeight: 1.7,
            color: 'var(--primary-navy)',
            overflowX: 'auto',
          }}
        >
          {`Student User
   │
   ▼
React + TypeScript Frontend (Single Page Application)
   │  [REST API / Bearer JWT Authorization]
   ▼
FastAPI Backend Application
   ├── Auth Router (Signup, Login, Demo Session)
   ├── Lecture Processing Pipeline (Upload, Chunking, MIME Validation)
   ├── Transcription Service (OpenAI Whisper API with Offline Fallback)
   ├── Concept Segmentation Service (Pedagogical Semantic Chunking)
   ├── Interactive Checkpoint Engine (MCQ exact match & semantic short-answer)
   ├── Playback Telemetry Engine (Replay counting, seek timing, unresolve events)
   ├── Misconception Tracking Engine (Tri-Signal Synthesis: Explicit, Behavioural, Pattern)
   └── Severity Scoring Engine (Transparent Points: 0-2 Low, 3-5 Medium, 6+ High)
   │
   ▼
Relational Storage Layer (SQLite / PostgreSQL)
   ├── users
   ├── lectures & media_files
   ├── transcripts & transcript_segments
   ├── concepts & concept_progress
   ├── checkpoints & checkpoint_attempts
   ├── playback_events
   └── misconceptions & misconception_evidence`}
        </div>
      </div>
    </div>
  );
};
