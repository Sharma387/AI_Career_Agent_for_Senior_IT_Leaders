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
      const formData = new URLSearchParams();
      formData.append('username', payload.email);
      formData.append('password', payload.password);
      return client.post<AuthResponse>('/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
    },
    register(payload: RegisterPayload) {
      return client.post<User>('/api/auth/register', payload);
    },
  },

  profile: {
    get() {
      return client.get<CareerProfile>('/api/profile');
    },
    uploadResume(file: File) {
      const formData = new FormData();
      formData.append('file', file);
      return client.post<CareerProfile>('/api/profile/resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    addProject(project: Project) {
      return client.post<Project>('/api/profile/projects', project);
    },
  },

  jobs: {
    add(job: Partial<JobPosting>) {
      return client.post<JobPosting>('/api/jobs', job);
    },
    list(params?: { seniority_level?: string; location?: string }) {
      return client.get<JobPosting[]>('/api/jobs', { params });
    },
    match(jobId: number) {
      return client.post<MatchResult>(`/api/jobs/${jobId}/match`);
    },
  },

  materials: {
    generate(jobId: number) {
      return client.post<{ cover_letter: string; interview_prep: string }>(
        `/api/materials/generate`,
        { job_id: jobId }
      );
    },
  },

  applications: {
    track(payload: { job_id: number; status?: string }) {
      return client.post<Application>('/api/applications/track', payload);
    },
    updateStatus(applicationId: string, status: string) {
      return client.patch<Application>(`/api/applications/${applicationId}/status`, {
        status,
      });
    },
    getStats() {
      return client.get<ApplicationStats>('/api/applications/stats');
    },
    list() {
      return client.get<Application[]>('/api/applications');
    },
  },

  insights: {
    get() {
      return client.get<{
        recommendations: string[];
        market_trends: string[];
        skill_gaps: string[];
      }>('/api/insights');
    },
  },
};

export default client;
