import React, { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import type { Lecture } from '../types';
import {
  UploadCloud,
  FileVideo,
  FileAudio,
  CheckCircle,
  AlertCircle,
  Loader2,
  ArrowRight,
  Info
} from 'lucide-react';

interface UploadPageProps {
  setActiveTab: (tab: string) => void;
  onLectureCreated: (lectureId: number) => void;
}

const STAGES = [
  { id: 1, title: 'Uploading recording', desc: 'Securely uploading multimedia file to MindTrace server' },
  { id: 2, title: 'Extracting audio track', desc: 'Validating sample rate and acoustic encoding' },
  { id: 3, title: 'Transcribing speech', desc: 'Processing audio and automatically detecting language' },
  { id: 4, title: 'Detecting concept boundaries', desc: 'Identifying cohesive pedagogical concept transitions' },
  { id: 5, title: 'Generating targeted checkpoints', desc: 'Creating concept assessment questions and distractors' },
  { id: 6, title: 'Preparing concept timeline', desc: 'Assembling interactive seek points and progress markers' },
  { id: 7, title: 'Ready for study', desc: 'All concepts and checkpoints initialized successfully' },
];

const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.webm', '.mp3', '.wav', '.m4a', '.ogg'];
const ALLOWED_MIME_TYPES = [
  'video/mp4', 'video/quicktime', 'video/webm', 'video/ogg',
  'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/wave',
  'audio/m4a', 'audio/mp4', 'audio/x-m4a',
  'audio/ogg', 'application/ogg', 'audio/vorbis', 'audio/opus'
];

export const UploadPage: React.FC<UploadPageProps> = ({ setActiveTab, onLectureCreated }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [courseCode, setCourseCode] = useState('CS101');
  const [existingLectures, setExistingLectures] = useState<Lecture[]>([]);
  const [prerequisiteLectureId, setPrerequisiteLectureId] = useState<string>('');
  
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [qualityWarning, setQualityWarning] = useState<string | null>(null);
  const [createdLectureId, setCreatedLectureId] = useState<number | null>(null);
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [duplicateLectureData, setDuplicateLectureData] = useState<{
    id: number;
    title: string;
    duration_seconds: number;
    concepts_count: number;
    message: string;
  } | null>(null);

  useEffect(() => {
    let isMounted = true;
    api.lectures.list().then((lecs) => {
      if (isMounted && Array.isArray(lecs)) {
        setExistingLectures(lecs);
      }
    }).catch(() => {
      // Ignore background fetch error
    });
    return () => { isMounted = false; };
  }, []);

  const handleResetUpload = () => {
    setUploading(false);
    setCurrentStage(0);
    setSelectedFile(null);
    setTitle('');
    setCourseCode('CS101');
    setPrerequisiteLectureId('');
    setQualityWarning(null);
    setIsDuplicate(false);
    setDuplicateLectureData(null);
    setError(null);
    setCreatedLectureId(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (file: File) => {
    const extMatch = file.name.match(/\.[0-9a-z]+$/i);
    const ext = extMatch ? extMatch[0].toLowerCase() : '';

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file format '${ext || file.name}'. Allowed formats: MP4, MOV, WEBM, MP3, WAV, M4A, OGG.`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    if (file.type && file.type !== 'application/octet-stream' && !ALLOWED_MIME_TYPES.includes(file.type.toLowerCase())) {
      setError(`Unsupported MIME type '${file.type}'. Allowed media types include audio/ogg, application/ogg, MP3, WAV, MP4, etc.`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    if (file.size > 250 * 1024 * 1024) {
      setError('File size exceeds the 250MB limit.');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setSelectedFile(file);
    if (!title) {
      // Suggest clean title from filename
      const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
      setTitle(baseName.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()));
    }
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a video or audio lecture file.');
      return;
    }
    if (!title.trim()) {
      setError('Please provide a lecture title.');
      return;
    }

    setUploading(true);
    setError(null);
    setCurrentStage(1);

    // Realistic stage simulation interval while backend processes
    const stageTimer = setInterval(() => {
      setCurrentStage((prev) => {
        if (prev < 6) return prev + 1;
        return prev;
      });
    }, 1800);

    try {
      const formData = new FormData();
      formData.append('title', title.trim());
      formData.append('course_code', courseCode.trim() || 'CS101');
      formData.append('description', '');
      formData.append('file', selectedFile);
      if (prerequisiteLectureId) {
        formData.append('prerequisite_lecture_id', prerequisiteLectureId);
      }

      const res = await api.lectures.upload(formData);
      setQualityWarning(res.quality_warning || null);
      clearInterval(stageTimer);
      if (res.is_duplicate) {
        setIsDuplicate(true);
        setDuplicateLectureData({
          id: res.lecture_id,
          title: res.title,
          duration_seconds: res.duration_seconds || 0,
          concepts_count: res.concepts_count || 0,
          message: res.message || 'This lecture already exists in your library.'
        });
        setCreatedLectureId(res.lecture_id);
        setCurrentStage(7);
      } else {
        setIsDuplicate(false);
        setDuplicateLectureData(null);
        setCurrentStage(7);
        setCreatedLectureId(res.lecture_id);
      }
    } catch (err: any) {
      clearInterval(stageTimer);
      setError(err.message || 'Upload and processing failed.');
      setUploading(false);
      setCurrentStage(0);
    }
  };

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', paddingBottom: '60px' }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Upload Lecture Recording</h1>
          <p className="section-subtitle">
            Upload course video or audio to automatically generate timestamped concepts and checkpoints.
          </p>
        </div>
      </div>

      {uploading ? (
        isDuplicate && duplicateLectureData ? (
          <div className="card" style={{ padding: '40px 32px', textAlign: 'center' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'var(--accent-soft)',
                color: 'var(--primary-accent)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
              }}
            >
              <Info size={32} />
            </div>

            <h2 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--primary-navy)', marginBottom: '8px' }}>
              This lecture already exists in your library.
            </h2>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '540px', margin: '0 auto 24px', lineHeight: 1.6 }}>
              MindTrace detected identical file content via cryptographic SHA-256 verification.
              No redundant records, transcriptions, or quizzes were created, and your existing study progress and MCQ answers remain preserved.
            </p>

            <div
              style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                padding: '18px 24px',
                maxWidth: '480px',
                margin: '0 auto 32px',
                textAlign: 'left',
              }}
            >
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-purple)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Existing Lecture In Library
              </div>
              <div style={{ fontSize: '17px', fontWeight: 800, color: 'var(--primary-navy)', marginTop: '4px' }}>
                {duplicateLectureData.title}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px', display: 'flex', gap: '16px' }}>
                <span>{duplicateLectureData.concepts_count} Concepts</span>
                <span>•</span>
                <span>{Math.floor(duplicateLectureData.duration_seconds / 60)}m {Math.floor(duplicateLectureData.duration_seconds % 60)}s</span>
                <span>•</span>
                <span style={{ color: '#16A34A', fontWeight: 600 }}>Ready to Study</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                id="btn-open-existing-lecture"
                className="btn btn-primary btn-lg"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 24px' }}
                onClick={() => onLectureCreated(duplicateLectureData.id)}
              >
                <span>Open Existing Lecture</span>
                <ArrowRight size={18} />
              </button>
              <button
                id="btn-upload-different-lecture"
                className="btn btn-secondary btn-lg"
                style={{ padding: '12px 24px' }}
                onClick={handleResetUpload}
              >
                <span>Upload Another Lecture</span>
              </button>
            </div>
          </div>
        ) : (
        <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
          <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--primary-navy)', marginBottom: '8px' }}>
            {currentStage === 7 ? 'Processing Complete!' : 'Processing Lecture Recording'}
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '32px' }}>
            {selectedFile?.name} ({((selectedFile?.size || 0) / (1024 * 1024)).toFixed(2)} MB)
          </p>

          {/* Stepper Display */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', textAlign: 'left', maxWidth: '580px', margin: '0 auto 36px' }}>
            {STAGES.map((st) => {
              const isDone = currentStage > st.id || (currentStage === 7 && st.id === 7);
              const isCurrent = currentStage === st.id && currentStage !== 7;
              return (
                <div
                  key={st.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    padding: '12px 18px',
                    borderRadius: 'var(--radius-md)',
                    background: isCurrent ? 'var(--accent-soft)' : isDone ? '#F0FDF4' : 'var(--bg-subtle)',
                    border: `1px solid ${isCurrent ? '#C7D2FE' : isDone ? '#BBF7D0' : 'var(--border-subtle)'}`,
                    transition: 'all 0.3s ease',
                  }}
                >
                  <div style={{ flexShrink: 0 }}>
                    {isDone ? (
                      <CheckCircle size={22} color="#16A34A" />
                    ) : isCurrent ? (
                      <Loader2 size={22} color="var(--accent-purple)" className="spin-animation" />
                    ) : (
                      <div
                        style={{
                          width: '22px',
                          height: '22px',
                          borderRadius: '50%',
                          border: '2px solid var(--border-strong)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '11px',
                          fontWeight: 700,
                          color: 'var(--text-muted)',
                        }}
                      >
                        {st.id}
                      </div>
                    )}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: isCurrent ? 'var(--accent-purple)' : isDone ? '#16A34A' : 'var(--text-muted)',
                      }}
                    >
                      {st.title}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {st.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {currentStage === 7 && qualityWarning && (
            <div
              style={{
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: '#FEF3C7',
                border: '1px solid #FDE68A',
                color: '#92400E',
                fontSize: '13px',
                fontWeight: 600,
                marginTop: '20px',
                marginBottom: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                textAlign: 'left',
              }}
            >
              <AlertCircle size={18} color="#D97706" style={{ flexShrink: 0 }} />
              <span>{qualityWarning}</span>
            </div>
          )}

          {currentStage === 7 && createdLectureId && (
            <button
              id="btn-open-processed-lecture"
              className="btn btn-accent btn-lg"
              onClick={() => onLectureCreated(createdLectureId)}
            >
              <span>Open Concept Timeline Player</span>
              <ArrowRight size={18} />
            </button>
          )}
        </div>
        )
      ) : (
        <form onSubmit={handleSubmit} className="card" style={{ padding: '36px' }}>
          {error && (
            <div className="alert-banner alert-warning">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {/* Drag & Drop Upload Zone */}
          <div
            id="dropzone-area"
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? 'var(--accent-purple)' : 'var(--border-strong)'}`,
              borderRadius: 'var(--radius-xl)',
              background: isDragging ? 'var(--accent-soft)' : 'var(--bg-subtle)',
              padding: '48px 24px',
              textAlign: 'center',
              cursor: 'pointer',
              marginBottom: '28px',
              transition: 'all 0.2s ease',
            }}
          >
            <input
              ref={fileInputRef}
              id="lecture-file-input"
              type="file"
              accept=".mp4,.mov,.webm,.mp3,.wav,.m4a,.ogg,audio/ogg,application/ogg"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileChange(e.target.files[0]);
                }
              }}
            />

            {selectedFile ? (
              <div>
                <div
                  style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    background: '#DCFCE7',
                    color: '#16A34A',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '14px',
                  }}
                >
                  {selectedFile.type.startsWith('video') && !selectedFile.name.toLowerCase().endsWith('.ogg') ? (
                    <FileVideo size={28} />
                  ) : (
                    <FileAudio size={28} />
                  )}
                </div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--primary-navy)' }}>
                  {selectedFile.name}
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze
                </div>
                <button
                  type="button"
                  style={{
                    marginTop: '12px',
                    background: 'none',
                    border: 'none',
                    color: 'var(--accent-purple)',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                >
                  Choose a different file
                </button>
              </div>
            ) : (
              <div>
                <div
                  style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    background: 'var(--accent-soft)',
                    color: 'var(--accent-purple)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '14px',
                  }}
                >
                  <UploadCloud size={28} />
                </div>
                <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--primary-navy)' }}>
                  Drag & drop your lecture file here, or browse
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px' }}>
                  Supported formats: <strong>MP4, MOV, WEBM, MP3, WAV, M4A, OGG</strong> (Max 250MB)
                </div>
              </div>
            )}
          </div>

          {/* Metadata fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div className="form-group">
              <label className="form-label">Lecture Title *</label>
              <input
                id="lecture-title-input"
                type="text"
                className="form-input"
                placeholder="e.g. Introduction to Functions"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Course Code</label>
              <input
                id="lecture-course-input"
                type="text"
                className="form-input"
                placeholder="CS101"
                value={courseCode}
                onChange={(e) => setCourseCode(e.target.value)}
              />
            </div>
          </div>

          {/* Prerequisite Lecture Field */}
          <div className="form-group" style={{ marginBottom: '28px' }}>
            <label className="form-label" htmlFor="lecture-prerequisite-select">
              Prerequisite lecture (optional)
            </label>
            <select
              id="lecture-prerequisite-select"
              className="form-input"
              value={prerequisiteLectureId}
              onChange={(e) => setPrerequisiteLectureId(e.target.value)}
              style={{
                cursor: 'pointer',
                background: 'var(--bg-card)',
                color: 'var(--primary-navy)'
              }}
            >
              <option value="">None</option>
              {existingLectures.map((lec) => (
                <option key={lec.id} value={lec.id}>
                  {lec.title} {lec.course_code ? `(${lec.course_code})` : ''}
                </option>
              ))}
            </select>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px', lineHeight: 1.4 }}>
              Choose an earlier lecture this one builds on. MindTrace will re-check your unresolved gaps from it first.
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setActiveTab('dashboard')}
            >
              Cancel
            </button>
            <button
              id="btn-submit-upload"
              type="submit"
              className="btn btn-primary"
              disabled={!selectedFile}
            >
              <UploadCloud size={16} />
              <span>Upload & Analyze Lecture</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
