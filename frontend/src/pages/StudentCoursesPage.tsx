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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400">
              <GraduationCap className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              My Courses
            </h1>
          </div>
          <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-400">
            Connect with your instructors using course join codes to share subject-specific learning insights.
          </p>
        </div>

        <button
          onClick={openJoinModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900"
        >
          <Plus className="w-4 h-4" />
          Join Course
        </button>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div className="mt-6 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 flex items-center justify-between text-emerald-800 dark:text-emerald-300 text-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>{notification}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="p-1 text-emerald-600 hover:text-emerald-800 dark:text-emerald-400 dark:hover:text-emerald-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mt-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 flex items-center justify-between text-rose-800 dark:text-rose-300 text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchEnrollments}
            className="inline-flex items-center gap-1.5 px-3 py-1 bg-white dark:bg-rose-900/50 rounded-md border border-rose-200 dark:border-rose-700 hover:bg-rose-50 text-xs font-medium"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      )}

      {/* Main Content */}
      <div className="mt-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500 dark:text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
            <p className="text-sm">Loading your enrolled courses...</p>
          </div>
        ) : enrollments.length === 0 ? (
          /* Empty State */
          <div className="rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-800 p-12 text-center bg-slate-50/50 dark:bg-slate-900/20">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <BookOpen className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
              No courses joined yet
            </h3>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              If your teacher gave you a joining code (e.g. <code className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-xs">MIND-XXXXXX</code>), join their course to share learning insights while keeping unrelated study private.
            </p>
            <button
              onClick={openJoinModal}
              className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Join Your First Course
            </button>
          </div>
        ) : (
          /* Courses Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {enrollments.map((enr) => {
              const isActive = enr.status === 'active' && enr.consent_granted;
              return (
                <div
                  key={enr.id}
                  className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between overflow-hidden"
                >
                  <div className="p-6">
                    {/* Header: Title + Status */}
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-snug">
                          {enr.title}
                        </h3>
                        {enr.course_code ? (
                          <span className="mt-1.5 inline-block px-2.5 py-0.5 text-xs font-semibold rounded-md bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/60 font-mono">
                            {enr.course_code}
                          </span>
                        ) : (
                          <span className="mt-1.5 inline-block px-2.5 py-0.5 text-xs font-medium rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            Independent
                          </span>
                        )}
                      </div>

                      {isActive ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 shrink-0">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 shrink-0">
                          Disconnected
                        </span>
                      )}
                    </div>

                    {/* Instructor Info */}
                    <div className="mt-4 flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                      <UserCheck className="w-4 h-4 text-indigo-500" />
                      <span>Instructor: <strong className="text-slate-800 dark:text-slate-200">{enr.teacher_name}</strong></span>
                    </div>

                    {/* Course Description */}
                    {enr.description && (
                      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                        {enr.description}
                      </p>
                    )}

                    {/* Privacy & Association Metrics */}
                    <div className="mt-5 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-slate-400" />
                          Associated Lectures
                        </span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {enr.associated_lectures_count}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                          Insights Sharing
                        </span>
                        <span className={`font-medium ${isActive ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}`}>
                          {isActive ? 'Aggregated Only' : 'Disabled'}
                        </span>
                      </div>

                      {enr.consent_at && (
                        <div className="pt-1 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-400 flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          <span>Connected {new Date(enr.consent_at).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Actions */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-900/80 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
                    {isActive ? (
                      <>
                        <button
                          onClick={() => openAssociatedLectures(enr)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 rounded-lg transition-colors"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          View Shared ({enr.associated_lectures_count})
                        </button>
                        <button
                          onClick={() => {
                            setDisconnectError(null);
                            setDisconnectingCourse(enr);
                          }}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-rose-600 dark:text-rose-400 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition-colors"
                          title="Disconnect from course and revoke consent"
                        >
                          <LogOut className="w-3.5 h-3.5" />
                          Disconnect
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
                        className="w-full py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 text-center"
                      >
                        Re-join Course
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    {joinStep === 'input' ? 'Join a Course' : 'Confirm Course & Consent'}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {joinStep === 'input'
                      ? 'Enter the 6-character code given by your instructor'
                      : 'Review course details and privacy terms before joining'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsJoinOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5">
              {joinStep === 'input' ? (
                /* Step 1: Input Code */
                <form onSubmit={handleVerifyCode} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      Course Joining Code <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={inputCode}
                      onChange={(e) => {
                        setInputCode(e.target.value.toUpperCase());
                        setVerifyError(null);
                      }}
                      placeholder="e.g. MIND-P8Q3PU"
                      className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono uppercase tracking-wider text-center text-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      autoFocus
                      required
                    />
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 text-center">
                      Case-insensitive. Dashes are optional.
                    </p>
                  </div>

                  {verifyError && (
                    <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 flex items-center gap-2.5 text-rose-700 dark:text-rose-300 text-xs">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
                      <span>{verifyError}</span>
                    </div>
                  )}

                  <div className="pt-2 flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setIsJoinOpen(false)}
                      className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={verifying || !inputCode.trim()}
                      className="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-sm"
                    >
                      {verifying ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" /> Verifying...
                        </>
                      ) : (
                        <>
                          Verify Code <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                /* Step 2: Preview & Explicit Consent */
                <div className="space-y-4">
                  {/* Course Details Card */}
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                        Course Found
                      </span>
                      {preview?.course_code && (
                        <span className="px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-mono text-xs font-semibold">
                          {preview.course_code}
                        </span>
                      )}
                    </div>
                    <h4 className="text-lg font-bold text-slate-900 dark:text-white">
                      {preview?.title}
                    </h4>
                    <p className="text-xs text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                      <UserCheck className="w-4 h-4 text-slate-400" />
                      Instructor: <strong className="text-slate-800 dark:text-slate-200">{preview?.teacher_name}</strong>
                    </p>
                    {preview?.description && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 pt-1">
                        {preview.description}
                      </p>
                    )}
                  </div>

                  {preview?.already_enrolled && (
                    <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 flex items-center gap-2 text-amber-800 dark:text-amber-300 text-xs">
                      <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
                      <span>You are already actively enrolled in this course.</span>
                    </div>
                  )}

                  {/* One-Time Privacy & Consent Disclosure */}
                  <div className="p-4 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/50 space-y-2.5">
                    <div className="flex items-center gap-2 text-indigo-900 dark:text-indigo-200 font-semibold text-xs">
                      <ShieldCheck className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
                      <span>Privacy & Data Sharing Disclosure</span>
                    </div>
                    <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-1.5 list-disc pl-5">
                      <li>
                        <strong>Explicit association only:</strong> Only lectures you explicitly assign to{' '}
                        <strong className="text-indigo-700 dark:text-indigo-300">
                          {preview?.title}
                        </strong>{' '}
                        during upload will share insights with this instructor.
                      </li>
                      <li>
                        <strong>Aggregated insights:</strong> Your teacher sees class-level concept confusion and struggling patterns, not your private notes.
                      </li>
                      <li>
                        <strong>Strict subject isolation:</strong> Your other lectures and independent study remain 100% private.
                      </li>
                      <li>
                        <strong>You stay in control:</strong> You can disconnect and revoke consent at any time from My Courses.
                      </li>
                    </ul>
                  </div>

                  {/* Explicit Consent Checkbox */}
                  <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={consentChecked}
                      onChange={(e) => {
                        setConsentChecked(e.target.checked);
                        setJoinError(null);
                      }}
                      className="mt-0.5 w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                      I understand and explicitly agree to join this course and share relevant learning insights with my instructor.
                    </span>
                  </label>

                  {joinError && (
                    <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 flex items-center gap-2 text-rose-700 dark:text-rose-300 text-xs">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
                      <span>{joinError}</span>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="pt-2 flex justify-between gap-3">
                    <button
                      type="button"
                      onClick={() => setJoinStep('input')}
                      className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleConfirmJoin}
                      disabled={joining || !consentChecked || preview?.already_enrolled}
                      className="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-sm"
                    >
                      {joining ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" /> Joining...
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 flex items-center justify-center mb-4">
                <ShieldAlert className="w-6 h-6" />
              </div>

              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Disconnect from Course?
              </h3>

              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                Are you sure you want to disconnect from{' '}
                <strong className="text-slate-900 dark:text-white">"{disconnectingCourse.title}"</strong>?
              </p>

              <div className="mt-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60 text-xs text-slate-600 dark:text-slate-400 space-y-1.5">
                <div className="flex items-center gap-2 font-medium text-slate-800 dark:text-slate-200">
                  <Info className="w-4 h-4 text-indigo-500" />
                  <span>What happens when you disconnect:</span>
                </div>
                <ul className="list-disc pl-5 space-y-1">
                  <li>Teacher access to your learning insights for this course stops immediately.</li>
                  <li>Your personal learning history, lectures, and misconceptions are <strong>NOT deleted</strong> and remain in your account.</li>
                  <li>You can reconnect anytime if you wish.</li>
                </ul>
              </div>

              {disconnectError && (
                <div className="mt-4 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 text-rose-700 dark:text-rose-300 text-xs">
                  {disconnectError}
                </div>
              )}

              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setDisconnectingCourse(null)}
                  disabled={disconnecting}
                  className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 rounded-lg shadow-sm"
                >
                  {disconnecting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Disconnecting...
                    </>
                  ) : (
                    'Disconnect & Revoke'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Associated Lectures Transparency Modal */}
      {activeLecturesCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col">
            <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    Associated Lectures
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Lectures linked to {activeLecturesCourse.title} ({activeLecturesCourse.course_code || 'No Code'})
                  </p>
                </div>
              </div>
              <button
                onClick={() => setActiveLecturesCourse(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 max-h-96 overflow-y-auto">
              {loadingLectures ? (
                <div className="flex items-center justify-center py-8 text-slate-400">
                  <RefreshCw className="w-6 h-6 animate-spin text-indigo-500 mr-2" />
                  <span className="text-xs">Loading associated lectures...</span>
                </div>
              ) : lecturesError ? (
                <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 text-rose-700 text-xs">
                  {lecturesError}
                </div>
              ) : associatedLectures.length === 0 ? (
                <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                  <BookOpen className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                  <p className="text-sm font-medium">No lectures associated yet</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                    When you upload a lecture and select{' '}
                    <strong className="text-indigo-600 font-medium">{activeLecturesCourse.title}</strong>,
                    its insights will connect to this course.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  <p className="text-xs text-slate-500 mb-2">
                    These lectures match the course code and share aggregated learning insights with {activeLecturesCourse.teacher_name}:
                  </p>
                  {associatedLectures.map((lec) => (
                    <div
                      key={lec.id}
                      className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-indigo-500 shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-slate-900 dark:text-white">
                            {lec.title}
                          </p>
                          <p className="text-[11px] text-slate-400">
                            Course Code: <span className="font-mono text-indigo-600 dark:text-indigo-400">{lec.course_code}</span>
                          </p>
                        </div>
                      </div>
                      <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                        Shared
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="p-4 bg-slate-50 dark:bg-slate-900/80 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setActiveLecturesCourse(null)}
                className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
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
