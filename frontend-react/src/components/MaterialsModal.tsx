import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { X, Download, RefreshCw, Edit3, Save, FileText, Mail } from 'lucide-react';
import { api } from '../api/client';

interface MaterialsModalProps {
  isOpen: boolean;
  onClose: () => void;
  applicationId: number | null;
  jobTitle: string;
  company: string;
  jobId?: number;
  profileId?: number;
  onRegenerated?: () => void;
}

interface MaterialsData {
  application_id: number;
  resume_version_text: string;
  cover_letter_text: string;
  job_title: string;
  company: string;
}

export function MaterialsModal({
  isOpen,
  onClose,
  applicationId,
  jobTitle,
  company,
  jobId,
  profileId,
  onRegenerated,
}: MaterialsModalProps) {
  const [activeTab, setActiveTab] = useState<'resume' | 'cover_letter'>('resume');
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [materials, setMaterials] = useState<MaterialsData | null>(null);
  const [editResume, setEditResume] = useState('');
  const [editCoverLetter, setEditCoverLetter] = useState('');

  const fetchMaterials = useCallback(async () => {
    if (!applicationId) return;
    setLoading(true);
    try {
      const res = await api.applications.getMaterials(applicationId);
      setMaterials(res.data);
      setEditResume(res.data.resume_version_text);
      setEditCoverLetter(res.data.cover_letter_text);
    } catch {
      toast.error('Failed to load materials');
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    if (isOpen && applicationId) {
      fetchMaterials();
      setEditing(false);
      setActiveTab('resume');
    }
  }, [isOpen, applicationId, fetchMaterials]);

  const handleSave = async () => {
    if (!applicationId) return;
    setSaving(true);
    try {
      await api.applications.updateMaterials(applicationId, editResume, editCoverLetter);
      setMaterials((prev) =>
        prev
          ? { ...prev, resume_version_text: editResume, cover_letter_text: editCoverLetter }
          : prev
      );
      setEditing(false);
      toast.success('Changes saved');
    } catch {
      toast.error('Failed to save materials');
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerate = async () => {
    if (!jobId || !profileId) {
      toast.error('Job ID and Profile ID are required for regeneration');
      return;
    }
    setRegenerating(true);
    try {
      await api.jobs.generateMaterials(jobId, profileId);
      toast.success('Materials regenerated successfully');
      await fetchMaterials();
      onRegenerated?.();
    } catch {
      toast.error('Failed to regenerate materials');
    } finally {
      setRegenerating(false);
    }
  };

  const handleCancel = () => {
    if (materials) {
      setEditResume(materials.resume_version_text);
      setEditCoverLetter(materials.cover_letter_text);
    }
    setEditing(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="bg-[#131B2E] border border-[#1E2D4A] rounded-xl max-w-5xl w-full max-h-[90vh] overflow-y-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-white truncate pr-4">
            {jobTitle} @ {company}
          </h2>
          <div className="flex items-center gap-2 shrink-0">
            {!editing && !loading && jobId && profileId && (
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="btn-gold text-xs disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 mr-1 ${regenerating ? 'animate-spin' : ''}`} />
                {regenerating ? 'Generating...' : 'Regenerate'}
              </button>
            )}
            {!editing && !loading && (
              <button onClick={() => setEditing(true)} className="btn-ghost text-xs">
                <Edit3 className="w-3 h-3 mr-1" /> Edit
              </button>
            )}
            <button
              onClick={onClose}
              className="text-slate-500 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-[#1E2D4A]">
          <button
            onClick={() => setActiveTab('resume')}
            className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors -mb-px flex items-center gap-1.5 ${
              activeTab === 'resume'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            <FileText className="w-3 h-3" />
            Resume
          </button>
          <button
            onClick={() => setActiveTab('cover_letter')}
            className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors -mb-px flex items-center gap-1.5 ${
              activeTab === 'cover_letter'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            <Mail className="w-3 h-3" />
            Cover Letter
          </button>
        </div>

        {/* Content */}
        {loading || regenerating ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-3" />
            <p className="text-sm text-slate-400">
              {regenerating ? 'Generating...' : 'Loading materials...'}
            </p>
          </div>
        ) : (
          <>
            {activeTab === 'resume' ? (
              <div>
                {editing ? (
                  <textarea
                    value={editResume}
                    onChange={(e) => setEditResume(e.target.value)}
                    className="input-field w-full min-h-[300px] font-mono text-xs"
                    rows={15}
                  />
                ) : (
                  <div className="bg-white rounded-lg border border-[#1E2D4A] max-h-96 overflow-y-auto">
                    {applicationId && (
                      <iframe
                        src={api.applications.previewResumeHtml(applicationId)}
                        className="w-full min-h-[384px] border-0"
                        title="Resume Preview"
                      />
                    )}
                  </div>
                )}
                {!editing && applicationId && (
                  <div className="flex gap-2 mt-4">
                    <a
                      href={api.applications.downloadResumeHtml(applicationId)}
                      download
                      className="btn-ghost text-xs"
                    >
                      <Download className="w-3 h-3 mr-1" /> Download HTML
                    </a>
                    <a
                      href={api.applications.downloadResumeDocx(applicationId)}
                      download
                      className="btn-primary text-xs"
                    >
                      <Download className="w-3 h-3 mr-1" /> Download Word
                    </a>
                  </div>
                )}
              </div>
            ) : (
              <div>
                {editing ? (
                  <textarea
                    value={editCoverLetter}
                    onChange={(e) => setEditCoverLetter(e.target.value)}
                    className="input-field w-full min-h-[250px] font-mono text-xs"
                    rows={10}
                  />
                ) : (
                  <div className="bg-white rounded-lg border border-[#1E2D4A] max-h-96 overflow-y-auto">
                    {applicationId && (
                      <iframe
                        src={api.applications.previewCoverLetterHtml(applicationId)}
                        className="w-full min-h-[384px] border-0"
                        title="Cover Letter Preview"
                      />
                    )}
                  </div>
                )}
                {!editing && applicationId && (
                  <div className="flex gap-2 mt-4">
                    <a
                      href={api.applications.downloadCoverLetterHtml(applicationId)}
                      download
                      className="btn-ghost text-xs"
                    >
                      <Download className="w-3 h-3 mr-1" /> Download HTML
                    </a>
                    <a
                      href={api.applications.downloadCoverLetterDocx(applicationId)}
                      download
                      className="btn-primary text-xs"
                    >
                      <Download className="w-3 h-3 mr-1" /> Download Word
                    </a>
                  </div>
                )}
              </div>
            )}

            {editing && (
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={handleCancel} className="btn-ghost text-xs">
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="btn-primary text-xs disabled:opacity-50"
                >
                  <Save className="w-3 h-3 mr-1" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
