import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { Sparkles, Mail, Lock } from 'lucide-react';

type ForgotStep = 'email' | 'questions' | 'success';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const [showForgot, setShowForgot] = useState(false);
  const [forgotStep, setForgotStep] = useState<ForgotStep>('email');
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [secretQuestions, setSecretQuestions] = useState<Array<{ question: string; answer: string }>>([]);
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [forgotError, setForgotError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleGetQuestions = async () => {
    setForgotError('');
    setForgotLoading(true);
    try {
      const res = await api.auth.getSecretQuestions(forgotEmail);
      const questions = res.data.questions.map((q: any) => ({ question: q.question, answer: '' }));
      setSecretQuestions(questions);
      setForgotStep('questions');
    } catch {
      setForgotError('No secret questions found for this email, or email is invalid.');
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError('');
    if (newPassword !== confirmNewPassword) {
      setForgotError('Passwords do not match');
      return;
    }
    if (newPassword.length < 6) {
      setForgotError('Password must be at least 6 characters');
      return;
    }
    setForgotLoading(true);
    try {
      const answerPairs = secretQuestions.map((q) => ({ question: q.question, answer: q.answer }));
      await api.auth.forgotPassword(forgotEmail, answerPairs, newPassword);
      setForgotStep('success');
    } catch {
      setForgotError('Incorrect answers or password reset failed.');
    } finally {
      setForgotLoading(false);
    }
  };

  const resetForgotFlow = () => {
    setShowForgot(false);
    setForgotStep('email');
    setForgotEmail('');
    setSecretQuestions([]);
    setNewPassword('');
    setConfirmNewPassword('');
    setForgotError('');
  };

  if (showForgot) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080C18]">
        <div className="w-full max-w-md p-8">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-white">Reset Password</h1>
            <p className="text-slate-500 mt-1 text-sm">Recover your account access</p>
          </div>

          <div className="rounded-xl border border-[#1E2D4A] bg-[#0E1628] p-8">
            {forgotError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg text-sm mb-4">
                {forgotError}
              </div>
            )}

            {forgotStep === 'email' && (
              <div className="space-y-5">
                <p className="text-sm text-slate-400">Enter your email to retrieve your security questions.</p>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    className="input-field"
                    required
                  />
                </div>
                <button
                  onClick={handleGetQuestions}
                  disabled={forgotLoading || !forgotEmail.trim()}
                  className="w-full btn-primary py-3 disabled:opacity-50"
                >
                  {forgotLoading ? 'Loading...' : 'Continue'}
                </button>
                <button onClick={resetForgotFlow} className="w-full text-sm text-slate-500 hover:text-slate-300 transition-colors">
                  Back to Sign In
                </button>
              </div>
            )}

            {forgotStep === 'questions' && (
              <form onSubmit={handleResetPassword} className="space-y-5">
                <p className="text-sm text-slate-400">Answer your security questions and set a new password.</p>
                {secretQuestions.map((q, i) => (
                  <div key={i} className="space-y-1">
                    <label className="block text-sm font-medium text-slate-300">{q.question}</label>
                    <input
                      type="text"
                      value={q.answer}
                      onChange={(e) => { const updated = [...secretQuestions]; updated[i] = { ...updated[i], answer: e.target.value }; setSecretQuestions(updated); }}
                      className="input-field"
                      required
                    />
                  </div>
                ))}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">New Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="input-field"
                    required
                    minLength={6}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm New Password</label>
                  <input
                    type="password"
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    className="input-field"
                    required
                    minLength={6}
                  />
                </div>
                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="w-full btn-primary py-3 disabled:opacity-50"
                >
                  {forgotLoading ? 'Resetting...' : 'Reset Password'}
                </button>
                <button type="button" onClick={resetForgotFlow} className="w-full text-sm text-slate-500 hover:text-slate-300 transition-colors">
                  Back to Sign In
                </button>
              </form>
            )}

            {forgotStep === 'success' && (
              <div className="space-y-5 text-center">
                <div className="text-emerald-400 text-lg font-medium">Password reset successful!</div>
                <p className="text-sm text-slate-400">You can now sign in with your new password.</p>
                <button onClick={resetForgotFlow} className="w-full btn-primary py-3">
                  Back to Sign In
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

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
          <p className="text-slate-500 mt-1 text-sm">Sign in to your account</p>
        </div>

        <div className="rounded-xl border border-[#1E2D4A] bg-[#0E1628] p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-10"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-3 disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="text-center mt-4">
            <button
              onClick={() => { setShowForgot(true); setForgotEmail(email); }}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              Forgot Password?
            </button>
          </div>

          <p className="text-center text-sm text-slate-500 mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
