from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.llm_factory import get_llm


class ResumeAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.3)
        return self._llm

    def generate_resume(
        self, career_chunks: list, job_chunks: list, job_data: dict
    ) -> str:
        career_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in career_chunks]
        )
        job_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in job_chunks]
        )

        prompt = f"""You are an expert resume writer specializing in senior IT executive resumes.

Generate a tailored resume for the following candidate, optimized for the specific job opportunity.

CANDIDATE CAREER PROFILE (retrieved context):
---
{career_context}
---

JOB REQUIREMENTS (retrieved context):
---
{job_context}
---

JOB DETAILS:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company', 'N/A')}
- Seniority Level: {job_data.get('seniority_level', 'N/A')}

INSTRUCTIONS:
1. Use ONLY the information provided in the career context chunks. Do not fabricate or invent any experience, achievements, skills, or credentials.
2. Tailor the resume to emphasize experience and skills most relevant to this specific job.
3. Align the candidate's accomplishments with the job requirements using language from both contexts.
4. Highlight leadership experience, strategic impact, and quantifiable achievements.
5. Use strong action verbs and executive-level language appropriate for senior IT leaders.
6. Structure the resume with clear sections: Professional Summary, Key Experience, Technical Competencies, Education & Certifications.
7. If specific details are missing from the career context, omit those sections rather than making up information.

Generate the complete tailored resume text:"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    def generate_cover_letter(
        self, career_chunks: list, job_chunks: list, job_data: dict
    ) -> str:
        career_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in career_chunks]
        )
        job_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in job_chunks]
        )

        prompt = f"""You are an expert cover letter writer specializing in executive-level applications for senior IT leadership roles.

Generate a tailored cover letter for the following candidate, optimized for the specific job opportunity.

CANDIDATE CAREER PROFILE (retrieved context):
---
{career_context}
---

JOB REQUIREMENTS (retrieved context):
---
{job_context}
---

JOB DETAILS:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company', 'N/A')}
- Seniority Level: {job_data.get('seniority_level', 'N/A')}

INSTRUCTIONS:
1. Use ONLY the information provided in the career context chunks. Do not fabricate or invent any experience, achievements, or credentials.
2. Address the cover letter to the hiring manager at {job_data.get('company', 'the company')}.
3. Open with a compelling hook that connects the candidate's experience to this specific role.
4. Highlight 3-4 key qualifications from the career context that directly match the job requirements.
5. Demonstrate knowledge of the company and role by referencing details from the job context.
6. Close with a strong call to action that conveys executive confidence.
7. Maintain a professional, authoritative tone appropriate for a senior IT leader.
8. Keep the letter to one page (approximately 350-450 words).

Generate the complete tailored cover letter:"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
