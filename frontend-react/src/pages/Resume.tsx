import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { Project } from '../types';

const PROFILE_ID_KEY = 'career_agent_profile_id';

interface ProfileData {
  id: number;
  full_name: string;
  email: string;
  phone?: string;
  linkedin_url?: string;
  summary: string;
  raw_resume_text: string;
  interests?: string[];
  education?: Array<{ degree: string; institution: string; year: string }>;
  certifications?: Array<{ name: string; issuer?: string }>;
  created_at: string;
}

interface SkillData {
  id: number;
  name: string;
  category: string;
  proficiency?: string;
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

export function Resume() {
  const { profileId: authProfileId, setProfileId: setAuthProfileId } = useAuth();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [skills, setSkills] = useState<SkillData[]>([]);
  const [profileId, setProfileId] = useState<number | null>(authProfileId);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [project, setProject] = useState<Project>({ ...emptyProject });
  const [techInput, setTechInput] = useState('');
  const [editingSummary, setEditingSummary] = useState(false);
  const [summaryText, setSummaryText] = useState('');

  const [editingBasicInfo, setEditingBasicInfo] = useState(false);
  const [phone, setPhone] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');

  const [editingSkills, setEditingSkills] = useState(false);
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState('');
  const [editedSkills, setEditedSkills] = useState<SkillData[]>([]);

  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editingProject, setEditingProject] = useState<any>(null);
  const [editProjectTechInput, setEditProjectTechInput] = useState('');

  const [editingCerts, setEditingCerts] = useState(false);
  const [certs, setCerts] = useState<Array<{ name: string; issuer?: string }>>([]);
  const [newCertName, setNewCertName] = useState('');
  const [newCertIssuer, setNewCertIssuer] = useState('');

  const [editingInterests, setEditingInterests] = useState(false);
  const [interestsText, setInterestsText] = useState('');

  const loadProfile = async (id: number) => {
    try {
      const res = await api.profile.get(id);
      const data = res.data as any;
      if (data.profile) {
        setProfile(data.profile);
        setSummaryText(data.profile.summary || '');
        setPhone(data.profile.phone || '');
        setLinkedinUrl(data.profile.linkedin_url || '');
        setInterestsText((data.profile.interests || []).join(', '));
        setCerts(data.profile.certifications || []);
      }
      setProjects(data.projects || []);
      setSkills(data.skills || []);
    } catch {
      localStorage.removeItem(PROFILE_ID_KEY);
      setProfileId(null);
    }
  };

