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

  // Scheduler state
  const [schedulerStatus, setSchedulerStatus] = useState<'idle' | 'loading' | 'running' | 'stopped' | 'error'>('idle')
  const [schedulerInfo, setSchedulerInfo] = useState<{
    isRunning: boolean;
    nextIncrementalRun: string | null;
    nextFullRun: string | null;
    jobs: Array<{ id: string; name: string; nextRun: string | null }>;
  } | null>(null)
  const [schedulerLoading, setSchedulerLoading] = useState(false)
  const [schedulerMessage, setSchedulerMessage] = useState<string>('')
  const [schedulerMessageType, setSchedulerMessageType] = useState<'success' | 'error'>('success')
  const [schedulerHistory, setSchedulerHistory] = useState<Array<{
    timestamp: string;
    source: string;
    type: 'incremental' | 'full';
    newJobs: number;
    duplicates: number;
    errors: number;
  }>>([])

  useEffect(() => {
    loadQuestions()
    loadSchedulerInfo()
  }, [])

  const loadSchedulerInfo = async () => {
    setSchedulerLoading(true)
    setSchedulerStatus('loading')
    try {
      const res = await api.jobs.getSchedulerStatus()
      const data = res.data

      setSchedulerStatus(data.isRunning ? 'running' : 'stopped')
      setSchedulerInfo({
        isRunning: data.isRunning,
        nextIncrementalRun: data.nextIncrementalRun,
        nextFullRun: data.nextFullRun,
        jobs: data.jobs
      })

      // Scraping history will be populated by a real history API in the future
      setSchedulerHistory([])
    } catch (err: any) {
      setSchedulerMessage('Failed to load scheduler info')
      setSchedulerMessageType('error')
      setSchedulerStatus('error')
    } finally {
      setSchedulerLoading(false)
    }
  }

  const handleTriggerIncrementalScrape = async () => {
    setSchedulerMessage('')
    try {
      await api.jobs.triggerSchedulerIncremental()
      setSchedulerMessage('Incremental scrape triggered successfully!')
      setSchedulerMessageType('success')
      // Refresh scheduler info
      await loadSchedulerInfo()
    } catch (err: any) {
      setSchedulerMessage(err.response?.data?.detail || 'Failed to trigger incremental scrape')
      setSchedulerMessageType('error')
    }
  }

  const handleTriggerFullScrape = async () => {
    setSchedulerMessage('')
    try {
      await api.jobs.triggerSchedulerFull()
      setSchedulerMessage('Full scrape triggered successfully!')
      setSchedulerMessageType('success')
      // Refresh scheduler info
      await loadSchedulerInfo()
    } catch (err: any) {
      setSchedulerMessage(err.response?.data?.detail || 'Failed to trigger full scrape')
      setSchedulerMessageType('error')
    }
  }

  const loadQuestions = async () => {
    setQuestionsLoading(true)
    try {
      const meRes = await api.auth.me()
      const email = meRes.data.email
      const qRes = await api.auth.getSecretQuestions(email)
      let qs: SecretQuestion[] = qRes.data.questions || qRes.data

      if (!qs || qs.length === 0) {
        await api.auth.assignQuestions()
        const qRes2 = await api.auth.getSecretQuestions(email)
        qs = qRes2.data.questions || qRes2.data
      }

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

      {/* Scheduler Settings */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Job Scraping Scheduler</h2>
        <p className="text-sm text-gray-500 mb-4">
          Configure and monitor automated job scraping from LinkedIn and other sources.
        </p>

        {schedulerMessage && (
          <div
            className={`mb-4 p-4 rounded-lg text-sm ${
              schedulerMessageType === 'success'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}
          >
            {schedulerMessage}
          </div>
        )}

        {schedulerLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
          </div>
        ) : schedulerInfo ? (
          <>
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-4">
                <span className="font-medium">Scheduler Status:</span>
                <span className={schedulerStatus === 'running' ? 'text-green-600' : 'text-red-600'}>
                  {schedulerStatus === 'running' ? 'Running' : 'Stopped'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white rounded-lg p-4 border">
                  <h3 className="font-medium mb-2">Next Incremental Scrape</h3>
                  <p className="text-sm text-gray-600">{schedulerInfo.nextIncrementalRun}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border">
                  <h3 className="font-medium mb-2">Next Full Scrape</h3>
                  <p className="text-sm text-gray-600">{schedulerInfo.nextFullRun}</p>
                </div>
              </div>

              <div className="mt-6">
                <h3 className="font-medium mb-3">Scheduled Jobs</h3>
                {schedulerInfo.jobs.map((job, index) => (
                  <div key={index} className="border-t pt-4 first:border-t-0">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{job.name}</span>
                      <span className="text-sm text-gray-500">{job.nextRun}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6">
                <h3 className="font-medium mb-3">Manual Triggers</h3>
                <div className="space-y-3">
                  <button
                    onClick={handleTriggerIncrementalScrape}
                    className="btn-secondary w-full"
                  >
                    Trigger Incremental Scrape (Last 2 Hours)
                  </button>
                  <button
                    onClick={handleTriggerFullScrape}
                    className="btn-primary w-full"
                  >
                    Trigger Full Scrape
                  </button>
                </div>
              </div>

              {schedulerHistory.length > 0 && (
                <div className="mt-6">
                  <h3 className="font-medium mb-3">Recent Scraping History</h3>
                  <div className="space-y-2">
                    {schedulerHistory.map((record, index) => (
                      <div key={index} className="bg-white rounded-lg p-4 border">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="font-medium">{record.source} ({record.type})</span>
                            <span className="text-xs text-gray-500 block">{record.timestamp}</span>
                          </div>
                          <div className="text-right space-x-2">
                            <span className="text-sm font-medium text-green-600">+{record.newJobs}</span>
                            <span className="text-sm text-gray-500">{record.duplicates} duplicates</span>
                            {record.errors > 0 && (
                              <span className="text-sm text-red-500">{record.errors} errors</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <p className="text-gray-500 text-center py-8">Loading scheduler information...</p>
        )}
      </div>
    </div>
  )
}
