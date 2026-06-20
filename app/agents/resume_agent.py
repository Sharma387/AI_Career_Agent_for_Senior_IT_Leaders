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

        prompt = f"""You are an expert resume writer specializing in senior IT executive resumes for industry standards.

Generate a tailored, ATS-optimized resume for the following candidate, optimized for the specific job opportunity.

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
1. Use ONLY information provided in the career context. Do NOT fabricate experience, achievements, or credentials.
2. Output a structured resume with CLEARLY MARKED SECTIONS using these exact headers:
   - PROFESSIONAL SUMMARY
   - PROFESSIONAL EXPERIENCE
   - KEY SKILLS
   - EDUCATION & CERTIFICATIONS
   - KEY PROJECTS (if applicable)

3. For each experience entry, include:
   - Job Title | Company | Dates
   - 3-4 bullet points with QUANTIFIED achievements (use numbers, %, $, metrics)
   - Focus on impact and leadership outcomes
   
4. For skills, group by category and list most relevant first.

5. Include measurable results: ROI improvements, cost savings, process efficiency, team size managed, revenue impact.

6. Use strong action verbs: Architected, Spearheaded, Optimized, Led, Delivered, Transformed, etc.

7. Tailor emphasis to match job requirements - prioritize skills and experiences that directly align.

8. Keep it ATS-friendly: no tables, no graphics, use standard fonts in descriptions only.

Generate the complete structured resume:"""

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

        prompt = f"""You are an expert cover letter writer specializing in compelling executive-level applications for senior IT leadership roles.

Generate a tailored, high-impact cover letter for the following candidate, customized for this specific job opportunity.

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
1. Use ONLY information from career context. Do NOT fabricate experience or credentials.
2. Write 3-4 compelling paragraphs (~350-450 words total, one page).
3. Opening paragraph: Include specific reference to the role/company + a hook about how candidate's experience directly addresses their key challenge.
4. Body paragraphs (2-3): Highlight 2-3 SPECIFIC achievements from career context that directly match job requirements.
   - Each achievement must include: situation, action taken, and QUANTIFIED result
   - Use exact terminology from job description
   - Show proven track record in similar challenges
5. Closing paragraph: Strong call to action, confidence, enthusiasm to contribute.
6. Tone: Professional, confident, executive-level, authentic (not generic).
7. Avoid: Generic statements, repetition of resume content, vague language.
8. Emphasize: Strategic thinking, proven results, leadership impact, relevant expertise.

Generate the complete cover letter (ready to use):"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
