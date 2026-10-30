import React from 'react';
import {
  Brain,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Layers,
  Activity,
  FileCheck,
  ShieldCheck,
  Compass,
  Zap,
  BookOpen
} from 'lucide-react';

interface LandingPageProps {
  setActiveTab: (tab: string) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ setActiveTab }) => {
  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* Hero Section */}
      <section
        style={{
          textAlign: 'center',
          padding: '60px 20px 70px',
          maxWidth: '920px',
          margin: '0 auto',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 16px',
            background: 'var(--accent-soft)',
            border: '1px solid #C7D2FE',
            borderRadius: 'var(--radius-full)',
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--accent-purple)',
            marginBottom: '24px',
          }}
        >
          <Sparkles size={16} />
          <span>Intelligent Learning Companion • Evidence-Based EdTech</span>
        </div>

        <h1
          style={{
            fontSize: 'clamp(32px, 5vw, 54px)',
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: '-1.5px',
            color: 'var(--navy-800)',
            marginBottom: '20px',
          }}
        >
          Understand What You Understand.
        </h1>

        <p
          style={{
            fontSize: '18px',
            color: 'var(--text-muted)',
            lineHeight: 1.6,
            maxWidth: '740px',
            margin: '0 auto 36px',
          }}
        >
          MindTrace is an intelligent learning companion that actively detects, tracks, and systematically resolves
          persistent misconceptions while you study from course lecture recordings.
        </p>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            id="hero-signup-btn"
            className="btn btn-primary btn-lg"
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '14px 28px', fontSize: '15px' }}
            onClick={() => setActiveTab('signup')}
          >
            <span>Get Started</span>
            <ArrowRight size={18} />
          </button>
          <button
            id="hero-signin-btn"
            className="btn btn-secondary btn-lg"
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '14px 28px', fontSize: '15px' }}
            onClick={() => setActiveTab('login')}
          >
            <span>Sign In</span>
          </button>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '24px',
            marginTop: '36px',
            fontSize: '13px',
            color: 'var(--text-muted)',
            flexWrap: 'wrap'
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={16} color="var(--primary-accent)" /> Multi-Modal Misconception Tracking
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={16} color="var(--primary-accent)" /> Evidence-Based State Machine
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Compass size={16} color="var(--primary-accent)" /> Video Remediation Anchors
          </span>
        </div>
      </section>

      {/* 4-Step Academic Workflow */}
      <section style={{ marginBottom: '60px' }}>
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h2 style={{ fontSize: '28px', fontWeight: 800, color: 'var(--navy-800)', marginBottom: '10px' }}>
            How MindTrace Works in 4 Steps
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '16px' }}>
            From raw lecture media to structured, evidence-backed mastery.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px' }}>
          <div className="card card-hover" style={{ position: 'relative' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: 'var(--primary-accent)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '15px',
                marginBottom: '16px',
              }}
            >
              1
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: 'var(--navy-800)' }}>
              Upload & Transcription
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Upload any lecture recording (.mp4, .mp3, etc.). MindTrace transcribes the spoken content into structured, timestamped text.
            </p>
          </div>

          <div className="card card-hover" style={{ position: 'relative' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: 'var(--accent-purple)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '15px',
                marginBottom: '16px',
              }}
            >
              2
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: 'var(--navy-800)' }}>
              Concept Segmentation
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              The lecture is parsed into cohesive concept blocks with clear time boundaries, avoiding arbitrary equal-time slicing.
            </p>
          </div>

          <div className="card card-hover" style={{ position: 'relative' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: '#D97706',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '15px',
                marginBottom: '16px',
              }}
            >
              3
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: 'var(--navy-800)' }}>
              Checkpoints & Tracking
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Targeted checkpoints and replay telemetry record friction points, tracking severity levels and student confidence.
            </p>
          </div>

          <div className="card card-hover" style={{ position: 'relative' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: '#16A34A',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '15px',
                marginBottom: '16px',
              }}
            >
              4
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: 'var(--navy-800)' }}>
              Review & Ledger Resolution
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Review identified misconceptions with targeted explanations, spaced transfer probes, and verifiable evidence resolution.
            </p>
          </div>
        </div>
      </section>

      {/* Production Call to Action Banner */}
      <section
        style={{
          background: 'linear-gradient(135deg, var(--primary-navy) 0%, var(--navy-800) 100%)',
          color: 'white',
          borderRadius: 'var(--radius-xl)',
          padding: '48px 36px',
          textAlign: 'center',
        }}
      >
        <h2 style={{ fontSize: '28px', fontWeight: 800, marginBottom: '12px' }}>
          Empower Your Learning with Verifiable Understanding
        </h2>
        <p style={{ fontSize: '16px', color: '#CBD5E1', maxWidth: '680px', margin: '0 auto 28px' }}>
          Upload your own course lecture recordings to experience automated concept segmentation,
          active misconception tracking, and spaced transfer resolution in real time.
        </p>
        <button
          className="btn btn-primary btn-lg"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '14px 28px' }}
          onClick={() => setActiveTab('signup')}
        >
          <span>Get Started</span>
          <ArrowRight size={18} />
        </button>
      </section>
    </div>
  );
};
