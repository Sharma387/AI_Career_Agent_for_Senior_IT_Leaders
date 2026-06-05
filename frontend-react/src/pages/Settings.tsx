import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { SecretQuestion } from '../types'

export function Settings() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState('')
  const [passwordMessageType, setPasswordMessageType] = useState<'success' | 'error'>('success')

  const [questions, setQuestions] = useState<SecretQuestion[]>([])
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [editingAll, setEditingAll] = useState<Record<number, boolean>>({})
  const [questionsLoading, setQuestionsLoading] = useState(true)
  const [savingQuestions, setSavingQuestions] = useState(false)
  const [questionsMessage, setQuestionsMessage] = useState('')
  const [questionsMessageType, setQuestionsMessageType] = useState<'success' | 'error'>('success')

  useEffect(() => {
    loadQuestions()
  }, [])

  const loadQuestions = async () => {
    setQuestionsLoading(true)
    try {
      const meRes = await api.auth.me()
      const email = meRes.data.email
      const qRes = await api.auth.getSecretQuestions(email)
      const qs: SecretQuestion[] = qRes.data.questions || qRes.data
      setQuestions(qs)
      const initialAnswers: Record<number, string> = {}
      qs.forEach((q) => {
        if (q.answer_set) initialAnswers[q.id] = ''
      })
      setAnswers(initialAnswers)
    } catch (err) {
      setQuestionsMessage('Failed to load security questions')
      setQuestionsMessageType('error')
    } finally {
      setQuestionsLoading(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordMessage('')

    if (newPassword !== confirmPassword) {
      setPasswordMessage('Passwords do not match')
      setPasswordMessageType('error')
      return
    }
    if (newPassword.length < 8) {
      setPasswordMessage('Password must be at least 8 characters')
      setPasswordMessageType('error')
      return
    }

    setPasswordLoading(true)
    try {
      await api.auth.changePassword(currentPassword, newPassword)
      setPasswordMessage('Password changed successfully')
      setPasswordMessageType('success')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setPasswordMessage(err.response?.data?.detail || 'Failed to change password')
      setPasswordMessageType('error')
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleSaveQuestions = async (e: React.FormEvent) => {
    e.preventDefault()
    setQuestionsMessage('')
    setSavingQuestions(true)
    try {
      const payload = questions.map((q) => ({
        question: q.question,
        answer: answers[q.id] || '',
      }))
      await api.auth.setSecretQuestions(payload)
      setQuestionsMessage('Security questions saved successfully')
      setQuestionsMessageType('success')
      setEditingAll({})
      loadQuestions()
    } catch (err: any) {
      setQuestionsMessage(err.response?.data?.detail || 'Failed to save security questions')
      setQuestionsMessageType('error')
    } finally {
      setSavingQuestions(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Change Password */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Change Password</h2>

        {passwordMessage && (
          <div
            className={`mb-4 p-4 rounded-lg text-sm ${
              passwordMessageType === 'success'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}
          >
            {passwordMessage}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Current Password
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="input-field"
              placeholder="Enter current password"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input-field"
              placeholder="Min 8 characters"
              minLength={8}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input-field"
              placeholder="Re-enter new password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={passwordLoading}
            className="btn-primary px-6 py-2 text-sm disabled:opacity-50"
          >
            {passwordLoading ? 'Changing...' : 'Change Password'}
          </button>
        </form>
      </div>

      {/* Security Questions */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Security Questions</h2>
        <p className="text-sm text-gray-500 mb-4">
          These questions are used for password recovery. System-assigned questions cannot be changed.
        </p>

        {questionsMessage && (
          <div
            className={`mb-4 p-4 rounded-lg text-sm ${
              questionsMessageType === 'success'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}
          >
            {questionsMessage}
          </div>
        )}

        {questionsLoading ? (
          <p className="text-gray-500">Loading questions...</p>
        ) : questions.length === 0 ? (
          <p className="text-gray-500">No security questions found.</p>
        ) : (
          <form onSubmit={handleSaveQuestions} className="space-y-4">
            {questions.map((q) => (
              <div key={q.id}>
                <div className="flex items-center gap-2 mb-1.5">
                  <label className="text-sm font-medium text-gray-700">{q.question}</label>
                  {q.answer_set && !editingAll[q.id] && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Already set
                    </span>
                  )}
                </div>
                {q.answer_set && !editingAll[q.id] ? (
                  <button
                    type="button"
                    onClick={() => setEditingAll((prev) => ({ ...prev, [q.id]: true }))}
                    className="btn-secondary px-4 py-1.5 text-xs"
                  >
                    Update
                  </button>
                ) : (
                  <input
                    type="text"
                    value={answers[q.id] || ''}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                    className="input-field"
                    placeholder="Your answer"
                    required
                  />
                )}
              </div>
            ))}

            <button
              type="submit"
              disabled={savingQuestions}
              className="btn-primary px-6 py-2 text-sm disabled:opacity-50"
            >
              {savingQuestions ? 'Saving...' : 'Save Answers'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
