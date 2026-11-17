import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { Course } from '../types';
import {
  School,
  Plus,
  BookOpen,
  KeyRound,
  CheckCircle2,
  Copy,
  Check,
  Edit3,
  Trash2,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  X,
  Calendar,
  Layers,
  Sparkles,
  Info
} from 'lucide-react';

export const TeacherDashboardPage: React.FC = () => {
  const { user } = useAuth();

  // Courses state
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Success notification banner (e.g. after creating course)
  const [successBanner, setSuccessBanner] = useState<{ message: string; joinCode: string; courseTitle: string } | null>(null);

  // Copy-to-clipboard state
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Create Modal state
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [createTitle, setCreateTitle] = useState<string>('');
  const [createCourseCode, setCreateCourseCode] = useState<string>('');
  const [createDescription, setCreateDescription] = useState<string>('');
  const [creating, setCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Edit Modal state
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [editTitle, setEditTitle] = useState<string>('');
  const [editCourseCode, setEditCourseCode] = useState<string>('');
  const [editDescription, setEditDescription] = useState<string>('');
  const [updating, setUpdating] = useState<boolean>(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  // Delete Confirmation Modal state
  const [deletingCourse, setDeletingCourse] = useState<Course | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Course Detail Modal state
  const [detailCourse, setDetailCourse] = useState<Course | null>(null);

  // Fetch teacher's courses
  const fetchCourses = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.teacher.courses.list();
      setCourses(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load courses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  // Copy joining code to clipboard
  const handleCopyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2500);
    } catch {
      // Fallback
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2500);
    }
  };

  // Open Create Modal
  const openCreateModal = () => {
    setCreateTitle('');
    setCreateCourseCode('');
    setCreateDescription('');
    setCreateError(null);
    setIsCreateOpen(true);
  };

  // Submit Create Course
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanTitle = createTitle.trim();
    if (!cleanTitle) {
      setCreateError('Course title is required.');
      return;
    }

    setCreating(true);
    setCreateError(null);
    try {
      const newCourse = await api.teacher.courses.create({
        title: cleanTitle,
        course_code: createCourseCode.trim() || undefined,
        description: createDescription.trim() || undefined,
      });
      setIsCreateOpen(false);
      setSuccessBanner({
        message: 'Course created successfully! Share this joining code with your students.',
        joinCode: newCourse.join_code,
        courseTitle: newCourse.title,
      });
      await fetchCourses();
    } catch (err: any) {
      setCreateError(err.message || 'Could not create course. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  // Open Edit Modal
  const openEditModal = (course: Course) => {
    setEditingCourse(course);
    setEditTitle(course.title);
    setEditCourseCode(course.course_code || '');
    setEditDescription(course.description || '');
    setUpdateError(null);
  };

  // Submit Edit Course
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCourse) return;
    const cleanTitle = editTitle.trim();
    if (!cleanTitle) {
      setUpdateError('Course title is required.');
      return;
    }

    setUpdating(true);
    setUpdateError(null);
    try {
      await api.teacher.courses.update(editingCourse.id, {
        title: cleanTitle,
        course_code: editCourseCode.trim() || undefined,
        description: editDescription.trim() || undefined,
      });
      setEditingCourse(null);
      await fetchCourses();
    } catch (err: any) {
      setUpdateError(err.message || 'Failed to update course.');
    } finally {
      setUpdating(false);
    }
  };

  // Submit Delete Course
  const handleDeleteSubmit = async () => {
    if (!deletingCourse) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.teacher.courses.delete(deletingCourse.id);
      setDeletingCourse(null);
      if (detailCourse?.id === deletingCourse.id) {
        setDetailCourse(null);
      }
      await fetchCourses();
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to delete course.');
    } finally {
      setDeleting(false);
    }
  };

  // Format date helper
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* ── Page Header ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '11px',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '9999px',
                background: 'rgba(79, 70, 229, 0.12)',
                color: '#4f46e5',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}
            >
              <School size={13} />
              Teacher Workspace
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              • Courses & Learning Insights
            </span>
          </div>
          <h1 className="section-title" style={{ fontSize: '26px', fontWeight: 800, margin: '0 0 6px' }}>
            Teacher Workspace
          </h1>
          <p className="section-subtitle" style={{ fontSize: '14px', color: 'var(--text-muted)', margin: 0 }}>
            Manage your courses and access course-specific learning insights in future phases.
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            id="btn-refresh-courses"
            className="btn btn-secondary btn-sm"
            onClick={fetchCourses}
            disabled={loading}
            title="Refresh courses"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'spin-animation' : ''} />
            <span>Refresh</span>
          </button>
          <button
            id="btn-create-course"
            className="btn btn-primary btn-sm"
            onClick={openCreateModal}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={16} />
            <span>Create Course</span>
          </button>
        </div>
      </div>

      {/* ── Success Banner After Course Creation ── */}
      {successBanner && (
        <div
          className="card"
          style={{
            background: 'linear-gradient(135deg, rgba(22, 163, 74, 0.08) 0%, rgba(79, 70, 229, 0.05) 100%)',
            border: '1px solid rgba(22, 163, 74, 0.25)',
            borderRadius: 'var(--radius-md)',
            padding: '16px 20px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: 'rgba(22, 163, 74, 0.15)',
                color: '#16a34a',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <CheckCircle2 size={20} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy-900)' }}>
                {successBanner.courseTitle} created successfully!
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Share this unique joining code with your students so they can join this course in Phase 3.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: '#FFFFFF',
                padding: '6px 14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <KeyRound size={14} color="#4f46e5" />
              <code style={{ fontSize: '15px', fontWeight: 800, color: '#4f46e5', letterSpacing: '0.05em' }}>
                {successBanner.joinCode}
              </code>
              <button
                id="btn-copy-success-code"
                onClick={() => handleCopyCode(successBanner.joinCode)}
                className="btn btn-secondary btn-sm"
                style={{ padding: '3px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                title="Copy code"
              >
                {copiedCode === successBanner.joinCode ? (
                  <>
                    <Check size={12} color="#16a34a" />
                    <span style={{ color: '#16a34a' }}>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <button
              onClick={() => setSuccessBanner(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              title="Dismiss"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ── Main Error Alert ── */}
      {error && (
        <div
          className="alert-banner alert-warning"
          style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchCourses}>
            Retry
          </button>
        </div>
      )}

      {/* ── Loading Skeleton ── */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <RefreshCw size={28} className="spin-animation" style={{ color: '#4f46e5' }} />
          <div style={{ marginTop: '12px', color: 'var(--text-muted)', fontSize: '14px' }}>
            Loading your courses...
          </div>
        </div>
      ) : courses.length === 0 ? (
        /* ── Empty State ── */
        <div
          className="card"
          style={{
            textAlign: 'center',
            padding: '56px 24px',
            border: '2px dashed var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            background: 'var(--bg-card)',
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: 'rgba(79, 70, 229, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#4f46e5',
              margin: '0 auto 16px',
            }}
          >
            <BookOpen size={28} />
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy-900)', margin: '0 0 8px' }}>
            No courses created yet
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '460px', margin: '0 auto 20px', lineHeight: 1.6 }}>
            Create your first course to generate an automatic, secure joining code that students can use to connect with your course.
          </p>
          <button
            id="btn-empty-create-course"
            className="btn btn-primary"
            onClick={openCreateModal}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={16} />
            <span>Create Your First Course</span>
          </button>
        </div>
      ) : (
        /* ── Courses Grid ── */
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Your Active Courses ({courses.length})
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
              gap: '18px',
            }}
          >
            {courses.map((course) => (
              <div
                key={course.id}
                className="card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border-subtle)',
                  padding: '20px',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                }}
              >
                <div>
                  {/* Card Header: Code Badge & Actions */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                      {course.course_code ? (
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: 'var(--accent-soft)',
                            color: 'var(--primary-accent)',
                            letterSpacing: '0.04em',
                            textTransform: 'uppercase',
                          }}
                        >
                          {course.course_code}
                        </span>
                      ) : (
                        <span
                          style={{
                            fontSize: '11px',
                            color: 'var(--text-muted)',
                            padding: '2px 6px',
                            background: 'var(--bg-subtle)',
                            borderRadius: '4px',
                          }}
                        >
                          No code set
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '4px 8px' }}
                        onClick={() => openEditModal(course)}
                        title="Edit course details"
                      >
                        <Edit3 size={13} />
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '4px 8px', color: '#dc2626' }}
                        onClick={() => {
                          setDeletingCourse(course);
                          setDeleteError(null);
                        }}
                        title="Delete course"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {/* Course Title */}
                  <h3
                    style={{
                      fontSize: '17px',
                      fontWeight: 800,
                      color: 'var(--navy-900)',
                      margin: '0 0 8px',
                      cursor: 'pointer',
                    }}
                    onClick={() => setDetailCourse(course)}
                  >
                    {course.title}
                  </h3>

                  {/* Description */}
                  <p
                    style={{
                      fontSize: '13px',
                      color: 'var(--text-muted)',
                      margin: '0 0 16px',
                      lineHeight: 1.5,
                      minHeight: '38px',
                    }}
                  >
                    {course.description
                      ? course.description.length > 120
                        ? `${course.description.slice(0, 120)}…`
                        : course.description
                      : 'No description provided.'}
                  </p>
                </div>

                {/* Card Footer: Joining Code & Details link */}
                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '14px', marginTop: '4px' }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: 'var(--bg-subtle)',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-md)',
                      marginBottom: '10px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <KeyRound size={13} color="#4f46e5" />
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Join Code:</span>
                      <code style={{ fontSize: '13px', fontWeight: 800, color: '#4f46e5' }}>
                        {course.join_code}
                      </code>
                    </div>

                    <button
                      onClick={() => handleCopyCode(course.join_code)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '2px 4px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '3px',
                        fontSize: '11px',
                        color: copiedCode === course.join_code ? '#16a34a' : 'var(--text-muted)',
                        fontWeight: 600,
                      }}
                      title="Copy joining code"
                    >
                      {copiedCode === course.join_code ? (
                        <>
                          <Check size={12} color="#16a34a" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={12} />
                      <span>{formatDate(course.created_at)}</span>
                    </div>

                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '3px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      onClick={() => setDetailCourse(course)}
                    >
                      <span>View Details</span>
                      <ExternalLink size={12} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Architecture Preview Notice ── */}
      <div
        className="card"
        style={{
          marginTop: '36px',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          padding: '22px 24px',
          background: 'var(--bg-card)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <Sparkles size={18} color="#4f46e5" />
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy-900)', margin: 0 }}>
            Teacher Insights Roadmap
          </h3>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>
          <strong>Phase 2 Active:</strong> You can create and manage courses with secure join codes. In <strong>Phase 3</strong>, students will enter your code and grant one-time consent to connect their learning activity. Course concept boundaries and confusion analytics will unlock in subsequent phases.
        </p>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ── CREATE COURSE MODAL ── */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {isCreateOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '500px', width: '100%' }}>
            <div className="modal-header">
              <h2 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <School size={20} color="#4f46e5" />
                <span>Create New Course</span>
              </h2>
              <button
                className="modal-close-btn"
                onClick={() => setIsCreateOpen(false)}
                disabled={creating}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div className="modal-body">
                {createError && (
                  <div className="alert-banner alert-warning" style={{ marginBottom: '16px' }}>
                    {createError}
                  </div>
                )}

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>
                    Course Title <span style={{ color: '#dc2626' }}>*</span>
                  </label>
                  <input
                    id="input-create-course-title"
                    type="text"
                    className="input-field"
                    placeholder="e.g. Database Systems, Data Structures & Algorithms"
                    value={createTitle}
                    onChange={(e) => setCreateTitle(e.target.value)}
                    disabled={creating}
                    autoFocus
                    required
                    style={{ width: '100%', padding: '10px 12px', fontSize: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>
                    Course Code <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
                  </label>
                  <input
                    id="input-create-course-code"
                    type="text"
                    className="input-field"
                    placeholder="e.g. CS301, CS101, DBS202"
                    value={createCourseCode}
                    onChange={(e) => setCreateCourseCode(e.target.value)}
                    disabled={creating}
                    style={{ width: '100%', padding: '10px 12px', fontSize: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>
                    Description <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
                  </label>
                  <textarea
                    id="textarea-create-course-desc"
                    className="input-field"
                    placeholder="Brief description of the course topic, syllabus, or target section..."
                    rows={3}
                    value={createDescription}
                    onChange={(e) => setCreateDescription(e.target.value)}
                    disabled={creating}
                    style={{ width: '100%', padding: '10px 12px', fontSize: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', resize: 'vertical' }}
                  />
                </div>

                <div
                  style={{
                    background: 'var(--bg-subtle)',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <KeyRound size={15} color="#4f46e5" style={{ flexShrink: 0 }} />
                  <span>A secure, collision-resistant joining code (e.g. <code>MIND-XXXXXX</code>) will be generated automatically upon creation.</span>
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsCreateOpen(false)}
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-create-course"
                  type="submit"
                  className="btn btn-primary"
                  disabled={creating}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  {creating && <RefreshCw size={14} className="spin-animation" />}
                  <span>{creating ? 'Creating...' : 'Create Course'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ── EDIT COURSE MODAL ── */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {editingCourse && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '500px', width: '100%' }}>
            <div className="modal-header">
              <h2 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Edit3 size={18} color="#4f46e5" />
                <span>Edit Course Details</span>
              </h2>
              <button
                className="modal-close-btn"
                onClick={() => setEditingCourse(null)}
                disabled={updating}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div className="modal-body">
                {updateError && (
                  <div className="alert-banner alert-warning" style={{ marginBottom: '16px' }}>
                    {updateError}
                  </div>
                )}

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>
                    Course Title <span style={{ color: '#dc2626' }}>*</span>
                  </label>
                  <input
                    id="input-edit-course-title"
                    type="text"
                    className="input-field"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    disabled={updating}
                    required
                    style={{ width: '100%', padding: '10px 12px', fontSize: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>
                    Course Code <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
                  </label>
                  <input
                    id="input-edit-course-code"
                    type="text"
                    className="input-field"
                    value={editCourseCode}
                    onChange={(e) => setEditCourseCode(e.target.value)}
                    disabled={updating}
                    style={{ width: '100%', padding: '10px 12px', fontSize: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>
                    Description <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
                  </label>
                  <textarea
                    id="textarea-edit-course-desc"
                    className="input-field"
                    rows={3}
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    disabled={updating}
                    style={{ width: '100%', padding: '10px 12px', fontSize: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', resize: 'vertical' }}
                  />
                </div>

                <div
                  style={{
                    background: 'var(--bg-subtle)',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <Info size={14} color="#4f46e5" />
                  <span>Join Code (<code>{editingCourse.join_code}</code>) is permanent and cannot be modified.</span>
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setEditingCourse(null)}
                  disabled={updating}
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-edit-course"
                  type="submit"
                  className="btn btn-primary"
                  disabled={updating}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  {updating && <RefreshCw size={14} className="spin-animation" />}
                  <span>{updating ? 'Saving...' : 'Save Changes'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ── COURSE DETAIL MODAL ── */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {detailCourse && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '540px', width: '100%' }}>
            <div className="modal-header">
              <h2 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BookOpen size={20} color="#4f46e5" />
                <span>Course Details</span>
              </h2>
              <button
                className="modal-close-btn"
                onClick={() => setDetailCourse(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {/* Title & Code */}
              <div style={{ marginBottom: '18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--navy-900)', margin: 0 }}>
                    {detailCourse.title}
                  </h3>
                  {detailCourse.course_code && (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: 'var(--accent-soft)',
                        color: 'var(--primary-accent)',
                      }}
                    >
                      {detailCourse.course_code}
                    </span>
                  )}
                </div>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
                  {detailCourse.description || 'No description provided for this course.'}
                </p>
              </div>

              {/* Joining Code Card */}
              <div
                style={{
                  background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.08) 0%, rgba(124, 58, 237, 0.05) 100%)',
                  border: '1px solid rgba(79, 70, 229, 0.25)',
                  borderRadius: 'var(--radius-md)',
                  padding: '18px 20px',
                  marginBottom: '18px',
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#4f46e5', letterSpacing: '0.04em', marginBottom: '6px' }}>
                  Student Course Join Code
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                  <code style={{ fontSize: '22px', fontWeight: 800, color: '#4f46e5', letterSpacing: '0.06em' }}>
                    {detailCourse.join_code}
                  </code>
                  <button
                    id="btn-copy-detail-code"
                    className="btn btn-primary btn-sm"
                    onClick={() => handleCopyCode(detailCourse.join_code)}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    {copiedCode === detailCourse.join_code ? (
                      <>
                        <Check size={14} />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={14} />
                        <span>Copy Code</span>
                      </>
                    )}
                  </button>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '8px 0 0', lineHeight: 1.4 }}>
                  Distribute this joining code to your students. In Phase 3, students will enter this code to connect with your course.
                </p>
              </div>

              {/* Meta information */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '12px',
                  background: 'var(--bg-subtle)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                }}
              >
                <div>
                  <span style={{ fontWeight: 600 }}>Created Date:</span> {formatDate(detailCourse.created_at)}
                </div>
                <div>
                  <span style={{ fontWeight: 600 }}>Last Updated:</span> {formatDate(detailCourse.updated_at)}
                </div>
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <button
                className="btn btn-secondary btn-sm"
                style={{ color: '#dc2626' }}
                onClick={() => {
                  setDeletingCourse(detailCourse);
                  setDeleteError(null);
                }}
              >
                Delete Course
              </button>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => openEditModal(detailCourse)}
                >
                  Edit Details
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setDetailCourse(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ── DELETE CONFIRMATION MODAL ── */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {deletingCourse && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '440px', width: '100%' }}>
            <div className="modal-header">
              <h2 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#dc2626' }}>
                <AlertCircle size={20} />
                <span>Delete Course?</span>
              </h2>
              <button
                className="modal-close-btn"
                onClick={() => setDeletingCourse(null)}
                disabled={deleting}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {deleteError && (
                <div className="alert-banner alert-warning" style={{ marginBottom: '14px' }}>
                  {deleteError}
                </div>
              )}
              <p style={{ fontSize: '14px', color: 'var(--navy-800)', margin: '0 0 12px', lineHeight: 1.5 }}>
                Are you sure you want to delete <strong>{deletingCourse.title}</strong>?
              </p>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
                Its joining code (<code>{deletingCourse.join_code}</code>) will be permanently deactivated. Unrelated student records and lecture data will not be affected.
              </p>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setDeletingCourse(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-delete-course"
                className="btn"
                onClick={handleDeleteSubmit}
                disabled={deleting}
                style={{
                  background: '#dc2626',
                  color: '#FFFFFF',
                  border: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {deleting && <RefreshCw size={14} className="spin-animation" />}
                <span>{deleting ? 'Deleting...' : 'Yes, Delete Course'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
