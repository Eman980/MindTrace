import React from 'react';
import {
  Brain,
  MessageSquareX,
  Database,
  Activity,
  Layers,
  CheckCircle2,
  Sparkles,
  ShieldCheck,
  Scale
} from 'lucide-react';

export const DifferentiationPage: React.FC = () => {
  return (
    <div style={{ maxWidth: '920px', margin: '0 auto', paddingBottom: '60px' }}>
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
          <Scale size={16} />
          <span>Academic Viva Research Distinction</span>
        </div>
        <h1 className="section-title">What Makes MindTrace Different from ChatGPT?</h1>
        <p className="section-subtitle" style={{ maxWidth: '720px', margin: '8px auto 0' }}>
          MindTrace is not a conversational chatbot. It is a purpose-built multimedia learning companion
          architected around persistent, evidence-backed misconception diagnosis.
        </p>
      </div>

      {/* Comparison Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px', marginBottom: '40px' }}>
        {/* Generic LLM Card */}
        <div className="card" style={{ background: '#FFF1F2', borderColor: '#FECDD3' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <div style={{ background: '#FEE2E2', color: '#DC2626', padding: '8px', borderRadius: 'var(--radius-md)' }}>
              <MessageSquareX size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#9F1239' }}>Standard AI Chatbots</h3>
              <div style={{ fontSize: '12px', color: '#BE123C' }}>e.g. ChatGPT, Gemini Conversational Interface</div>
            </div>
          </div>

          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px', color: '#4C0519' }}>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <span style={{ color: '#DC2626', fontWeight: 800 }}>✕</span>
              <span><strong>Passive Interaction:</strong> Waits for the student to ask a question. Students unaware of their misunderstandings never inquire.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <span style={{ color: '#DC2626', fontWeight: 800 }}>✕</span>
              <span><strong>Isolated Sessions:</strong> Treats each chat thread as a distinct conversation, lacking a structured longitudinal knowledge graph.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <span style={{ color: '#DC2626', fontWeight: 800 }}>✕</span>
              <span><strong>Zero Playback Telemetry:</strong> Cannot observe video scrubbing, concept replay thresholds, or pause patterns.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <span style={{ color: '#DC2626', fontWeight: 800 }}>✕</span>
              <span><strong>No Severity Prioritization:</strong> Answers student queries equally without classifying which topics pose high exam risks.</span>
            </li>
          </ul>
        </div>

        {/* MindTrace Card */}
        <div className="card" style={{ background: '#F0FDF4', borderColor: '#BBF7D0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <div style={{ background: '#DCFCE7', color: '#16A34A', padding: '8px', borderRadius: 'var(--radius-md)' }}>
              <Brain size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#14532D' }}>MindTrace Learning Platform</h3>
              <div style={{ fontSize: '12px', color: '#15803D' }}>University FYP-1 Implementation</div>
            </div>
          </div>

          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px', color: '#052E16' }}>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={18} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Proactive Diagnosis:</strong> Evaluates understanding after each concept segment without waiting for students to recognize confusion.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={18} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Persistent Relational Memory:</strong> Misconceptions are saved in a relational database schema across study days until verified resolved.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={18} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Behavioural Evidence:</strong> Integrates replay counts (≥ 3 times) and manual 'Mark as Unresolved' clicks directly into the evidence trail.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <CheckCircle2 size={18} color="#16A34A" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Severity Scoring Algorithm:</strong> Calculates transparent priority scores (Low, Medium, High) to focus revision time effectively.</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Deep-Dive Architectural Points (Section 27) */}
      <div className="card" style={{ padding: '36px' }}>
        <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--primary-navy)', marginBottom: '20px' }}>
          6 Core Pillars of MindTrace Differentiation
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '24px' }}>
          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-purple)', marginBottom: '6px' }}>
              1. Proactive Detection
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Detects friction through targeted checkpoints tied to concept boundaries, revealing misunderstandings the student didn't know they possessed.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-purple)', marginBottom: '6px' }}>
              2. Structured Persistent Memory
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Not ephemeral context windows. Misconceptions are normalized relational database entities with foreign keys linking back to lectures and concepts.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-purple)', marginBottom: '6px' }}>
              3. Telemetry from Video Playback
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              MindTrace tracks media events: pausing repeatedly on a segment or seeking backwards 3+ times triggers a behavioural signal.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-purple)', marginBottom: '6px' }}>
              4. Evidence-Based Severity
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Transparent additive scoring: checkpoint failure (+2), replay friction (+2), manual unresolved flag (+3). Quantifies revision urgency.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-purple)', marginBottom: '6px' }}>
              5. Concept-Specific Checkpoints
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Checkpoints are explicitly aligned with timestamped concept boundaries, rather than summarizing whole lectures generically.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-purple)', marginBottom: '6px' }}>
              6. Active Resolution Workflow
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              A misconception does not magically resolve on its own; students must read the targeted diagnosis and pass a verification checkpoint.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
