"""
Tests for bug fixes:
1. Issue 2: Resume not displaying after upload (formatted_resume_html missing)
2. Issue 1: Resume formatting and industry standards
3. Issue 3: Generated documents too generic (better customization)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.profile_service import ProfileService
from app.services.job_service import JobService
from app.services.document_service import _parse_resume_text
from app.db.models import CareerProfile, JobPosting, Project, Skill, Certification
from app.agents.resume_agent import ResumeAgent


class TestIssue2ResomeDisplayAfterUpload:
    """Test Issue 2: Resume not displaying in viewer after upload"""
    
    @pytest.mark.asyncio
    async def test_get_profile_returns_formatted_resume_html(self, db_session):
        """
        Issue 2 Fix: get_profile() should return formatted_resume_html
        so the frontend can display the formatted resume immediately after upload
        """
        # Create a test profile with formatted HTML
        profile = CareerProfile(
            full_name="John Doe",
            email="john@example.com",
            raw_resume_text="My resume text",
            formatted_resume_html="<html><body>John Doe</body></html>",
        )
        db_session.add(profile)
        await db_session.flush()
        
        # Get the profile
        service = ProfileService()
        result = await service.get_profile(profile.id, db_session)
        
        # Verify formatted_resume_html is in the response
        assert "profile" in result
        assert "formatted_resume_html" in result["profile"]
        assert result["profile"]["formatted_resume_html"] == "<html><body>John Doe</body></html>"
        assert result["profile"]["raw_resume_text"] == "My resume text"

    @pytest.mark.asyncio
    async def test_upload_resume_response_includes_html(self, db_session):
        """
        Issue 2 Fix: upload_resume() response should include formatted_resume_html
        for immediate frontend display without needing a second GET request
        """
        with patch("app.services.profile_service.ResumeParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser_class.return_value = mock_parser
            
            # Mock parser responses
            mock_parser.parse.return_value = "John Doe\njohn@example.com\nSummary text"
            mock_parser.extract_sections.return_value = {"contact_info": "John Doe\njohn@example.com"}
            
            with patch("app.services.profile_service.CareerExpander") as mock_expander_class:
                mock_expander = MagicMock()
                mock_expander_class.return_value = mock_expander
                mock_expander.expand_profile.return_value = {
                    "summary": "Senior IT Leader",
                    "detailed_projects": [],
                    "skills_by_category": {"Leadership": ["Project Management"]},
                }
                
                with patch("app.services.profile_service.render_resume_html") as mock_render:
                    mock_render.return_value = "<html><body>Formatted</body></html>"
                    
                    service = ProfileService()
                    result = await service.upload_resume(
                        "dummy_path.pdf",
                        db_session,
                        user_id=None
                    )
                    
                    # Verify response includes both text and HTML
                    assert "profile_id" in result
                    assert "raw_resume_text" in result
                    assert "formatted_resume_html" in result
                    assert result["formatted_resume_html"] == "<html><body>Formatted</body></html>"


class TestIssue1ResumeFormatting:
    """Test Issue 1: Resume formatting matches industry standards"""
    
    def test_parse_resume_with_clear_section_headers(self):
        """
        Issue 1 Fix: Parser should handle clear section headers like 
        'PROFESSIONAL SUMMARY', 'PROFESSIONAL EXPERIENCE', etc.
        """
        resume_text = """
PROFESSIONAL SUMMARY
Senior IT Leader with 15 years of experience

PROFESSIONAL EXPERIENCE
CTO | Acme Corp | 2020-Present
- Led digital transformation saving $2M annually
- Built engineering team from 5 to 50 people
- Implemented cloud-first strategy reducing costs by 40%

VP Engineering | TechCorp | 2015-2020
- Delivered 10+ major product releases
- Improved deployment frequency by 300%

KEY SKILLS
Cloud Architecture: AWS, Azure, GCP
Leadership: Team Building, Mentoring, Strategic Planning

EDUCATION & CERTIFICATIONS
MBA, Harvard Business School
AWS Solutions Architect Certification
"""
        
        parsed = _parse_resume_text(resume_text)
        
        # Verify sections are properly parsed
        assert parsed["summary"] and "Senior IT Leader" in parsed["summary"]
        assert len(parsed["experience"]) >= 2
        assert any("CTO" in exp.get("title", "") for exp in parsed["experience"])
        assert "Cloud Architecture" in parsed["skills"]
        assert len(parsed["certifications"]) > 0

    def test_parse_resume_extracts_quantified_achievements(self):
        """
        Issue 1 Fix: Parser should properly extract quantified achievements
        that were emphasized in the prompt improvements
        """
        resume_text = """
