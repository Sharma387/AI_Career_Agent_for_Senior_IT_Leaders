import axios from 'axios';
import type {
  User,
  CareerProfile,
  Project,
  JobPosting,
  MatchResult,
  Application,
  ApplicationStats,
  LoginPayload,
  RegisterPayload,
  AuthResponse,
  Skill,
  InterviewStrategy,
  SecretQuestion,
} from '../types';

const client = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const api = {
  auth: {
    login(payload: LoginPayload) {
      return client.post<AuthResponse>('/api/auth/login', {
        email: payload.email,
        password: payload.password,
      });
    },
    register(payload: RegisterPayload) {
      return client.post<AuthResponse>('/api/auth/register', payload);
    },
    me() {
      return client.get<User>('/api/auth/me');
    },
    setSecretQuestions(questions: { question: string; answer: string }[]) {
      return client.post('/api/auth/set-secret-questions', { questions });
    },
    getSecretQuestions(email: string) {
      return client.get<{ questions: SecretQuestion[] }>(`/api/auth/secret-questions/${email}`);
    },
    forgotPassword(email: string, answers: { question: string; answer: string }[], newPassword: string) {
      return client.post('/api/auth/forgot-password', {
        email,
        answers,
        new_password: newPassword,
      });
    },
    changePassword(currentPassword: string, newPassword: string) {
      return client.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
    },
    assignQuestions() {
      return client.post<{ message: string; assigned: boolean }>('/api/auth/assign-questions');
    },
  },

  profile: {
    get(profileId: number) {
      return client.get<CareerProfile>(`/api/profile/${profileId}`);
    },
    getMyProfile() {
      return client.get<{ profile: CareerProfile | null }>('/api/profile/me');
    },
    uploadResume(file: File) {
      const formData = new FormData();
      formData.append('file', file);
      return client.post<CareerProfile>('/api/profile/upload-resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    update(profileId: number, data: Partial<CareerProfile>) {
      return client.put<CareerProfile>(`/api/profile/${profileId}`, data);
    },
    updateSkills(profileId: number, skills: { name: string; category: string; proficiency?: string }[]) {
      return client.put<Skill[]>(`/api/profile/${profileId}/skills`, { skills });
    },
    addProject(profileId: number, project: Project) {
      return client.post<Project>(`/api/profile/${profileId}/project`, project);
    },
    updateProject(profileId: number, projectId: number, data: Partial<Project>) {
      return client.put<Project>(`/api/profile/${profileId}/projects/${projectId}`, data);
    },
    deleteProject(profileId: number, projectId: number) {
      return client.delete(`/api/profile/${profileId}/projects/${projectId}`);
    },
    downloadResumeHtml(profileId: number) {
      return `/api/profile/${profileId}/resume/html?download=true`;
    },
    previewResumeHtml(profileId: number) {
      return `/api/profile/${profileId}/resume/html`;
    },
    downloadResumeDocx(profileId: number) {
      return `/api/profile/${profileId}/resume/docx`;
    },
  },

  jobs: {
    add(text: string, source?: string) {
      return client.post<JobPosting>('/api/jobs/add', { text, source: source || 'manual' });
    },
    list() {
      return client.get<JobPosting[]>('/api/jobs');
    },
    match(jobId: number, profileId: number) {
      return client.post<MatchResult>(`/api/jobs/${jobId}/match?profile_id=${profileId}`);
    },
    matchEnhanced(jobId: number, profileId: number) {
      return client.post<MatchResult & { score_breakdown: any; improvement_recommendations: any[] }>(
        `/api/jobs/${jobId}/match-enhanced?profile_id=${profileId}`
      );
    },
    generateMaterials(jobId: number, profileId: number) {
      return client.post<{ application_id: number; cover_letter: string; resume: string; resume_html: string; cover_letter_html: string }>(
        `/api/jobs/${jobId}/generate-materials?profile_id=${profileId}`
      );
    },
    getInterviewStrategy(jobId: number, profileId: number) {
      return client.get<InterviewStrategy>(`/api/jobs/${jobId}/interview-strategy/${profileId}`);
    },
    triggerScrape(request: { source?: string; keywords: string; location: string; hours?: number; force?: boolean }) {
      return client.post(`/api/jobs/scrape/trigger`, request);
    },
    getSearchUsage() {
      return client.get(`/api/jobs/search/usage`);
    },
    triggerIncrementalScrape(hours: number, source?: string) {
      return client.post(`/api/jobs/scrape/incremental`, { hours, source });
    },
    triggerFullScrape(source?: string) {
      return client.post(`/api/jobs/scrape/full`, { source });
    },
    triggerSchedulerIncremental() {
      return client.post(`/api/scheduler/trigger-incremental`);
    },
    triggerSchedulerFull() {
      return client.post(`/api/scheduler/trigger-full`);
    },
    getSchedulerStatus() {
      return client.get(`/api/scheduler/status`);
    },
  },

  match: {
    getPrevious(jobId: number, profileId: number) {
      return client.get<{
        match_id: number;
        match_score: number;
        strengths: string[];
        gaps: string[];
        evidence: any[];
        explanation: string;
        recommendation: string;
        created_at: string;
        articulations: Array<{
          id: number;
          gap_text: string;
          has_skill: boolean;
          evidence: string;
        }>;
      } | null>(`/api/match/${jobId}/${profileId}`);
    },
    saveArticulations(matchId: number, articulations: Array<{ gap_text: string; has_skill: boolean; evidence: string }>) {
      return client.post(`/api/match/${matchId}/articulations`, articulations);
    },
  },

  llm: {
    getInfo() {
      return client.get<{ provider: string; model: string; embedding_model: string }>('/api/llm/info');
    },
  },

  applications: {
    track(jobId: number, profileId: number, status?: string) {
      return client.post<Application>('/api/applications/track', {
        job_id: jobId,
        profile_id: profileId,
        status: status || 'applied',
      });
    },
    updateStatus(applicationId: number, newStatus: string, feedback?: string) {
      return client.put<Application>(`/api/applications/${applicationId}/status`, {
        new_status: newStatus,
        feedback,
      });
    },
    getStats(profileId: number) {
      return client.get<ApplicationStats>(`/api/applications/stats/${profileId}`);
    },
    list(profileId: number) {
      return client.get<Application[]>(`/api/applications/${profileId}`);
    },
    getInsights(profileId: number) {
      return client.get(`/api/applications/${profileId}/insights`);
    },
    getMaterials(applicationId: number) {
      return client.get<{
        application_id: number;
        resume_version_text: string;
        cover_letter_text: string;
        job_title: string;
        company: string;
      }>(`/api/applications/${applicationId}/materials`);
    },
    updateMaterials(applicationId: number, resumeText: string, coverLetterText?: string) {
      return client.put(`/api/applications/${applicationId}/materials`, {
        resume_text: resumeText,
        cover_letter_text: coverLetterText,
      });
    },
    downloadResumeHtml(applicationId: number) {
      return `/api/applications/${applicationId}/resume/html?download=true`;
    },
    downloadCoverLetterHtml(applicationId: number) {
      return `/api/applications/${applicationId}/cover-letter/html?download=true`;
    },
    previewResumeHtml(applicationId: number) {
      return `/api/applications/${applicationId}/resume/html`;
    },
    previewCoverLetterHtml(applicationId: number) {
      return `/api/applications/${applicationId}/cover-letter/html`;
    },
    downloadResumeDocx(applicationId: number) {
      return `/api/applications/${applicationId}/resume/docx`;
    },
    downloadCoverLetterDocx(applicationId: number) {
      return `/api/applications/${applicationId}/cover-letter/docx`;
    },
  },
};

export default client;
