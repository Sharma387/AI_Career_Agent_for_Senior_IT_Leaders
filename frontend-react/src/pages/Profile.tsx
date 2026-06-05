import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { Project } from '../types';

const PROFILE_ID_KEY = 'career_agent_profile_id';

interface ProfileData {
  id: number;
  full_name: string;
  email: string;
  summary: string;
  raw_resume_text: string;
  created_at: string;
}

interface SkillData {
  id: number;
  name: string;
  category: string;
}

const emptyProject: Project = {
  title: '',
  description: '',
  role: '',
  technologies: [],
  impact: '',
  star_situation: '',
  star_task: '',
  star_action: '',
  star_result: '',
};

export function Profile() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [skills, setSkills] = useState<SkillData[]>([]);
  const [profileId, setProfileId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [project, setProject] = useState<Project>({ ...emptyProject });
  const [techInput, setTechInput] = useState('');
  const [editingSummary, setEditingSummary] = useState(false);
  const [summaryText, setSummaryText] = useState('');

  const loadProfile = async (id: number) => {
    try {
      const res = await api.profile.get(id);
      const data = res.data as any;
      if (data.profile) {
        setProfile(data.profile);
        setSummaryText(data.profile.summary || '');
      }
      setProjects(data.projects || []);
      setSkills(data.skills || []);
    } catch {
      localStorage.removeItem(PROFILE_ID_KEY);
      setProfileId(null);
    }
  };

  useEffect(() => {
    const stored = localStorage.getItem(PROFILE_ID_KEY);
    if (stored) {
      const id = Number(stored);
      setProfileId(id);
      loadProfile(id).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await api.profile.uploadResume(file);
      const newProfileId = res.data.profile_id ?? res.data.id;
      if (!newProfileId) throw new Error('No profile ID returned');
      localStorage.setItem(PROFILE_ID_KEY, String(newProfileId));
      setProfileId(newProfileId);
      await loadProfile(newProfileId);
    } catch {
      alert('Failed to upload resume');
    } finally {
      setUploading(false);
    }
  };

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profileId) {
      alert('Upload a resume first to create your profile');
      return;
    }
    try {
      await api.profile.addProject(profileId, project);
      setProject({ ...emptyProject });
      setShowProjectForm(false);
      await loadProfile(profileId);
      alert('Project added successfully');
    } catch {
      alert('Failed to add project');
    }
  };

  const addTech = () => {
    if (techInput.trim() && !project.technologies.includes(techInput.trim())) {
      setProject({ ...project, technologies: [...project.technologies, techInput.trim()] });
      setTechInput('');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <h1 className="text-2xl font-bold">Your Profile</h1>

      {/* Base Resume Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Base Resume</h2>
          {profileId && profile?.raw_resume_text && (
            <div className="flex gap-2">
              <a
                href={api.profile.downloadResumeHtml(profileId)}
                download
                className="btn-secondary text-sm"
              >
                Download HTML
              </a>
              <a
                href={api.profile.downloadResumeDocx(profileId)}
                download
                className="btn-primary text-sm"
              >
                Download Word (.docx)
              </a>
            </div>
          )}
        </div>
        {profile?.raw_resume_text ? (
          <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{profile.raw_resume_text}</p>
          </div>
        ) : (
          <p className="text-gray-500 mb-4">No resume uploaded yet. Upload your base resume to get started.</p>
        )}
        <div className="flex gap-2 mt-4">
          <label className="btn-primary inline-block cursor-pointer">
            {uploading ? 'Uploading...' : profile ? 'Replace Resume' : 'Upload Resume'}
            <input type="file" accept=".pdf,.doc,.docx,.txt" onChange={handleResumeUpload} className="hidden" />
          </label>
        </div>
      </div>

      {/* Summary Section */}
      {profile && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Profile Summary</h2>
            <button onClick={() => setEditingSummary(!editingSummary)} className="text-sm text-blue-600 hover:text-blue-700">
              {editingSummary ? 'Cancel' : 'Edit'}
            </button>
          </div>
          {editingSummary ? (
            <div>
              <textarea
                value={summaryText}
                onChange={(e) => setSummaryText(e.target.value)}
                className="input-field w-full"
                rows={4}
              />
              <button className="btn-primary text-sm mt-2">Save Summary</button>
            </div>
          ) : (
            <p className="text-gray-700 whitespace-pre-wrap">{profile.summary || 'No summary yet.'}</p>
          )}
        </div>
      )}

      {/* Skills Section */}
      {skills.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Skills</h2>
          <div className="flex flex-wrap gap-2">
            {skills.map((skill) => (
              <span key={skill.id} className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm">
                {skill.name}
                {skill.category && <span className="text-blue-500 ml-1">({skill.category})</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Projects Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Projects ({projects.length})</h2>
          <button onClick={() => setShowProjectForm(!showProjectForm)} className="btn-primary text-sm">
            {showProjectForm ? 'Cancel' : '+ Add Project'}
          </button>
        </div>

        {projects.length > 0 && (
          <div className="space-y-4 mb-4">
            {projects.map((p, i) => (
              <div key={p.id || i} className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-medium">{p.title}</h3>
                {p.role && <p className="text-sm text-gray-600">{p.role}</p>}
                {p.description && <p className="text-sm text-gray-700 mt-1">{p.description}</p>}
                {p.technologies && <p className="text-xs text-gray-500 mt-1">Tech: {p.technologies}</p>}
                {p.impact && <p className="text-sm text-green-700 mt-1">Impact: {p.impact}</p>}
              </div>
            ))}
          </div>
        )}

        {showProjectForm && (
          <form onSubmit={handleAddProject} className="space-y-4 border-t pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Title</label>
                <input
                  value={project.title}
                  onChange={(e) => setProject({ ...project, title: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Role</label>
                <input
                  value={project.role}
                  onChange={(e) => setProject({ ...project, role: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={project.description}
                onChange={(e) => setProject({ ...project, description: e.target.value })}
                className="input-field"
                rows={2}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Technologies</label>
              <div className="flex gap-2">
                <input
                  value={techInput}
                  onChange={(e) => setTechInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTech())}
                  className="input-field flex-1"
                  placeholder="Add technology"
                />
                <button type="button" onClick={addTech} className="btn-secondary text-sm">Add</button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {project.technologies.map((tech) => (
                  <span key={tech} className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm flex items-center gap-1">
                    {tech}
                    <button type="button" onClick={() => setProject({ ...project, technologies: project.technologies.filter(t => t !== tech) })}>×</button>
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Impact</label>
              <input
                value={project.impact}
                onChange={(e) => setProject({ ...project, impact: e.target.value })}
                className="input-field"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">STAR: Situation</label>
                <textarea value={project.star_situation} onChange={(e) => setProject({ ...project, star_situation: e.target.value })} className="input-field" rows={2} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">STAR: Task</label>
                <textarea value={project.star_task} onChange={(e) => setProject({ ...project, star_task: e.target.value })} className="input-field" rows={2} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">STAR: Action</label>
                <textarea value={project.star_action} onChange={(e) => setProject({ ...project, star_action: e.target.value })} className="input-field" rows={2} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">STAR: Result</label>
                <textarea value={project.star_result} onChange={(e) => setProject({ ...project, star_result: e.target.value })} className="input-field" rows={2} />
              </div>
            </div>

            <button type="submit" className="btn-primary">Save Project</button>
          </form>
        )}
      </div>
    </div>
  );
}