PROFESSIONAL EXPERIENCE
Director of Engineering | Global Tech | 2018-Present
- Reduced deployment time from 2 hours to 15 minutes (87.5% improvement)
- Led 25-person team to deliver 5 major products
- Saved $1.2M in infrastructure costs through optimization
"""
        
        parsed = _parse_resume_text(resume_text)
        
        assert len(parsed["experience"]) > 0
        exp = parsed["experience"][0]
        assert "Director of Engineering" in exp["title"]
        assert len(exp["bullets"]) >= 3
        # Verify quantified metrics are preserved
        assert any("87.5%" in bullet for bullet in exp["bullets"])
        assert any("$1.2M" in bullet for bullet in exp["bullets"])

    def test_resume_agent_prompt_includes_structure_guidance(self):
        """
        Issue 1 Fix: The improved resume_agent prompt should include 
        explicit guidance for structured, parseable output
        """
        with patch("app.agents.resume_agent.get_llm") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm_factory.return_value = mock_llm
            mock_response = MagicMock()
            mock_response.content = "PROFESSIONAL SUMMARY\nText here"
            mock_llm.invoke.return_value = mock_response
            
            agent = ResumeAgent()
            agent.generate_resume(
                career_chunks=[{"content": "CTO with 15 years"}],
                job_chunks=[{"content": "Seeking cloud expert"}],
                job_data={"title": "CTO", "company": "Acme", "seniority_level": "Executive"}
            )
            
            call_args = mock_llm.invoke.call_args
            prompt = call_args[0][0][0].content
            
            # Verify improved prompt includes structure guidance
            assert "PROFESSIONAL SUMMARY" in prompt.upper()
            assert "PROFESSIONAL EXPERIENCE" in prompt.upper()
            assert "quantified" in prompt.lower() or "quantif" in prompt.lower()
            assert "ATS" in prompt or "parseable" in prompt.lower()


class TestIssue3DocumentCustomization:
    """Test Issue 3: Generated documents too generic"""
    
    @pytest.mark.asyncio
    async def test_job_service_uses_targeted_rag_query(self, db_session):
        """
        Issue 3 Fix: generate_application_materials should query for
        most relevant chunks instead of getting all chunks
        """
        # Create test data
        job = JobPosting(
            title="Senior Engineering Manager",
            company="TechCorp",
            description="Looking for experienced engineering leader",
            requirements_text="AWS, team leadership, microservices",
            seniority_level="Senior",
        )
        db_session.add(job)
        await db_session.flush()
        
        profile = CareerProfile(
            full_name="Jane Doe",
            email="jane@example.com",
            raw_resume_text="My resume",
            summary="Engineering leader",
        )
        profile.user_id = None
        db_session.add(profile)
        await db_session.flush()
        
        with patch.object(JobService, "career_rag") as mock_career_rag, \
             patch.object(JobService, "job_rag") as mock_job_rag, \
             patch.object(JobService, "resume_agent") as mock_resume_agent, \
             patch("app.services.job_service.render_resume_html") as mock_render_html, \
             patch("app.services.job_service.render_cover_letter_html") as mock_render_letter:
            
            # Mock the query to return targeted chunks (not all)
            mock_career_rag.query.return_value = [
                (MagicMock(page_content="Relevant achievement text"), 0.95),
                (MagicMock(page_content="Another relevant project"), 0.87),
            ]
            mock_career_rag.get_all_chunks.return_value = [
                {"content": "Generic filler", "metadata": {"type": "skill"}},
            ]
            
            mock_job_rag.query.return_value = [
                (MagicMock(page_content="AWS requirement"), 0.92),
            ]
            
            mock_resume_agent.generate_resume.return_value = "Generated resume"
            mock_resume_agent.generate_cover_letter.return_value = "Generated cover letter"
            mock_render_html.return_value = "<html>Resume</html>"
            mock_render_letter.return_value = "<html>Letter</html>"
            
            service = JobService()
            result = await service.generate_application_materials(job.id, profile.id, db_session)
            
            # Verify career_rag.query was called (targeted search)
            mock_career_rag.query.assert_called()
            
            # Verify job_rag.query was called with job requirements
            mock_job_rag.query.assert_called()
            
            # Verify targeted chunks were used in generation
            call_args = mock_resume_agent.generate_resume.call_args
            career_chunks = call_args[0][0]  # First argument
            
            # Should include query results (targeted chunks)
            assert len(career_chunks) >= 2


    def test_resume_agent_prompt_emphasizes_customization(self):
        """
        Issue 3 Fix: Enhanced prompts should specifically request
        extraction of quantified achievements and specific examples
        """
        with patch("app.agents.resume_agent.get_llm") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm_factory.return_value = mock_llm
            mock_response = MagicMock()
            mock_response.content = "Generated resume"
            mock_llm.invoke.return_value = mock_response
            
            agent = ResumeAgent()
            agent.generate_resume(
                career_chunks=[{"content": "CTO with 15 years"}],
                job_chunks=[{"content": "Seeking cloud expert"}],
                job_data={"title": "CTO", "company": "Acme", "seniority_level": "Executive"}
            )
            
            call_args = mock_llm.invoke.call_args
            prompt = call_args[0][0][0].content
            
            # Verify improved customization instructions
            assert "QUANTIF" in prompt.upper()  # Quantified
            assert "SPECIFIC" in prompt.upper() or "TAILORED" in prompt.upper()
            assert "MATCH" in prompt.upper() or "ALIGN" in prompt.upper()
            assert "JOB REQUIREMENTS" in prompt.upper()

    def test_cover_letter_prompt_includes_specific_matching(self):
        """
        Issue 3 Fix: Cover letter should reference specific achievements
        and job requirements for better customization
        """
        with patch("app.agents.resume_agent.get_llm") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm_factory.return_value = mock_llm
            mock_response = MagicMock()
            mock_response.content = "Generated cover letter"
            mock_llm.invoke.return_value = mock_response
            
            agent = ResumeAgent()
            agent.generate_cover_letter(
                career_chunks=[{"content": "Led team transformation"}],
                job_chunks=[{"content": "Needs change management experience"}],
                job_data={"title": "VP Operations", "company": "Acme", "seniority_level": "Executive"}
            )
            
            call_args = mock_llm.invoke.call_args
            prompt = call_args[0][0][0].content
            
            # Verify prompt requests specific customization
            assert "SPECIFIC" in prompt.upper()
            assert "ACHIEVEMENT" in prompt.upper()
            assert "QUANTIF" in prompt.upper()
            assert "RESULT" in prompt.upper()
            assert "SITUATION, ACTION" in prompt.upper() or ("SITUATION" in prompt.upper() and "ACTION" in prompt.upper())
