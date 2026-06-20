import { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { Sparkles, Upload } from 'lucide-react';

type Step = 'account' | 'security' | 'resume';

export function Register() {
  const [step, setStep] = useState<Step>('account');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
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
    setUploadProgress('📤 Uploading resume file...');
    try {
      setUploadProgress('📤 Uploading resume file... 100%');
      await api.profile.uploadResume(selectedFile);
      
      setUploadProgress('📝 Parsing resume content...');
      const profileRes = await api.profile.getMyProfile();
      
      setUploadProgress('🔍 Extracting resume sections...');
      setUploadProgress('🤖 Processing with AI...');
      
      if (profileRes.data.profile) {
        setProfileId(profileRes.data.profile.id);
      }
      setUploadProgress('✅ Resume processed successfully!');
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      setUploadProgress('');
      setUploading(false);
    }
  };

  const stepLabels = ['Account', 'Security', 'Resume'];
  const stepIndex = step === 'account' ? 0 : step === 'security' ? 1 : 2;

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#080C18]">
      <div className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white">
            Career<span className="text-blue-400">AI</span>
          </h1>
          <p className="text-slate-500 mt-1 text-sm">Create your account</p>
        </div>

        {/* Step Indicator */}
        <div className="flex justify-between mb-6 px-4">
          {stepLabels.map((label, i) => (
            <div key={label} className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                  i <= stepIndex
                    ? 'bg-blue-600 border-blue-600 text-white'
                    : 'bg-transparent border-[#1E2D4A] text-slate-500'
                }`}
              >
                {i + 1}
              </div>
              <span className={`text-[10px] mt-1 ${i <= stepIndex ? 'text-blue-400' : 'text-slate-500'}`}>
                {label}
              </span>
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-[#1E2D4A] bg-[#0E1628] p-8">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          {step === 'account' && (
            <form onSubmit={handleAccountSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
                <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className="input-field" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" required minLength={8} />
              </div>
              <button type="submit" disabled={loading} className="w-full btn-primary py-3 disabled:opacity-50">
                {loading ? 'Creating account...' : 'Create Account'}
              </button>
            </form>
          )}

          {step === 'security' && (
            <form onSubmit={handleSecuritySubmit} className="space-y-5">
              <p className="text-xs text-slate-400">Answer your security questions to enable password recovery.</p>
              {questions.map((q, i) => (
                <div key={i}>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">{q.question}</label>
                  <input type="text" value={q.answer} onChange={(e) => updateAnswer(i, e.target.value)} className="input-field" required />
                </div>
              ))}
              <button type="submit" disabled={loading} className="w-full btn-primary py-3 disabled:opacity-50">
                {loading ? 'Saving...' : 'Save Answers'}
              </button>
            </form>
          )}

          {step === 'resume' && (
            <div className="space-y-5">
              <p className="text-xs text-slate-400">Upload your resume to get started, or skip for now.</p>

              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  dragOver ? 'border-blue-500 bg-blue-500/5' : 'border-[#1E2D4A] hover:border-slate-500'
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
                <Upload className="w-8 h-8 text-slate-500 mx-auto mb-3" />
                {selectedFile ? (
                  <p className="text-sm text-slate-300">{selectedFile.name}</p>
                ) : (
                  <p className="text-xs text-slate-500">Drag & drop your resume here, or click to browse</p>
                )}
              </div>

              {selectedFile && (
                <button onClick={handleUpload} disabled={uploading} className="w-full btn-gold py-3 disabled:opacity-50">
                  {uploading ? 'Uploading...' : 'Upload & Continue'}
                </button>
              )}
              
              {/* Upload Progress */}
              {uploading && uploadProgress && (
                <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20 animate-pulse">
                  <p className="text-sm text-blue-300 font-medium">{uploadProgress}</p>
                </div>
              )}

              <button onClick={() => navigate('/')} className="w-full text-center text-xs text-slate-500 hover:text-slate-300 transition-colors">
                Skip for now
              </button>
            </div>
          )}

          <p className="text-center text-xs text-slate-500 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
