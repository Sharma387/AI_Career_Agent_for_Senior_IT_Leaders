import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

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
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="w-full max-w-md p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white">AI Career Agent</h1>
            <p className="text-slate-400 mt-2">Reset your password</p>
          </div>

          <div className="bg-white rounded-xl shadow-xl p-8">
            {forgotError && (
              <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
                {forgotError}
              </div>
            )}

            {forgotStep === 'email' && (
              <div className="space-y-5">
                <p className="text-sm text-gray-600">Enter your email to retrieve your security questions.</p>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
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
                <button onClick={resetForgotFlow} className="w-full text-sm text-gray-600 hover:text-gray-800">
                  Back to Sign In
                </button>
              </div>
            )}

            {forgotStep === 'questions' && (
              <form onSubmit={handleResetPassword} className="space-y-5">
                <p className="text-sm text-gray-600">Answer your security questions and set a new password.</p>
                {secretQuestions.map((q, i) => (
                  <div key={i} className="space-y-1">
                    <label className="block text-sm font-medium text-gray-700">{q.question}</label>
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
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
                <button type="button" onClick={resetForgotFlow} className="w-full text-sm text-gray-600 hover:text-gray-800">
                  Back to Sign In
                </button>
              </form>
            )}

            {forgotStep === 'success' && (
              <div className="space-y-5 text-center">
                <div className="text-green-600 text-lg font-medium">Password reset successful!</div>
                <p className="text-sm text-gray-600">You can now sign in with your new password.</p>
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">AI Career Agent</h1>
          <p className="text-slate-400 mt-2">Sign in to your account</p>
        </div>

        <div className="bg-white rounded-xl shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

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
              />
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
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Forgot Password?
            </button>
          </div>

          <p className="text-center text-sm text-gray-600 mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-600 hover:text-blue-700 font-medium">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
