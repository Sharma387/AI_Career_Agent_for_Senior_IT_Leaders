import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { Lock, Shield, Clock, Play } from 'lucide-react'
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
  const [, setSchedulerHistory] = useState<Array<{
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
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* Change Password */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Lock className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Change Password</h2>
        </div>

        {passwordMessage && (
          <div className={`mb-4 p-3 rounded-lg text-xs ${
            passwordMessageType === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border border-red-500/20 text-red-400'
          }`}>
            {passwordMessage}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Current Password</label>
            <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className="input-field" placeholder="Enter current password" required />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">New Password</label>
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="input-field" placeholder="Min 8 characters" minLength={8} required />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Confirm New Password</label>
            <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="input-field" placeholder="Re-enter new password" required />
          </div>
          <button type="submit" disabled={passwordLoading} className="btn-primary text-xs disabled:opacity-50">
            {passwordLoading ? 'Changing...' : 'Change Password'}
          </button>
        </form>
      </div>

      {/* Security Questions */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-semibold text-white">Security Questions</h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          These questions are used for password recovery. System-assigned questions cannot be changed.
        </p>

        {questionsMessage && (
          <div className={`mb-4 p-3 rounded-lg text-xs ${
            questionsMessageType === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border border-red-500/20 text-red-400'
          }`}>
            {questionsMessage}
          </div>
        )}

        {questionsLoading ? (
          <p className="text-slate-500 text-xs">Loading questions...</p>
        ) : questions.length === 0 ? (
          <p className="text-slate-500 text-xs">No security questions found.</p>
        ) : (
          <form onSubmit={handleSaveQuestions} className="space-y-4">
            {questions.map((q) => (
              <div key={q.id}>
                <div className="flex items-center gap-2 mb-1.5">
                  <label className="text-xs font-medium text-slate-300">{q.question}</label>
                  {q.answer_set && !editingAll[q.id] && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Set
                    </span>
                  )}
                </div>
                {q.answer_set && !editingAll[q.id] ? (
                  <button
                    type="button"
                    onClick={() => setEditingAll((prev) => ({ ...prev, [q.id]: true }))}
                    className="btn-ghost text-xs"
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
            <button type="submit" disabled={savingQuestions} className="btn-primary text-xs disabled:opacity-50">
              {savingQuestions ? 'Saving...' : 'Save Answers'}
            </button>
          </form>
        )}
      </div>

      {/* Scheduler */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-white">Job Scraping Scheduler</h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Configure and monitor automated job scraping.
        </p>

        {schedulerMessage && (
          <div className={`mb-4 p-3 rounded-lg text-xs ${
            schedulerMessageType === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border border-red-500/20 text-red-400'
          }`}>
            {schedulerMessage}
          </div>
        )}

        {schedulerLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto" />
          </div>
        ) : schedulerInfo ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300">Status:</span>
              <span className={`text-xs font-medium ${schedulerStatus === 'running' ? 'text-emerald-400' : 'text-red-400'}`}>
                {schedulerStatus === 'running' ? '● Running' : '○ Stopped'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#0E1628] rounded-lg p-3 border border-[#1E2D4A]">
                <h3 className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Next Incremental</h3>
                <p className="text-xs text-slate-300 font-mono">{schedulerInfo.nextIncrementalRun || '—'}</p>
              </div>
              <div className="bg-[#0E1628] rounded-lg p-3 border border-[#1E2D4A]">
                <h3 className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Next Full</h3>
                <p className="text-xs text-slate-300 font-mono">{schedulerInfo.nextFullRun || '—'}</p>
              </div>
            </div>

            {schedulerInfo.jobs.length > 0 && (
              <div>
                <h3 className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Scheduled Jobs</h3>
                {schedulerInfo.jobs.map((job, index) => (
                  <div key={index} className="flex items-center justify-between py-2 border-t border-[#1E2D4A] first:border-t-0">
                    <span className="text-xs text-slate-300">{job.name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{job.nextRun || '—'}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-2 pt-2">
              <h3 className="text-[10px] text-slate-500 uppercase tracking-wider">Manual Triggers</h3>
              <button onClick={handleTriggerIncrementalScrape} className="btn-ghost w-full text-xs">
                <Play className="w-3 h-3 mr-1" /> Incremental Scrape (Last 2 Hours)
              </button>
              <button onClick={handleTriggerFullScrape} className="btn-primary w-full text-xs">
                <Play className="w-3 h-3 mr-1" /> Full Scrape
              </button>
            </div>
          </div>
        ) : (
          <p className="text-slate-500 text-center py-8 text-xs">Loading scheduler info...</p>
        )}
      </div>
    </div>
  )
}