  useEffect(() => {
    if (authProfileId) {
      setProfileId(authProfileId);
      loadProfile(authProfileId).finally(() => setLoading(false));
    } else {
      const stored = localStorage.getItem(PROFILE_ID_KEY);
      if (stored) {
        const id = Number(stored);
        setProfileId(id);
        setAuthProfileId(id);
        loadProfile(id).finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    }
  }, [authProfileId]);

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
      setAuthProfileId(newProfileId);
      await loadProfile(newProfileId);
    } catch {
      alert('Failed to upload resume');
    } finally {
      setUploading(false);
    }
  };

  const handleSaveSummary = async () => {
    if (!profileId) return;
    try {
      await api.profile.update(profileId, { summary: summaryText } as any);
      setProfile(prev => prev ? { ...prev, summary: summaryText } : prev);
      setEditingSummary(false);
    } catch {
      alert('Failed to save summary');
    }
  };

  const handleSaveBasicInfo = async () => {
    if (!profileId) return;
    try {
      await api.profile.update(profileId, { phone, linkedin_url: linkedinUrl } as any);
      setProfile(prev => prev ? { ...prev, phone, linkedin_url: linkedinUrl } : prev);
      setEditingBasicInfo(false);
    } catch {
      alert('Failed to save basic info');
    }
  };

  const handleSaveSkills = async () => {
    if (!profileId) return;
    try {
      await api.profile.updateSkills(profileId, editedSkills.map(s => ({ name: s.name, category: s.category, proficiency: s.proficiency })));
      setSkills(editedSkills);
      setEditingSkills(false);
    } catch {
      alert('Failed to save skills');
    }
  };

  const handleAddSkill = () => {
    if (!newSkillName.trim()) return;
    const newSkill: SkillData = { id: Date.now(), name: newSkillName.trim(), category: newSkillCategory.trim() || 'General', proficiency: 'Intermediate' };
    setEditedSkills(prev => [...prev, newSkill]);
    setNewSkillName('');
    setNewSkillCategory('');
  };

  const handleDeleteSkill = (id: number) => {
    setEditedSkills(prev => prev.filter(s => s.id !== id));
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

  const handleUpdateProject = async (projectId: number) => {
    if (!profileId || !editingProject) return;
    try {
      await api.profile.updateProject(profileId, projectId, editingProject);
      setEditingProjectId(null);
      setEditingProject(null);
      await loadProfile(profileId);
    } catch {
      alert('Failed to update project');
    }
  };

  const handleDeleteProject = async (projectId: number) => {
    if (!profileId) return;
    if (!confirm('Delete this project?')) return;
    try {
      await api.profile.deleteProject(profileId, projectId);
      await loadProfile(profileId);
    } catch {
      alert('Failed to delete project');
    }
  };

  const addTech = () => {
    if (techInput.trim() && !project.technologies.includes(techInput.trim())) {
      setProject({ ...project, technologies: [...project.technologies, techInput.trim()] });
      setTechInput('');
    }
  };

  const addEditTech = () => {
    if (editProjectTechInput.trim() && !editingProject.technologies.includes(editProjectTechInput.trim())) {
      setEditingProject({ ...editingProject, technologies: [...editingProject.technologies, editProjectTechInput.trim()] });
      setEditProjectTechInput('');
    }
  };

  const handleSaveCerts = async () => {
    if (!profileId) return;
    try {
      await api.profile.update(profileId, { certifications: certs } as any);
      setProfile(prev => prev ? { ...prev, certifications: certs } : prev);
      setEditingCerts(false);
    } catch {
      alert('Failed to save certifications');
    }
  };

  const handleSaveInterests = async () => {
    if (!profileId) return;
    const interestsArr = interestsText.split(',').map(s => s.trim()).filter(Boolean);
    try {
      await api.profile.update(profileId, { interests: interestsArr } as any);
      setProfile(prev => prev ? { ...prev, interests: interestsArr } : prev);
      setEditingInterests(false);
    } catch {
      alert('Failed to save interests');
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
      <h1 className="text-2xl font-bold">Resume</h1>

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

      {/* Basic Info Section */}
      {profile && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Basic Info</h2>
            <button onClick={() => { setEditingBasicInfo(!editingBasicInfo); setPhone(profile.phone || ''); setLinkedinUrl(profile.linkedin_url || ''); }} className="text-sm text-blue-600 hover:text-blue-700">
              {editingBasicInfo ? 'Cancel' : 'Edit'}
            </button>
          </div>
          {editingBasicInfo ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Phone</label>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} className="input-field w-full" placeholder="+1 555-0100" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">LinkedIn URL</label>
                <input value={linkedinUrl} onChange={(e) => setLinkedinUrl(e.target.value)} className="input-field w-full" placeholder="https://linkedin.com/in/yourname" />
              </div>
              <button onClick={handleSaveBasicInfo} className="btn-primary text-sm">Save</button>
            </div>
          ) : (
            <div className="space-y-2 text-sm">
              <p><span className="font-medium">Name:</span> {profile.full_name}</p>
              <p><span className="font-medium">Email:</span> {profile.email}</p>
              <p><span className="font-medium">Phone:</span> {profile.phone || '—'}</p>
              <p><span className="font-medium">LinkedIn:</span> {profile.linkedin_url || '—'}</p>
            </div>
          )}
        </div>
      )}

      {/* Summary Section */}
      {profile && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Profile Summary</h2>
            <button onClick={() => { setEditingSummary(!editingSummary); setSummaryText(profile.summary || ''); }} className="text-sm text-blue-600 hover:text-blue-700">
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
              <button onClick={handleSaveSummary} className="btn-primary text-sm mt-2">Save Summary</button>
            </div>
          ) : (
            <p className="text-gray-700 whitespace-pre-wrap">{profile.summary || 'No summary yet.'}</p>
          )}
        </div>
      )}

      {/* Skills Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Skills ({skills.length})</h2>
          <button
            onClick={() => {
              if (editingSkills) {
                setEditingSkills(false);
              } else {
                setEditedSkills([...skills]);
                setEditingSkills(true);
              }
            }}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {editingSkills ? 'Cancel' : 'Edit'}
          </button>
        </div>
        {editingSkills ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {editedSkills.map((skill) => (
                <span key={skill.id} className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm flex items-center gap-1">
                  {skill.name}
                  {skill.category && <span className="text-blue-500 ml-1">({skill.category})</span>}
                  <button onClick={() => handleDeleteSkill(skill.id)} className="ml-1 text-red-500 hover:text-red-700 font-bold">×</button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input value={newSkillName} onChange={(e) => setNewSkillName(e.target.value)} className="input-field flex-1" placeholder="Skill name" onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())} />
              <input value={newSkillCategory} onChange={(e) => setNewSkillCategory(e.target.value)} className="input-field flex-1" placeholder="Category" onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())} />
              <button onClick={handleAddSkill} className="btn-secondary text-sm">Add</button>
            </div>
            <button onClick={handleSaveSkills} className="btn-primary text-sm">Save Skills</button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {skills.map((skill) => (
              <span key={skill.id} className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm">
                {skill.name}
                {skill.category && <span className="text-blue-500 ml-1">({skill.category})</span>}
              </span>
            ))}
          </div>
        )}
      </div>

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
            {projects.map((p) => (
              editingProjectId === p.id ? (
                <div key={p.id} className="bg-yellow-50 rounded-lg p-4 border border-yellow-200 space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Title</label>
                      <input value={editingProject.title} onChange={(e) => setEditingProject({ ...editingProject, title: e.target.value })} className="input-field w-full" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Role</label>
                      <input value={editingProject.role} onChange={(e) => setEditingProject({ ...editingProject, role: e.target.value })} className="input-field w-full" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Description</label>
                    <textarea value={editingProject.description} onChange={(e) => setEditingProject({ ...editingProject, description: e.target.value })} className="input-field w-full" rows={2} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Impact</label>
                    <input value={editingProject.impact} onChange={(e) => setEditingProject({ ...editingProject, impact: e.target.value })} className="input-field w-full" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Technologies</label>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {editingProject.technologies.map((tech: string) => (
                        <span key={tech} className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm flex items-center gap-1">
                          {tech}
                          <button type="button" onClick={() => setEditingProject({ ...editingProject, technologies: editingProject.technologies.filter((t: string) => t !== tech) })}>×</button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2 mt-2">
                      <input value={editProjectTechInput} onChange={(e) => setEditProjectTechInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addEditTech())} className="input-field flex-1" placeholder="Add technology" />
                      <button type="button" onClick={addEditTech} className="btn-secondary text-sm">Add</button>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleUpdateProject(p.id)} className="btn-primary text-sm">Save</button>
                    <button onClick={() => { setEditingProjectId(null); setEditingProject(null); }} className="btn-secondary text-sm">Cancel</button>
                  </div>
                </div>
              ) : (
                <div key={p.id} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium">{p.title}</h3>
                      {p.role && <p className="text-sm text-gray-600">{p.role}</p>}
                      {p.description && <p className="text-sm text-gray-700 mt-1">{p.description}</p>}
                      {p.technologies && <p className="text-xs text-gray-500 mt-1">Tech: {p.technologies}</p>}
                      {p.impact && <p className="text-sm text-green-700 mt-1">Impact: {p.impact}</p>}
                    </div>
                    <div className="flex gap-2 ml-2">
                      <button onClick={() => { setEditingProjectId(p.id); setEditingProject({ ...p, technologies: Array.isArray(p.technologies) ? p.technologies : [] }); setEditProjectTechInput(''); }} className="text-sm text-blue-600 hover:text-blue-700">Edit</button>
                      <button onClick={() => handleDeleteProject(p.id)} className="text-sm text-red-600 hover:text-red-700">Delete</button>
                    </div>
                  </div>
                </div>
              )
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

      {/* Certifications Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Certifications ({certs.length})</h2>
          <button onClick={() => setEditingCerts(!editingCerts)} className="text-sm text-blue-600 hover:text-blue-700">
            {editingCerts ? 'Cancel' : 'Edit'}
          </button>
        </div>
        {editingCerts ? (
          <div className="space-y-4">
            {certs.map((cert, i) => (
              <div key={i} className="flex items-center gap-2">
                <input value={cert.name} onChange={(e) => { const updated = [...certs]; updated[i] = { ...updated[i], name: e.target.value }; setCerts(updated); }} className="input-field flex-1" placeholder="Certification name" />
                <input value={cert.issuer || ''} onChange={(e) => { const updated = [...certs]; updated[i] = { ...updated[i], issuer: e.target.value }; setCerts(updated); }} className="input-field flex-1" placeholder="Issuer" />
                <button onClick={() => setCerts(certs.filter((_, idx) => idx !== i))} className="text-red-500 hover:text-red-700 font-bold">×</button>
              </div>
            ))}
            <div className="flex gap-2">
              <input value={newCertName} onChange={(e) => setNewCertName(e.target.value)} className="input-field flex-1" placeholder="New certification name" />
              <input value={newCertIssuer} onChange={(e) => setNewCertIssuer(e.target.value)} className="input-field flex-1" placeholder="Issuer" />
              <button onClick={() => { if (newCertName.trim()) { setCerts(prev => [...prev, { name: newCertName.trim(), issuer: newCertIssuer.trim() || undefined }]); setNewCertName(''); setNewCertIssuer(''); } }} className="btn-secondary text-sm">Add</button>
            </div>
            <button onClick={handleSaveCerts} className="btn-primary text-sm">Save Certifications</button>
          </div>
        ) : (
          <div className="space-y-2">
            {certs.length === 0 ? (
              <p className="text-gray-500 text-sm">No certifications added yet.</p>
            ) : (
              certs.map((cert, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="font-medium">{cert.name}</span>
                  {cert.issuer && <span className="text-gray-500">— {cert.issuer}</span>}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Interests Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Interests</h2>
          <button onClick={() => { setEditingInterests(!editingInterests); setInterestsText((profile?.interests || []).join(', ')); }} className="text-sm text-blue-600 hover:text-blue-700">
            {editingInterests ? 'Cancel' : 'Edit'}
          </button>
        </div>
        {editingInterests ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Interests (comma-separated)</label>
              <input value={interestsText} onChange={(e) => setInterestsText(e.target.value)} className="input-field w-full" placeholder="AI, Cloud Architecture, DevOps, Leadership" />
            </div>
            <button onClick={handleSaveInterests} className="btn-primary text-sm">Save Interests</button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {(profile?.interests || []).length === 0 ? (
              <p className="text-gray-500 text-sm">No interests added yet.</p>
            ) : (
              (profile?.interests || []).map((interest, i) => (
                <span key={i} className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm">{interest}</span>
              ))
            )}
          </div>
        )}
      </div>

      {/* Education Section */}
      {profile?.education && profile.education.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Education</h2>
          <div className="space-y-3">
            {profile.education.map((edu, i) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3">
                <p className="font-medium">{edu.degree}</p>
                <p className="text-sm text-gray-600">{edu.institution}</p>
                <p className="text-sm text-gray-500">{edu.year}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
