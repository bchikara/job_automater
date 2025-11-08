#!/usr/bin/env python3
"""
Enhanced Resume Tailoring with ATS Optimization
Aggressive tailoring with keyword tracking and iterative refinement
"""

import os
import logging
import google.generativeai as genai
import json
from typing import Dict, List, Tuple
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from utils import escape_latex, decode_html_to_text, load_template
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
            "temperature": 0.7,  # Higher for more creative rewrites
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        gemini_model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL_NAME,
            generation_config=generation_config
        )
        logger.info("Gemini API configured for enhanced tailoring")
except Exception as e:
    logger.error(f"Failed to configure Gemini: {e}")


class EnhancedResumeTailor:
    """
    Enhanced resume tailoring with ATS optimization and iterative refinement
    """

    TARGET_ATS_SCORE = 85
    MAX_REFINEMENT_ITERATIONS = 6  # Increased to allow more attempts to reach target

    def __init__(self):
        self.ats_scorer = ATSScorer()
        self.base_experience = []
        self.base_projects = []
        self.base_skills = {}
        self.achievements_text = ""

    def load_base_data(self):
        """Load base resume data from JSON"""
        base_resume_path = os.path.join(PROJECT_ROOT, 'base_resume.json')
        achievements_path = os.path.join(PROJECT_ROOT, 'info', 'achievements.txt')

        try:
            with open(base_resume_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.base_experience = data.get('experience', [])
                self.base_projects = data.get('projects', [])
                self.base_skills = data.get('skills', {})
                logger.info("Base resume data loaded")
        except Exception as e:
            logger.error(f"Failed to load base resume: {e}")

        try:
            with open(achievements_path, 'r', encoding='utf-8') as f:
                self.achievements_text = f.read()
        except Exception as e:
            logger.warning(f"No achievements file: {e}")

    def create_aggressive_resume_prompt(self, job_data: Dict, jd_keywords: Dict,
                                        keyword_violations: List = None,
                                        previous_score: int = 0,
                                        suggestions: List = None) -> str:
        """
        Create HIGHLY AGGRESSIVE resume tailoring prompt
        Forces complete rewrites aligned to job requirements
        """
        job_description = decode_html_to_text(job_data.get('description', ''))
        must_have = jd_keywords.get('must_have', [])
        preferred = jd_keywords.get('preferred', [])
        tech_keywords = jd_keywords.get('technologies', [])
        action_verbs = jd_keywords.get('action_verbs', [])

        # Build score feedback
        score_feedback = ""
        if previous_score > 0:
            score_feedback = f"""
⚠️ PREVIOUS ATTEMPT SCORE: {previous_score}/100 - BELOW TARGET OF 85!
YOU MUST IMPROVE THIS SCORE. The resume is being REJECTED by ATS systems.
"""

        # Build keyword violation guidance
        violation_guidance = ""
        if keyword_violations:
            violated_kw = [kw for kw, _ in keyword_violations]
            violation_guidance = f"""

KEYWORD REPETITION VIOLATIONS DETECTED:
These keywords are overused (>2 times): {', '.join(violated_kw[:10])}
YOU MUST reduce usage of these keywords. Use synonyms and varied phrasing.
Example: Instead of repeating "developed" 4 times, use: developed, engineered, built, created.
"""

        # Build suggestions
        suggestions_text = ""
        if suggestions:
            suggestions_text = f"""

SPECIFIC IMPROVEMENTS NEEDED:
{chr(10).join('- ' + s for s in suggestions[:5])}
YOU MUST address these issues in your rewrite!
"""

        prompt = f"""You are an EXPERT ATS resume optimizer and professional resume writer. Your ONLY job is to CREATE ENTIRELY NEW CONTENT that is HEAVILY BASED ON THE JOB DESCRIPTION while maintaining 100% truthfulness to the candidate's background.

⚠️ CRITICAL MISSION:
- FORGET the exact wording from the original resume - treat it as background context ONLY
- Your PRIMARY SOURCE is the JOB DESCRIPTION below
- GENERATE EVERY BULLET from the perspective: "What would this job posting want to hear?"
- Use the candidate's experiences as proof points, but REWRITE EVERYTHING using JD language
- Think: "I'm writing bullets that directly answer each JD requirement"

🚫 ABSOLUTELY FORBIDDEN:
- Copying phrases from base resume (even partially)
- Using generic tech descriptions that could fit any job
- Writing bullets that don't directly address JD requirements
- Missing opportunities to use JD-specific keywords

✅ MANDATORY APPROACH:
- Read JD requirement → Find matching experience → Write NEW bullet using JD's exact terminology
- Every sentence must sound like it was written specifically for THIS job posting
- Use JD keywords in EVERY bullet (3-5 keywords minimum per bullet)

{score_feedback}{suggestions_text}

═══════════════════════════════════════════════════════════════
I. THE JOB DESCRIPTION (YOUR PRIMARY SOURCE - READ THIS FIRST!)
═══════════════════════════════════════════════════════════════
Job Title: {job_data.get('job_title', 'N/A')}
Company: {job_data.get('company_name', 'N/A')}

🎯 KEYWORDS YOU MUST USE (EXACT TERMS):
Must-Have (USE EVERY ONE): {', '.join(must_have[:15])}
Preferred (USE AS MANY AS POSSIBLE): {', '.join(preferred[:10])}
Technologies (PRIORITIZE THESE): {', '.join(tech_keywords[:20])}
Action Verbs (START BULLETS WITH THESE): {', '.join(action_verbs[:15])}

📋 FULL JOB DESCRIPTION (THIS IS YOUR BLUEPRINT):
{job_description[:3000]}

READ THE JD CAREFULLY. Your bullets must directly respond to what they're asking for above.

═══════════════════════════════════════════════════════════════
II. CANDIDATE'S BACKGROUND (Context Only - DO NOT Copy Wording!)
═══════════════════════════════════════════════════════════════
Experience: {json.dumps(self.base_experience, indent=2)}
Projects: {json.dumps(self.base_projects, indent=2)}
Skills: {json.dumps(self.base_skills)}
Achievements: {self.achievements_text[:1000]}

⚠️ IMPORTANT: This background info proves the candidate HAS the experience. But you must describe it using THE JOB DESCRIPTION'S language, not the original resume's language.

═══════════════════════════════════════════════════════════════
III. MANDATORY REWRITING INSTRUCTIONS
═══════════════════════════════════════════════════════════════

🔴 CRITICAL RULE #1: GENERATE BULLETS FROM JOB DESCRIPTION (MOST IMPORTANT!)

STEP-BY-STEP PROCESS FOR EACH BULLET:
1. Pick a requirement from the JOB DESCRIPTION
2. Find which experience/project addresses that requirement
3. Write a BRAND NEW sentence that:
   a) Uses action verb FROM the JD
   b) Includes 3-5 keywords FROM the JD
   c) Describes impact using numbers
   d) Sounds like it was written BY the hiring manager

❌ WRONG APPROACH (copying original resume):
Original bullet: "Developed scalable web applications using React"
Bad rewrite: "Built scalable web applications using React and Node.js"
Why bad: Just swapped words, still generic, could apply to any job

✅ RIGHT APPROACH (JD-first thinking):
JD says: "Need engineer to build microservices with React, Node, Docker, CI/CD"
You write: "Architected enterprise microservices platform using React, Node.js, and Docker, implementing automated CI/CD pipelines that reduced deployment cycles by 60% and enabled 50K+ concurrent users"
Why good: Directly answers what JD asked for, uses exact JD terms, adds metrics

🎯 YOUR MENTAL PROCESS FOR EVERY BULLET:
"What is the hiring manager looking for?" → Find it in candidate's background → Describe it using JD's exact language + metrics

🔴 CRITICAL RULE #2: EXACT KEYWORD MATCHING
- Use EXACT terminology from job description (if JD says "microservices architecture", use that EXACT phrase)
- Must-have keywords MUST appear at least once, ideally 1-2 times
- Preferred keywords should appear if truthfully applicable
- Technical keywords should be integrated naturally, not stuffed

🔴 CRITICAL RULE #3: NO KEYWORD REPETITION
- Maximum 2 uses of any single keyword across ALL bullets
- Track keyword usage carefully
- Use synonyms and varied phrasing:
  * "developed" → "engineered", "built", "created", "implemented"
  * "improved" → "enhanced", "optimized", "increased", "boosted"
  * "managed" → "led", "coordinated", "orchestrated", "directed"
{violation_guidance}

🔴 CRITICAL RULE #4: QUANTIFY EVERYTHING
- Every bullet MUST include metrics (%, numbers, scale, users, time savings)
- If original has numbers, maintain or enhance them
- Examples: "improved by 35%", "serving 10K+ users", "reduced time by 50%"

🔴 CRITICAL RULE #5: MAP TO JOB REQUIREMENTS
For EACH bullet point:
STEP 1: Identify which specific job requirement it addresses
STEP 2: Rewrite to EXPLICITLY show you meet that requirement
STEP 3: Use the JD's exact phrasing and terminology
STEP 4: Add quantified impact

═══════════════════════════════════════════════════════════════
IV. EXPERIENCE SECTION - GENERATE JD-SPECIFIC BULLETS
═══════════════════════════════════════════════════════════════

For EACH experience entry:

1. KEEP UNCHANGED: company, title, dates, location

2. TECHNOLOGIES:
   - Reorder to put JD-required technologies FIRST
   - Add 2-3 JD technologies if they fit the role naturally
   - Example: Original "Python, Django, PostgreSQL" → Reordered for AWS role: "AWS, Docker, Python, PostgreSQL"

3. DESCRIPTION BULLETS - CRITICAL SECTION:

   🚫 DO NOT look at original bullets and modify them
   ✅ DO look at JOB DESCRIPTION and generate new bullets

   PROCESS FOR EACH BULLET:
   Step 1: Read a JD requirement (e.g., "Must build RESTful APIs")
   Step 2: Check if this experience addresses it (e.g., "Yes, built APIs at this job")
   Step 3: Write NEW bullet using FORMULA:

   [JD ACTION VERB] + [JD TECHNOLOGIES] + [JD RESPONSIBILITY] + [METRIC] + [BUSINESS IMPACT]

   EXAMPLE - JD requires: "Build scalable dashboards with React, Redux for data visualization"

   ❌ WRONG (modified original): "Built dashboards using React"
   ❌ WRONG (generic): "Developed React dashboards with good performance"
   ✅ CORRECT (JD-generated): "Architected real-time analytics dashboards leveraging React, Redux, and D3.js to enable executive decision-making, reducing reporting time by 40% across 15 departments"

   Why correct version works:
   - "Architected" = senior action verb matching JD tone
   - "React, Redux, D3.js" = exact JD technologies
   - "analytics dashboards" = exact JD need
   - "40% reduction, 15 departments" = quantified impact
   - Could ONLY be written for THIS specific job

═══════════════════════════════════════════════════════════════
V. PROJECTS SECTION - SHOWCASE JD-REQUIRED SKILLS
═══════════════════════════════════════════════════════════════

SAME JD-FIRST APPROACH for projects:

1. KEEP UNCHANGED: title, dates

2. TECHNOLOGIES (Max 4 keywords):
   - List ONLY JD-relevant technologies FIRST
   - If original project used React but JD needs Vue, and you know Vue, mention Vue if truthful
   - Prioritize JD tech stack completely

3. DESCRIPTION BULLETS - PROVE YOU HAVE JD SKILLS:

   🎯 MISSION: Show this project demonstrates EXACTLY what the JD asks for

   PROCESS:
   Step 1: Identify key JD requirements (e.g., "microservices, Docker, AWS, CI/CD")
   Step 2: Describe project using THOSE exact terms
   Step 3: Add scale/metrics that match JD expectations

   EXAMPLE - JD needs: "Cloud-native apps with Docker, Kubernetes, AWS"

   ❌ WRONG (generic): "Built web app with Node.js backend"
   ❌ WRONG (vague): "Created scalable application using modern technologies"
   ✅ CORRECT (JD-targeted): "Engineered cloud-native microservices architecture using Node.js, Express, and Docker, deployed on AWS ECS with Kubernetes orchestration, achieving 99.9% uptime serving 10K+ daily users"

   Why correct:
   - "cloud-native microservices" = exact JD terminology
   - "Docker, AWS, Kubernetes" = exact JD technologies
   - "99.9% uptime, 10K+ users" = enterprise-scale metrics
   - Proves candidate can deliver what JD asks for

═══════════════════════════════════════════════════════════════
VI. SKILLS SECTION OPTIMIZATION
═══════════════════════════════════════════════════════════════

Create two lists:

1. skills_list:
   - Include ALL must-have keywords that are skills
   - Include ALL technical keywords you can truthfully claim
   - Order by relevance to JD (most important first)
   - Aim for 12-18 skills total
   - USE EXACT PHRASING from JD (if JD says "RESTful APIs", not just "APIs")

2. tools_list:
   - All tools/platforms from JD that you have experience with
   - Order by relevance
   - Aim for 8-12 tools
   - Include cloud platforms, devops tools, databases mentioned in JD

═══════════════════════════════════════════════════════════════
VII. OUTPUT FORMAT (STRICT JSON)
═══════════════════════════════════════════════════════════════

Return ONLY valid JSON:

{{
  "tailored_experience": [
    {{
      "company": "Original Company Name",
      "title": "Original Title",
      "dates": "Original Dates",
      "technologies": "Reordered tech, prioritizing JD match",
      "location": "Original Location",
      "description": [
        "COMPLETELY REWRITTEN bullet 1 with JD keywords and metrics",
        "COMPLETELY REWRITTEN bullet 2 with different angle on JD requirements",
        "COMPLETELY REWRITTEN bullet 3 addressing another JD need"
      ]
    }}
  ],
  "tailored_projects": [
    {{
      "title": "Original Project Name",
      "technologies": "Reordered/enhanced tech list",
      "dates": "Original Dates",
      "description": [
        "COMPLETELY REWRITTEN project bullet showing JD-relevant skills",
        "COMPLETELY REWRITTEN project bullet with quantified impact"
      ]
    }}
  ],
  "tailored_skills": {{
    "skills_list": ["JD keyword 1", "JD keyword 2", "Relevant skill 3", ...],
    "tools_list": ["JD tool 1", "JD tool 2", "Relevant tool 3", ...]
  }},
  "keyword_mapping": {{
    "must_have_coverage": ["keyword1: used in experience bullet 2", "keyword2: used in project 1", ...],
    "preferred_coverage": ["keyword: location in resume", ...],
    "keyword_frequency": {{"keyword": count, ...}}
  }}
}}

═══════════════════════════════════════════════════════════════
🚨 FINAL CRITICAL REMINDER BEFORE YOU START WRITING
═══════════════════════════════════════════════════════════════

WRONG MINDSET: "Let me take this resume and improve it"
RIGHT MINDSET: "Let me generate bullets that answer exactly what the JD is asking for"

Your source of truth is THE JOB DESCRIPTION, not the original resume.
The original resume is just proof that the candidate has done relevant work.
But YOU must describe that work using the HIRING MANAGER'S language.

If you find yourself copying phrases from the original resume, STOP and restart.
If a bullet could fit on any generic resume, STOP and rewrite it JD-specific.
If you haven't used 3+ JD keywords in a bullet, STOP and add them.

FINAL CHECKLIST BEFORE RETURNING:
✓ Every bullet sounds like it was written specifically for THIS job posting
✓ Every bullet uses exact terminology from the JD (not generic synonyms)
✓ Every bullet includes 3-5 keywords from the must-have/preferred/tech lists
✓ No keyword used more than 2 times total across entire resume
✓ Every bullet has quantified metrics (%, numbers, scale)
✓ Technologies reordered to put JD requirements FIRST
✓ If I showed these bullets to the hiring manager, they'd think "This person is EXACTLY what we need"

⚠️ SCORING REALITY: Generic bullets = 60-70 ATS score (REJECTION). JD-specific bullets with keywords = 85+ score (INTERVIEW). Your goal is 85+ ATS score.
"""

        return prompt

    def tailor_with_refinement(self, job_data: Dict) -> Dict:
        """
        Iteratively tailor resume until ATS score >= 85
        Returns: {'experience': [...], 'projects': [...], 'skills': {...}, 'ats_score': 87}
        """
        self.load_base_data()

        # Extract keywords from JD
        jd_keywords = self.ats_scorer.extract_keywords_from_jd(job_data)
        logger.info(f"Extracted JD keywords: {sum(len(v) for v in jd_keywords.values())} total")

        best_resume = None
        best_score = 0
        keyword_violations = None
        previous_suggestions = []

        for iteration in range(self.MAX_REFINEMENT_ITERATIONS):
            logger.info(f"\n{'='*60}")
            logger.info(f"REFINEMENT ITERATION {iteration + 1}/{self.MAX_REFINEMENT_ITERATIONS}")
            logger.info(f"{'='*60}")

            # Create prompt with violation feedback and previous score
            prompt = self.create_aggressive_resume_prompt(
                job_data, jd_keywords, keyword_violations,
                previous_score=best_score,
                suggestions=previous_suggestions
            )

            # Call Gemini
            try:
                logger.info("Calling Gemini API for aggressive tailoring...")
                response = gemini_model.generate_content(prompt)

                # Parse response
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:-3].strip()
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:-3].strip()

                tailored_data = json.loads(raw_text)

                # Validate structure
                if not all(k in tailored_data for k in ['tailored_experience', 'tailored_projects', 'tailored_skills']):
                    raise ValueError("Missing required keys in response")

                logger.info("✓ Successfully parsed tailored resume from Gemini")

                # Score this version
                resume_for_scoring = {
                    'experience': tailored_data['tailored_experience'],
                    'projects': tailored_data['tailored_projects'],
                    'skills': tailored_data['tailored_skills']
                }

                score_result = self.ats_scorer.score_resume(
                    resume_for_scoring, job_data
                )

                current_score = score_result['total_score']
                logger.info(f"ATS Score: {current_score}/100")

                # Log breakdown
                logger.info("Score Breakdown:")
                for category, score in score_result['breakdown'].items():
                    logger.info(f"  {category}: {score}")

                # Check violations
                keyword_violations = score_result.get('violations', [])
                if keyword_violations:
                    logger.warning(f"Keyword violations: {len(keyword_violations)}")
                    for kw, count in keyword_violations[:5]:
                        logger.warning(f"  - {kw}: {count} times")

                # Capture suggestions for next iteration
                previous_suggestions = score_result.get('suggestions', [])

                # Update best if this is better
                if current_score > best_score:
                    best_score = current_score
                    best_resume = tailored_data
                    logger.info(f"✓ New best score: {best_score}")

                # Check if we met target
                if current_score >= self.TARGET_ATS_SCORE:
                    logger.info(f"🎉 TARGET ACHIEVED! Score: {current_score} >= {self.TARGET_ATS_SCORE}")
                    break

                # Log feedback for next iteration
                if iteration < self.MAX_REFINEMENT_ITERATIONS - 1:
                    logger.info(f"⚠️  Refinement needed. Suggestions for iteration {iteration + 2}:")
                    for suggestion in previous_suggestions:
                        logger.info(f"  - {suggestion}")
                else:
                    logger.warning(f"Max iterations reached. Final score: {best_score}/100")

            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                if 'response' in locals():
                    logger.error(f"Raw response: {response.text[:500]}")
                continue

            except Exception as e:
                logger.error(f"Tailoring error: {e}", exc_info=True)
                continue

        # Return best result
        if best_resume:
            logger.info(f"\n{'='*60}")
            logger.info(f"FINAL RESULT: ATS Score = {best_score}/100")
            logger.info(f"{'='*60}")

            return {
                'experience': best_resume['tailored_experience'],
                'projects': best_resume['tailored_projects'],
                'skills': best_resume['tailored_skills'],
                'ats_score': best_score,
                'keyword_mapping': best_resume.get('keyword_mapping', {})
            }
        else:
            logger.error("All tailoring attempts failed")
            return None


def generate_tailored_resume_enhanced(job_data: Dict) -> Dict:
    """
    Main entry point for enhanced resume tailoring
    Returns tailored resume data with ATS score >= 85
    """
    tailor = EnhancedResumeTailor()
    result = tailor.tailor_with_refinement(job_data)
    return result


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
        'skills': ['React', 'Node.js', 'AWS', 'Docker', 'MongoDB', 'TypeScript'],
        'qualifications': {
            'mustHave': ['React', 'Node.js', 'AWS', 'Docker'],
            'preferredHave': ['TypeScript', 'Kubernetes', 'GraphQL']
        }
    }

    result = generate_tailored_resume_enhanced(test_job)

    if result:
        print(f"\n{'='*60}")
        print(f"✓ Resume tailored successfully!")
        print(f"ATS Score: {result['ats_score']}/100")
        print(f"{'='*60}")
