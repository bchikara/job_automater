#!/usr/bin/env python3
"""
ATS-Optimized Cover Letter Generator
Creates compelling cover letters with keyword optimization
"""

import os
import logging
import google.generativeai as genai
import json
from typing import Dict, List
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from utils import decode_html_to_text
    import config
    from ats_scorer import ATSScorer
except ImportError as e:
    logging.critical(f"Error importing modules: {e}", exc_info=True)
    raise SystemExit(f"Critical import error: {e}")

logger = logging.getLogger(__name__)

# Configure Gemini
gemini_model = None
try:
    if hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY:
        genai.configure(api_key=config.GEMINI_API_KEY)
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",
        }
        gemini_model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL_NAME,
            generation_config=generation_config
        )
        logger.info("Gemini API configured for cover letter generation")
except Exception as e:
    logger.error(f"Failed to configure Gemini: {e}")


class CoverLetterTailor:
    """
    Generate ATS-optimized cover letters with keyword integration
    """

    TARGET_ATS_SCORE = 85
    MAX_REFINEMENT_ITERATIONS = 4

    def __init__(self):
        self.ats_scorer = ATSScorer()
        self.base_experience = []
        self.base_projects = []

    def load_base_data(self):
        """Load base resume data for reference"""
        base_resume_path = os.path.join(PROJECT_ROOT, 'base_resume.json')
        try:
            with open(base_resume_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.base_experience = data.get('experience', [])
                self.base_projects = data.get('projects', [])
                logger.info("Base resume data loaded for cover letter generation")
        except Exception as e:
            logger.error(f"Failed to load base resume: {e}")

    def create_cover_letter_prompt(self, job_data: Dict, jd_keywords: Dict,
                                   previous_score: int = 0,
                                   suggestions: List = None) -> str:
        """
        Create prompt for generating ATS-optimized cover letter
        """
        job_description = decode_html_to_text(job_data.get('description', ''))
        job_title = job_data.get('job_title', 'the position')
        company_name = job_data.get('company_name', 'your company')

        must_have = jd_keywords.get('must_have', [])
        preferred = jd_keywords.get('preferred', [])
        tech_keywords = jd_keywords.get('technologies', [])

        # Build score feedback
        score_feedback = ""
        if previous_score > 0:
            score_feedback = f"""
⚠️ PREVIOUS ATTEMPT SCORE: {previous_score}/100 - BELOW TARGET OF 85!
YOU MUST IMPROVE THIS SCORE by adding more relevant keywords naturally.
"""

        # Build suggestions
        suggestions_text = ""
        if suggestions:
            suggestions_text = f"""
SPECIFIC IMPROVEMENTS NEEDED:
{chr(10).join('- ' + s for s in suggestions[:5])}
YOU MUST address these in your cover letter!
"""

        prompt = f"""You are an EXPERT cover letter writer and ATS optimization specialist. Your job is to create a COMPELLING, KEYWORD-RICH cover letter that achieves an ATS score of 85+ while remaining natural and professional.

{score_feedback}{suggestions_text}

═══════════════════════════════════════════════════════════════
I. TARGET JOB INFORMATION
═══════════════════════════════════════════════════════════════
Job Title: {job_title}
Company: {company_name}

MUST-HAVE Keywords (MUST appear in cover letter): {', '.join(must_have[:15])}
PREFERRED Keywords: {', '.join(preferred[:10])}
TECHNICAL Keywords: {', '.join(tech_keywords[:15])}

Full Job Description:
{job_description[:3000]}

═══════════════════════════════════════════════════════════════
II. CANDIDATE'S BACKGROUND
═══════════════════════════════════════════════════════════════
Experience: {json.dumps(self.base_experience[:3], indent=2)}
Projects: {json.dumps(self.base_projects[:2], indent=2)}

═══════════════════════════════════════════════════════════════
III. CRITICAL COVER LETTER REQUIREMENTS
═══════════════════════════════════════════════════════════════

🔴 RULE #1: KEYWORD INTEGRATION (MOST IMPORTANT!)
- MUST naturally integrate ALL must-have keywords into the cover letter
- MUST use exact terminology from job description
- Each paragraph should contain 3-5 relevant keywords from the job posting
- Keywords must flow naturally - don't stuff them awkwardly
- Use keywords in context of achievements and qualifications

🔴 RULE #2: STRUCTURE
The cover letter must have EXACTLY 4 PARAGRAPHS:

Paragraph 1 (Opening - 3-4 sentences):
- Express genuine interest in {job_title} role at {company_name}
- Mention 2-3 must-have keywords naturally
- State years of experience or key qualification that matches the role
- Hook: Why you're excited about THIS specific role

Paragraph 2 (Relevant Experience - 4-5 sentences):
- Highlight 2-3 specific achievements from your experience
- MUST include quantified results (percentages, numbers, scale)
- MUST incorporate 4-6 keywords from the job description
- Connect your experience directly to job requirements
- Use action verbs from the job posting

Paragraph 3 (Technical Skills & Projects - 3-4 sentences):
- Showcase technical expertise relevant to the role
- Mention 3-5 technical keywords from the job description
- Reference specific projects or implementations
- Demonstrate understanding of the technical stack they use
- Show passion for the technology/domain

Paragraph 4 (Closing - 2-3 sentences):
- Express enthusiasm for contributing to the company
- Mention interest in discussing how you can add value
- Professional and confident tone
- Include 1-2 final keywords naturally

🔴 RULE #3: TONE & STYLE
- Professional but personable
- Confident without being arrogant
- Specific (use numbers, technologies, achievements)
- NO clichés like "I'm a team player" or "I think outside the box"
- Focus on WHAT you can do for THEM, not what they can do for you

🔴 RULE #4: LENGTH
- Each paragraph: 3-5 sentences
- Total length: 250-350 words
- Must fit on ONE page when formatted

🔴 RULE #5: KEYWORD DENSITY
- Target: 2-4% of total words should be job-relevant keywords
- No keyword used more than 2 times
- Vary phrasing (e.g., "developed" → "engineered", "built", "created")

═══════════════════════════════════════════════════════════════
IV. OUTPUT FORMAT (STRICT JSON)
═══════════════════════════════════════════════════════════════

Return ONLY valid JSON:

{{
  "paragraphs": [
    "Paragraph 1: Opening with keywords...",
    "Paragraph 2: Experience with achievements and keywords...",
    "Paragraph 3: Technical skills and projects with keywords...",
    "Paragraph 4: Closing with enthusiasm and keywords..."
  ],
  "keyword_usage": {{
    "must_have_used": ["keyword1", "keyword2", ...],
    "preferred_used": ["keyword3", "keyword4", ...],
    "technical_used": ["tech1", "tech2", ...]
  }},
  "metrics": {{
    "total_words": 320,
    "keyword_count": 45,
    "density_percentage": "3.1%"
  }}
}}

EXAMPLE OF GOOD COVER LETTER OPENING:
"I am writing to express my strong interest in the Senior Full Stack Engineer position at TechCorp. With over 5 years of experience architecting scalable microservices using React, Node.js, and AWS, I have consistently delivered solutions that improved system performance by 40% and reduced deployment time by 60%. Your emphasis on building cloud-native applications and implementing CI/CD pipelines resonates deeply with my expertise and passion for modern software development."

(Notice: Natural flow, specific numbers, multiple keywords integrated smoothly)

BAD EXAMPLE:
"I am interested in the position. I have experience with React and Node.js. I am a hard worker and team player. I would be a great fit for your company."

(Notice: Generic, no specifics, no keywords, no achievements)

FINAL CHECKLIST:
✓ All must-have keywords included naturally
✓ 3-5 keywords per paragraph
✓ Quantified achievements included
✓ Specific to THIS job and THIS company
✓ Professional tone, no clichés
✓ 4 paragraphs, 250-350 words total
✓ Keywords used max 2 times each

Remember: ATS systems scan for keywords. Generic cover letters score LOW. Job-specific, keyword-rich cover letters score HIGH. Your goal is 85+ ATS score while maintaining natural, professional writing.
"""

        return prompt

    def generate_with_refinement(self, job_data: Dict) -> Dict:
        """
        Generate cover letter with iterative refinement until ATS >= 85
        """
        self.load_base_data()

        # Extract keywords from JD
        jd_keywords = self.ats_scorer.extract_keywords_from_jd(job_data)
        logger.info(f"Extracted {sum(len(v) for v in jd_keywords.values())} keywords for cover letter")

        best_cover_letter = None
        best_score = 0
        previous_suggestions = []

        for iteration in range(self.MAX_REFINEMENT_ITERATIONS):
            logger.info(f"\n{'='*60}")
            logger.info(f"COVER LETTER ITERATION {iteration + 1}/{self.MAX_REFINEMENT_ITERATIONS}")
            logger.info(f"{'='*60}")

            # Create prompt
            prompt = self.create_cover_letter_prompt(
                job_data, jd_keywords,
                previous_score=best_score,
                suggestions=previous_suggestions
            )

            # Call Gemini
            try:
                logger.info("Calling Gemini API for cover letter generation...")
                response = gemini_model.generate_content(prompt)

                # Parse response
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:-3].strip()
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:-3].strip()

                cover_letter_data = json.loads(raw_text)

                if 'paragraphs' not in cover_letter_data:
                    raise ValueError("Missing 'paragraphs' in response")

                logger.info("✓ Successfully generated cover letter")

                # Score this version
                # Combine paragraphs into a single text for scoring
                cover_letter_text = "\n\n".join(cover_letter_data['paragraphs'])

                # Create a mock resume structure for scoring
                mock_resume = {
                    'experience': [{'description': [cover_letter_text]}],
                    'projects': [],
                    'skills': {}
                }

                score_result = self.ats_scorer.score_resume(mock_resume, job_data)
                current_score = score_result['total_score']
                logger.info(f"Cover Letter ATS Score: {current_score}/100")

                # Capture suggestions
                previous_suggestions = score_result.get('suggestions', [])

                # Update best
                if current_score > best_score:
                    best_score = current_score
                    best_cover_letter = cover_letter_data
                    logger.info(f"✓ New best score: {best_score}")

                # Check if target met
                if current_score >= self.TARGET_ATS_SCORE:
                    logger.info(f"🎉 COVER LETTER TARGET ACHIEVED! Score: {current_score}/100")
                    break

                # Log feedback
                if iteration < self.MAX_REFINEMENT_ITERATIONS - 1:
                    logger.info(f"⚠️  Refinement needed. Suggestions:")
                    for suggestion in previous_suggestions:
                        logger.info(f"  - {suggestion}")

            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                if 'response' in locals():
                    logger.error(f"Raw response: {response.text[:500]}")
                continue

            except Exception as e:
                logger.error(f"Cover letter generation error: {e}", exc_info=True)
                continue

        # Return best result
        if best_cover_letter:
            logger.info(f"FINAL COVER LETTER SCORE: {best_score}/100")
            return {
                'paragraphs': best_cover_letter['paragraphs'],
                'ats_score': best_score,
                'keyword_usage': best_cover_letter.get('keyword_usage', {})
            }
        else:
            logger.error("All cover letter generation attempts failed")
            return None


