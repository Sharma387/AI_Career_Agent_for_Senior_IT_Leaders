import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { CareerProfile, Project } from '../types';

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
  const [profile, setProfile] = useState<CareerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [project, setProject] = useState<Project>({ ...emptyProject });
  const [techInput, setTechInput] = useState('');

  useEffect(() => {
    setLoading(false);
  }, []);

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await api.profile.uploadResume(file);
      setProfile(res.data);
    } catch {
      alert('Failed to upload resume');
    } finally {
      setUploading(false);
    }
  };

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) {
      alert('Upload a resume first to create your profile');
      return;
    }
    try {
      await api.profile.addProject(profile.id, project);
      setProject({ ...emptyProject });
      setShowProjectForm(false);
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

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Resume</h2>
        {profile?.raw_resume_text ? (
          <div className="bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{profile.raw_resume_text}</p>
          </div>
        ) : (
          <p className="text-gray-500 mb-4">No resume uploaded yet. Upload your resume to get started.</p>
        )}
        <label className="btn-primary inline-block cursor-pointer">
          {uploading ? 'Uploading...' : 'Upload Resume'}
          <input type="file" accept=".pdf,.doc,.docx,.txt" onChange={handleResumeUpload} className="hidden" />
        </label>
      </div>

      {profile && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Projects</h2>
            <button onClick={() => setShowProjectForm(!showProjectForm)} className="btn-primary text-sm">
              {showProjectForm ? 'Cancel' : '+ Add Project'}
            </button>
          </div>

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
      )}

      {profile?.summary && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-2">Profile Summary</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{profile.summary}</p>
        </div>
      )}
    </div>
  );
}
