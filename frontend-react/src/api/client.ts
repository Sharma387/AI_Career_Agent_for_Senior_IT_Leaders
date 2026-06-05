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
  },

  profile: {
    get(profileId: number) {
      return client.get<CareerProfile>(`/api/profile/${profileId}`);
    },
    uploadResume(file: File) {
      const formData = new FormData();
      formData.append('file', file);
      return client.post<CareerProfile>('/api/profile/upload-resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    addProject(profileId: number, project: Project) {
      return client.post<Project>(`/api/profile/${profileId}/project`, project);
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
    generateMaterials(jobId: number, profileId: number) {
      return client.post<{ application_id: number; cover_letter: string; resume: string }>(
        `/api/jobs/${jobId}/generate-materials?profile_id=${profileId}`
      );
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
  },
};

export default client;