def generate_ats_optimized_cover_letter(job_data: Dict) -> Dict:
    """
    Main entry point for ATS-optimized cover letter generation
    """
    tailor = CoverLetterTailor()
    return tailor.generate_with_refinement(job_data)


# Test
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    test_job = {
        'job_title': 'Senior Full Stack Engineer',
        'company_name': 'Tech Innovations Inc',
        'description': '''
        We're seeking a Senior Full Stack Engineer with strong experience in React, Node.js, and AWS.
        You'll architect scalable microservices, build responsive frontends, and deploy to cloud infrastructure.

        Must have: React, Node.js, AWS, Docker, MongoDB
        Preferred: TypeScript, Kubernetes, GraphQL
        ''',
        'skills': [
            {'skill': 'React', 'score': 3, 'type': 'hard_skill'},
            {'skill': 'Node.js', 'score': 3, 'type': 'hard_skill'},
            {'skill': 'AWS', 'score': 3, 'type': 'hard_skill'},
        ],
        'qualifications': {
            'mustHave': [
                'React', 'Node.js', 'AWS', 'Docker', 'MongoDB'
            ],
            'preferredHave': ['TypeScript', 'Kubernetes', 'GraphQL']
        }
    }

    result = generate_ats_optimized_cover_letter(test_job)

    if result:
        print(f"\n{'='*60}")
        print("✓ Cover letter generated successfully!")
        print(f"ATS Score: {result['ats_score']}/100")
        print(f"{'='*60}")
        print("\nGenerated Cover Letter:\n")
        for i, para in enumerate(result['paragraphs'], 1):
            print(f"Paragraph {i}:")
            print(para)
            print()
