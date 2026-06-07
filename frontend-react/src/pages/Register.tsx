import { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

type Step = 'account' | 'security' | 'resume';

export function Register() {
  const [step, setStep] = useState<Step>('account');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<Array<{ question: string; answer: string }>>([]);
  const [uploading, setUploading] = useState(false);
  const { register, setProfileId } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleAccountSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(email, password, fullName);
      setStep('security');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const fetchQuestions = useCallback(async () => {
    try {
      const res = await api.auth.getSecretQuestions(email);
      setQuestions(res.data.questions.map((q) => ({ question: q.question, answer: '' })));
    } catch {
      setError('Failed to load security questions');
    }
  }, [email]);

  useEffect(() => {
    if (step === 'security') {
      fetchQuestions();
    }
  }, [step, fetchQuestions]);

  const handleSecuritySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.auth.setSecretQuestions(questions);
      setStep('resume');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save answers';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const updateAnswer = (index: number, value: string) => {
    setQuestions((prev) => prev.map((q, i) => (i === index ? { ...q, answer: value } : q)));
  };

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError('');
    try {
      await api.profile.uploadResume(selectedFile);
      const profileRes = await api.profile.getMyProfile();
      if (profileRes.data.profile) {
        setProfileId(profileRes.data.profile.id);
      }
      navigate('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  const stepLabels = ['Account', 'Security', 'Resume'];
  const stepIndex = step === 'account' ? 0 : step === 'security' ? 1 : 2;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">AI Career Agent</h1>
          <p className="text-slate-400 mt-2">Create your account</p>
        </div>

        <div className="flex justify-between mb-6 px-4">
          {stepLabels.map((label, i) => (
            <div key={label} className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  i <= stepIndex
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-600 text-slate-300'
                }`}
              >
                {i + 1}
              </div>
              <span
                className={`text-xs mt-1 ${
                  i <= stepIndex ? 'text-white' : 'text-slate-400'
                }`}
              >
                {label}
              </span>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl shadow-xl p-8">
          {error && (
            <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          {step === 'account' && (
            <form onSubmit={handleAccountSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  required
                  minLength={8}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-3 disabled:opacity-50"
              >
                {loading ? 'Creating account...' : 'Create Account'}
              </button>
            </form>
          )}

          {step === 'security' && (
            <form onSubmit={handleSecuritySubmit} className="space-y-5">
              <p className="text-sm text-gray-600">
                Answer your security questions to enable password recovery.
              </p>
              {questions.map((q, i) => (
                <div key={i}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {q.question}
                  </label>
                  <input
                    type="text"
                    value={q.answer}
                    onChange={(e) => updateAnswer(i, e.target.value)}
                    className="input-field"
                    required
                  />
                </div>
              ))}
              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-3 disabled:opacity-50"
              >
                {loading ? 'Saving...' : 'Save Answers'}
              </button>
            </form>
          )}

          {step === 'resume' && (
            <div className="space-y-5">
              <p className="text-sm text-gray-600">
                Upload your resume to get started, or skip for now.
              </p>

              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.doc,.docx"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileSelect(file);
                  }}
                />
                {selectedFile ? (
                  <p className="text-sm text-gray-700">{selectedFile.name}</p>
                ) : (
                  <p className="text-sm text-gray-500">
                    Drag & drop your resume here, or click to browse
                  </p>
                )}
              </div>

              {selectedFile && (
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="w-full btn-primary py-3 disabled:opacity-50"
                >
                  {uploading ? 'Uploading...' : 'Upload & Continue'}
                </button>
              )}

              <button
                onClick={() => navigate('/')}
                className="w-full text-center text-sm text-gray-600 hover:text-gray-800"
              >
                Skip for now
              </button>
            </div>
          )}

          <p className="text-center text-sm text-gray-600 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-600 hover:text-blue-700 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
