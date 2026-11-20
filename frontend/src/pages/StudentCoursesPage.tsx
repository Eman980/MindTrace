import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { StudentEnrollment, CoursePreview, AssociatedLecture } from '../types';
import {
  GraduationCap,
  Plus,
  BookOpen,
  KeyRound,
  CheckCircle2,
  AlertCircle,
  X,
  Calendar,
  Layers,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  LogOut,
  Info,
  RefreshCw,
  FileText,
  UserCheck
} from 'lucide-react';

export const StudentCoursesPage: React.FC = () => {
  const [enrollments, setEnrollments] = useState<StudentEnrollment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Join Modal State
  const [isJoinOpen, setIsJoinOpen] = useState<boolean>(false);
  const [joinStep, setJoinStep] = useState<'input' | 'preview'>('input');
  const [inputCode, setInputCode] = useState<string>('');
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [preview, setPreview] = useState<CoursePreview | null>(null);
  const [consentChecked, setConsentChecked] = useState<boolean>(false);
  const [joining, setJoining] = useState<boolean>(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  // Disconnect Confirmation State
  const [disconnectingCourse, setDisconnectingCourse] = useState<StudentEnrollment | null>(null);
  const [disconnecting, setDisconnecting] = useState<boolean>(false);
  const [disconnectError, setDisconnectError] = useState<string | null>(null);

  // Associated Lectures Modal State
  const [activeLecturesCourse, setActiveLecturesCourse] = useState<StudentEnrollment | null>(null);
  const [associatedLectures, setAssociatedLectures] = useState<AssociatedLecture[]>([]);
  const [loadingLectures, setLoadingLectures] = useState<boolean>(false);
  const [lecturesError, setLecturesError] = useState<string | null>(null);

  // Success Notification Banner
  const [notification, setNotification] = useState<string | null>(null);

  const fetchEnrollments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.student.courses.list();
      setEnrollments(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load enrolled courses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEnrollments();
  }, []);

  const openJoinModal = () => {
    setInputCode('');
    setVerifyError(null);
    setPreview(null);
    setConsentChecked(false);
    setJoinError(null);
    setJoinStep('input');
    setIsJoinOpen(true);
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = inputCode.trim().toUpperCase();
    if (!code) {
      setVerifyError('Please enter a course joining code.');
      return;
    }

    setVerifying(true);
    setVerifyError(null);
    try {
      const previewData = await api.student.courses.preview({ join_code: code });
      setPreview(previewData);
      setJoinStep('preview');
    } catch (err: any) {
      setVerifyError(err?.message || 'Invalid joining code. Please check with your instructor.');
    } finally {
      setVerifying(false);
    }
  };

  const handleConfirmJoin = async () => {
    if (!preview) return;
    if (!consentChecked) {
      setJoinError('You must review and agree to the consent terms before joining.');
      return;
    }

    setJoining(true);
    setJoinError(null);
    try {
      await api.student.courses.join({
        join_code: inputCode.trim().toUpperCase(),
        consent_granted: true,
      });
      setIsJoinOpen(false);
      setNotification(`Successfully joined "${preview.title}" and connected learning insights!`);
      setTimeout(() => setNotification(null), 6000);
      await fetchEnrollments();
    } catch (err: any) {
      setJoinError(err?.message || 'Failed to join course. Please try again.');
    } finally {
      setJoining(false);
    }
  };

  const handleDisconnect = async () => {
    if (!disconnectingCourse) return;
    setDisconnecting(true);
    setDisconnectError(null);
    try {
      await api.student.courses.withdraw(disconnectingCourse.course_id);
      const title = disconnectingCourse.title;
      setDisconnectingCourse(null);
      setNotification(`Disconnected from "${title}". Your personal learning history remains safe.`);
      setTimeout(() => setNotification(null), 6000);
      await fetchEnrollments();
    } catch (err: any) {
      setDisconnectError(err?.message || 'Failed to disconnect from course.');
    } finally {
      setDisconnecting(false);
    }
  };

  const openAssociatedLectures = async (enr: StudentEnrollment) => {
    setActiveLecturesCourse(enr);
    setLoadingLectures(true);
    setLecturesError(null);
    try {
      const lecs = await api.student.courses.getAssociatedLectures(enr.course_id);
      setAssociatedLectures(lecs);
    } catch (err: any) {
      setLecturesError(err?.message || 'Failed to load associated lectures.');
    } finally {
      setLoadingLectures(false);
    }
  };

  return (
    <div>
      {/* Top Header */}
      <div className="section-header" style={{ marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--accent-soft)',
                color: 'var(--accent-purple)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <GraduationCap size={20} />
            </div>
            <h1 className="section-title">My Courses</h1>
          </div>
          <p className="section-subtitle">
            Connect with your instructors using course join codes to share subject-specific learning insights.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={openJoinModal}
            className="btn btn-primary btn-sm"
          >
            <Plus size={14} />
            <span>Join Course</span>
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          style={{
            padding: '12px 18px',
            marginBottom: '20px',
            borderRadius: 'var(--radius-md)',
            background: '#DCFCE7',
            color: '#16A34A',
            border: '1px solid #BBF7D0',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <CheckCircle2 size={16} />
            <span>{notification}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#16A34A',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div
          className="alert-banner alert-warning"
          style={{
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchEnrollments}
            className="btn btn-secondary btn-sm"
            style={{ padding: '4px 10px', fontSize: '12px' }}
          >
            <RefreshCw size={12} /> Retry
          </button>
        </div>
      )}

      {/* Main Content */}
      <div style={{ marginTop: '24px' }}>
        {loading ? (
          <div style={{ padding: '60px 0', textAlign: 'center' }}>
            <RefreshCw size={32} className="spin-animation" style={{ color: 'var(--accent-purple)' }} />
            <div style={{ marginTop: '16px', fontSize: '15px', color: 'var(--text-muted)' }}>
              Loading your enrolled courses...
            </div>
          </div>
        ) : enrollments.length === 0 ? (
          /* Empty State */
          <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                margin: '0 auto 16px',
                borderRadius: 'var(--radius-lg)',
                background: 'var(--accent-soft)',
                color: 'var(--accent-purple)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BookOpen size={32} />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--primary-navy)' }}>
              No courses joined yet
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '460px', margin: '8px auto 20px', lineHeight: 1.5 }}>
              If your teacher gave you a joining code (e.g.{' '}
              <code style={{ padding: '2px 6px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-subtle)', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
                MIND-XXXXXX
              </code>
              ), join their course to share learning insights while keeping unrelated study private.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={openJoinModal}
                className="btn btn-primary btn-sm"
              >
                <Plus size={14} />
                <span>Join Your First Course</span>
              </button>
            </div>
          </div>
        ) : (
          /* Courses Grid */
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            {enrollments.map((enr) => {
              const isActive = enr.status === 'active' && enr.consent_granted;
              return (
                <div
                  key={enr.id}
                  className="card card-hover"
                  style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                >
                  <div>
                    {/* Header: Title + Status */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', marginBottom: '12px' }}>
                      <div>
                        <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)', lineHeight: 1.3 }}>
                          {enr.title}
                        </h3>
                        {enr.course_code ? (
                          <span
                            style={{
                              display: 'inline-block',
                              marginTop: '6px',
                              padding: '2px 8px',
                              fontSize: '11px',
                              fontWeight: 700,
                              borderRadius: 'var(--radius-full)',
                              background: 'var(--accent-soft)',
                              color: 'var(--accent-purple)',
                              fontFamily: 'JetBrains Mono, monospace',
                            }}
                          >
                            {enr.course_code}
                          </span>
                        ) : (
                          <span
                            style={{
                              display: 'inline-block',
                              marginTop: '6px',
                              padding: '2px 8px',
                              fontSize: '11px',
                              fontWeight: 600,
                              borderRadius: 'var(--radius-full)',
                              background: 'var(--bg-subtle)',
                              color: 'var(--text-muted)',
                            }}
                          >
                            Independent
                          </span>
                        )}
                      </div>

                      {isActive ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 10px',
                            borderRadius: 'var(--radius-full)',
                            fontSize: '11px',
                            fontWeight: 700,
                            background: '#DCFCE7',
                            color: '#16A34A',
                            border: '1px solid #BBF7D0',
                            flexShrink: 0,
                          }}
                        >
                          <span
                            style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              background: '#16A34A',
                            }}
                          />
                          Active
                        </span>
                      ) : (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 10px',
                            borderRadius: 'var(--radius-full)',
                            fontSize: '11px',
                            fontWeight: 600,
                            background: 'var(--bg-subtle)',
                            color: 'var(--text-muted)',
                            border: '1px solid var(--border-subtle)',
                            flexShrink: 0,
                          }}
                        >
                          Disconnected
                        </span>
                      )}
                    </div>

                    {/* Instructor Info */}
                    <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
                      <UserCheck size={16} color="var(--accent-purple)" />
                      <span>
                        Instructor: <strong style={{ color: 'var(--primary-navy)' }}>{enr.teacher_name}</strong>
                      </span>
                    </div>

                    {/* Course Description */}
                    {enr.description && (
                      <p style={{ marginTop: '10px', fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        {enr.description}
                      </p>
                    )}

                    {/* Privacy & Association Metrics Box */}
                    <div
                      style={{
                        marginTop: '18px',
                        padding: '14px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--bg-subtle)',
                        border: '1px solid var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
                        <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Layers size={14} color="var(--text-light)" />
                          Associated Lectures
                        </span>
                        <span style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>
                          {enr.associated_lectures_count}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
                        <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <ShieldCheck size={14} color="#16A34A" />
                          Insights Sharing
                        </span>
                        <span style={{ fontWeight: 600, color: isActive ? '#16A34A' : 'var(--text-muted)' }}>
                          {isActive ? 'Aggregated Only' : 'Disabled'}
                        </span>
                      </div>

                      {enr.consent_at && (
                        <div
                          style={{
                            paddingTop: '6px',
                            borderTop: '1px solid var(--border-subtle)',
                            fontSize: '11px',
                            color: 'var(--text-light)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <Calendar size={12} />
                          <span>Connected {new Date(enr.consent_at).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Actions */}
                  <div
                    style={{
                      marginTop: '20px',
                      paddingTop: '14px',
                      borderTop: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                    }}
                  >
                    {isActive ? (
                      <>
                        <button
                          onClick={() => openAssociatedLectures(enr)}
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '12px', padding: '6px 12px' }}
                        >
                          <FileText size={14} />
                          <span>View Shared ({enr.associated_lectures_count})</span>
                        </button>
                        <button
                          onClick={() => {
                            setDisconnectError(null);
                            setDisconnectingCourse(enr);
                          }}
                          className="btn btn-sm"
                          style={{
                            fontSize: '12px',
                            padding: '6px 10px',
                            background: '#FEE2E2',
                            color: '#DC2626',
                            borderColor: '#FECACA',
                          }}
                          title="Disconnect from course and revoke consent"
                        >
                          <LogOut size={14} />
                          <span>Disconnect</span>
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => {
                          setInputCode('');
                          setPreview(null);
                          setVerifyError(null);
                          setConsentChecked(false);
                          setJoinStep('input');
                          setIsJoinOpen(true);
                        }}
                        className="btn btn-primary btn-sm"
                        style={{ width: '100%' }}
                      >
                        <span>Re-join Course</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Join Course Modal */}
      {isJoinOpen && (
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
          onClick={() => !verifying && !joining && setIsJoinOpen(false)}
        >
          <div
            className="card"
            style={{ maxWidth: '520px', width: '100%', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-soft)',
                    color: 'var(--accent-purple)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <KeyRound size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                    {joinStep === 'input' ? 'Join a Course' : 'Confirm Course & Consent'}
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {joinStep === 'input'
                      ? 'Enter the 6-character code given by your instructor'
                      : 'Review course details and privacy terms before joining'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsJoinOpen(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div>
              {joinStep === 'input' ? (
                /* Step 1: Input Code */
                <form onSubmit={handleVerifyCode}>
                  <div style={{ marginBottom: '16px' }}>
                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                      Course Joining Code <span style={{ color: '#DC2626' }}>*</span>
                    </label>
                    <input
                      type="text"
                      value={inputCode}
                      onChange={(e) => {
                        setInputCode(e.target.value.toUpperCase());
                        setVerifyError(null);
                      }}
                      placeholder="e.g. MIND-P8Q3PU"
                      style={{
                        width: '100%',
                        padding: '12px 14px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-strong)',
                        fontSize: '18px',
                        fontFamily: 'JetBrains Mono, monospace',
                        textTransform: 'uppercase',
                        letterSpacing: '2px',
                        textAlign: 'center',
                        outline: 'none',
                        boxSizing: 'border-box',
                      }}
                      autoFocus
                      required
                    />
                    <p style={{ marginTop: '6px', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
                      Case-insensitive. Dashes are optional.
                    </p>
                  </div>

                  {verifyError && (
                    <div style={{ padding: '10px 14px', background: '#FEE2E2', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '13px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <AlertCircle size={16} style={{ flexShrink: 0 }} />
                      <span>{verifyError}</span>
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                    <button
                      type="button"
                      onClick={() => setIsJoinOpen(false)}
                      className="btn btn-secondary btn-sm"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={verifying || !inputCode.trim()}
                      className="btn btn-primary btn-sm"
                    >
                      {verifying ? (
                        <>
                          <RefreshCw size={14} className="spin-animation" /> Verifying...
                        </>
                      ) : (
                        <>
                          <span>Verify Code</span>
                          <ArrowRight size={14} />
                        </>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                /* Step 2: Preview & Explicit Consent */
                <div>
                  {/* Course Details Card */}
                  <div
                    style={{
                      padding: '14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-subtle)',
                      border: '1px solid var(--border-subtle)',
                      marginBottom: '14px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-purple)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Course Found
                      </span>
                      {preview?.course_code && (
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: 'var(--radius-full)',
                            background: 'var(--accent-soft)',
                            color: 'var(--accent-purple)',
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: '11px',
                            fontWeight: 700,
                          }}
                        >
                          {preview.course_code}
                        </span>
                      )}
                    </div>
                    <h4 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                      {preview?.title}
                    </h4>
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                      <UserCheck size={14} color="var(--text-light)" />
                      Instructor: <strong style={{ color: 'var(--primary-navy)' }}>{preview?.teacher_name}</strong>
                    </p>
                    {preview?.description && (
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px', lineHeight: 1.4 }}>
                        {preview.description}
                      </p>
                    )}
                  </div>

                  {preview?.already_enrolled && (
                    <div style={{ padding: '10px 14px', background: '#FEF3C7', color: '#D97706', borderRadius: 'var(--radius-sm)', fontSize: '12px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <AlertCircle size={16} style={{ flexShrink: 0 }} />
                      <span>You are already actively enrolled in this course.</span>
                    </div>
                  )}

                  {/* One-Time Privacy & Consent Disclosure */}
                  <div
                    style={{
                      padding: '14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--accent-soft)',
                      border: '1px solid #C7D2FE',
                      marginBottom: '14px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-purple)', fontWeight: 700, fontSize: '12px', marginBottom: '8px' }}>
                      <ShieldCheck size={16} />
                      <span>Privacy & Data Sharing Disclosure</span>
                    </div>
                    <ul style={{ fontSize: '12px', color: 'var(--text-main)', paddingLeft: '20px', lineHeight: 1.5, margin: 0 }}>
                      <li style={{ marginBottom: '4px' }}>
                        <strong>Explicit association only:</strong> Only lectures you explicitly assign to{' '}
                        <strong style={{ color: 'var(--accent-purple)' }}>{preview?.title}</strong> during upload will share insights with this instructor.
                      </li>
                      <li style={{ marginBottom: '4px' }}>
                        <strong>Aggregated insights:</strong> Your teacher sees class-level concept confusion and struggling patterns, not your private notes.
                      </li>
                      <li style={{ marginBottom: '4px' }}>
                        <strong>Strict subject isolation:</strong> Your other lectures and independent study remain 100% private.
                      </li>
                      <li>
                        <strong>You stay in control:</strong> You can disconnect and revoke consent at any time from My Courses.
                      </li>
                    </ul>
                  </div>

                  {/* Explicit Consent Checkbox */}
                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px',
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-surface)',
                      cursor: 'pointer',
                      marginBottom: '14px',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={consentChecked}
                      onChange={(e) => {
                        setConsentChecked(e.target.checked);
                        setJoinError(null);
                      }}
                      style={{ marginTop: '2px', cursor: 'pointer' }}
                    />
                    <span style={{ fontSize: '12px', color: 'var(--text-main)', lineHeight: 1.4 }}>
                      I understand and explicitly agree to join this course and share relevant learning insights with my instructor.
                    </span>
                  </label>

                  {joinError && (
                    <div style={{ padding: '10px 14px', background: '#FEE2E2', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '12px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <AlertCircle size={16} style={{ flexShrink: 0 }} />
                      <span>{joinError}</span>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', marginTop: '16px' }}>
                    <button
                      type="button"
                      onClick={() => setJoinStep('input')}
                      className="btn btn-secondary btn-sm"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleConfirmJoin}
                      disabled={joining || !consentChecked || preview?.already_enrolled}
                      className="btn btn-primary btn-sm"
                    >
                      {joining ? (
                        <>
                          <RefreshCw size={14} className="spin-animation" /> Joining...
                        </>
                      ) : (
                        'Confirm & Join Course'
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Disconnect Confirmation Modal */}
      {disconnectingCourse && (
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
          onClick={() => !disconnecting && setDisconnectingCourse(null)}
        >
          <div
            className="card"
            style={{ maxWidth: '440px', width: '100%', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  background: '#FEE2E2',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#DC2626',
                }}
              >
                <ShieldAlert size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                  Disconnect from Course?
                </h3>
              </div>
            </div>

            <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.5, marginBottom: '14px' }}>
              Are you sure you want to disconnect from{' '}
              <strong style={{ color: 'var(--primary-navy)' }}>"{disconnectingCourse.title}"</strong>?
            </p>

            <div
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                fontSize: '12px',
                color: 'var(--text-muted)',
                marginBottom: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--primary-navy)', marginBottom: '6px' }}>
                <Info size={14} color="var(--accent-purple)" />
                <span>What happens when you disconnect:</span>
              </div>
              <ul style={{ paddingLeft: '18px', margin: 0, lineHeight: 1.5 }}>
                <li>Teacher access to your learning insights for this course stops immediately.</li>
                <li>Your personal learning history, lectures, and misconceptions are <strong>NOT deleted</strong> and remain in your account.</li>
                <li>You can reconnect anytime if you wish.</li>
              </ul>
            </div>

            {disconnectError && (
              <div style={{ padding: '8px 12px', background: '#FEE2E2', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '13px', marginBottom: '14px' }}>
                {disconnectError}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setDisconnectingCourse(null)}
                disabled={disconnecting}
                className="btn btn-secondary btn-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={disconnecting}
                className="btn btn-sm"
                style={{ background: '#DC2626', color: '#FFFFFF', borderColor: '#DC2626' }}
              >
                {disconnecting ? (
                  <>
                    <RefreshCw size={14} className="spin-animation" /> Disconnecting...
                  </>
                ) : (
                  'Disconnect & Revoke'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Associated Lectures Transparency Modal */}
      {activeLecturesCourse && (
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
          onClick={() => setActiveLecturesCourse(null)}
        >
          <div
            className="card"
            style={{ maxWidth: '540px', width: '100%', padding: '24px', display: 'flex', flexDirection: 'column', maxHeight: '85vh' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-soft)',
                    color: 'var(--accent-purple)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <FileText size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                    Associated Lectures
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Lectures linked to {activeLecturesCourse.title} ({activeLecturesCourse.course_code || 'No Code'})
                  </p>
                </div>
              </div>
              <button
                onClick={() => setActiveLecturesCourse(null)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ overflowY: 'auto', flex: 1, paddingRight: '4px', marginBottom: '16px' }}>
              {loadingLectures ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px 0', color: 'var(--text-muted)' }}>
                  <RefreshCw size={24} className="spin-animation" style={{ color: 'var(--accent-purple)', marginRight: '8px' }} />
                  <span style={{ fontSize: '13px' }}>Loading associated lectures...</span>
                </div>
              ) : lecturesError ? (
                <div style={{ padding: '10px 14px', background: '#FEE2E2', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '13px' }}>
                  {lecturesError}
                </div>
              ) : associatedLectures.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>
                  <BookOpen size={32} style={{ color: 'var(--text-light)', marginBottom: '8px' }} />
                  <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--primary-navy)' }}>No lectures associated yet</p>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', maxWidth: '360px', margin: '4px auto 0' }}>
                    When you upload a lecture and select{' '}
                    <strong style={{ color: 'var(--accent-purple)' }}>{activeLecturesCourse.title}</strong>, its insights will connect to this course.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    These lectures match the course code and share aggregated learning insights with {activeLecturesCourse.teacher_name}:
                  </p>
                  {associatedLectures.map((lec) => (
                    <div
                      key={lec.id}
                      style={{
                        padding: '12px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)',
                        background: 'var(--bg-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <FileText size={18} color="var(--accent-purple)" style={{ flexShrink: 0 }} />
                        <div>
                          <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--primary-navy)' }}>
                            {lec.title}
                          </p>
                          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Course Code:{' '}
                            <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-purple)', fontWeight: 600 }}>
                              {lec.course_code}
                            </span>
                          </p>
                          {lec.prerequisite_lecture_title && (
                            <p style={{ fontSize: '11px', color: 'var(--accent-purple)', fontWeight: 500, marginTop: '2px' }}>
                              Builds on: {lec.prerequisite_lecture_title}
                            </p>
                          )}
                        </div>
                      </div>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          color: '#16A34A',
                          background: '#DCFCE7',
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-full)',
                        }}
                      >
                        Shared
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                type="button"
                onClick={() => setActiveLecturesCourse(null)}
                className="btn btn-secondary btn-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
