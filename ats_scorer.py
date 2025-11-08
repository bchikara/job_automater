#!/usr/bin/env python3
"""
ATS (Applicant Tracking System) Scoring Engine
Ensures resume achieves 85+ ATS compatibility score
"""

import re
from collections import Counter
from typing import Dict, List, Tuple, Set
import logging

logger = logging.getLogger(__name__)


class ATSScorer:
    """ATS scoring engine with keyword tracking and optimization"""

    # ATS-friendly formatting rules
    REQUIRED_SECTIONS = ['education', 'experience', 'skills']
    MAX_KEYWORD_FREQUENCY = 2  # Max times a keyword can appear

    def __init__(self):
        self.keyword_tracker = Counter()
        self.score_breakdown = {}

    def extract_keywords_from_jd(self, job_data: Dict) -> Dict[str, List[str]]:
        """
        Extract and categorize keywords from job description
        Returns: {
            'must_have': [...],
            'preferred': [...],
            'technologies': [...],
            'action_verbs': [...]
        }
        """
        keywords = {
            'must_have': [],
            'preferred': [],
            'technologies': [],
            'action_verbs': []
        }

        # Extract from structured data
        qualifications = job_data.get('qualifications', {})
        if isinstance(qualifications, dict):
            must_have_raw = qualifications.get('mustHave', [])
            preferred_raw = qualifications.get('preferredHave', [])

            # Handle both list of strings and list of sentences
            # Extract keywords from qualification sentences
            for item in must_have_raw:
                if isinstance(item, str):
                    # Extract tech keywords from each requirement sentence
                    tech_from_req = self._extract_tech_keywords(item)
                    keywords['must_have'].extend(tech_from_req)
                    keywords['technologies'].extend(tech_from_req)

            for item in preferred_raw:
                if isinstance(item, str):
                    tech_from_pref = self._extract_tech_keywords(item)
                    keywords['preferred'].extend(tech_from_pref)
                    keywords['technologies'].extend(tech_from_pref)

        # Extract from skills list (handle both object and string formats)
        job_skills = job_data.get('skills', [])
        if isinstance(job_skills, list):
            for skill_item in job_skills:
                if isinstance(skill_item, dict):
                    # New format: {"skill": "Node.js", "score": 3, "type": "hard_skill"}
                    skill_name = skill_item.get('skill', '')
                    if skill_name:
                        keywords['technologies'].append(skill_name)
                        # Add high-score skills to must_have
                        if skill_item.get('score', 0) >= 3:
                            keywords['must_have'].append(skill_name)
                        elif skill_item.get('score', 0) >= 2:
                            keywords['preferred'].append(skill_name)
                elif isinstance(skill_item, str):
                    # Old format: just strings
                    keywords['technologies'].append(skill_item)

        # Extract from description using NLP-like patterns
        description = job_data.get('description', '')
        if description:
            # Common action verbs in tech JDs
            action_verbs = self._extract_action_verbs(description)
            keywords['action_verbs'].extend(action_verbs)

            # Extract technologies mentioned
            tech_keywords = self._extract_tech_keywords(description)
            keywords['technologies'].extend(tech_keywords)

        # Remove duplicates and normalize (handle only strings)
        for category in keywords:
            # Filter to only string items and normalize
            keywords[category] = list(set([
                kw.strip().lower()
                for kw in keywords[category]
                if isinstance(kw, str) and kw and kw.strip()
            ]))

        logger.info(f"Extracted keywords: {sum(len(v) for v in keywords.values())} total")
        return keywords

    def _extract_action_verbs(self, text: str) -> List[str]:
        """Extract action verbs from job description"""
        common_verbs = [
            'develop', 'design', 'implement', 'build', 'create', 'manage',
            'lead', 'architect', 'optimize', 'deploy', 'maintain', 'scale',
            'collaborate', 'integrate', 'automate', 'test', 'debug', 'analyze',
            'engineer', 'deliver', 'drive', 'improve', 'enhance', 'establish'
        ]

        text_lower = text.lower()
        found_verbs = []
        for verb in common_verbs:
            # Look for verb and its variations (develop, developed, developing)
            if re.search(r'\b' + verb + r'(s|ed|ing)?\b', text_lower):
                found_verbs.append(verb)

        return found_verbs

    def _extract_tech_keywords(self, text: str) -> List[str]:
        """Extract technology/tool keywords from text"""
        # Common tech keywords (expandable)
        tech_patterns = [
            # Languages
            r'\b(python|javascript|typescript|java|c\+\+|go|rust|ruby|php|swift|kotlin)\b',
            # Frontend
            r'\b(react|angular|vue|next\.js|redux|rxjs|d3\.js|three\.js)\b',
            # Backend
            r'\b(node\.js|express|django|flask|spring|\.net)\b',
            # Databases
            r'\b(mongodb|postgresql|mysql|redis|elasticsearch|dynamodb)\b',
            # Cloud/DevOps
            r'\b(aws|azure|gcp|docker|kubernetes|terraform|jenkins|ci/cd)\b',
            # Other
            r'\b(graphql|rest\s+api|microservices|serverless|websocket)\b'
        ]

        found_tech = []
        text_lower = text.lower()
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            found_tech.extend(matches)

        return list(set(found_tech))

    def count_keywords_in_resume(self, resume_data: Dict) -> Counter:
        """
        Count keyword frequency across all resume sections
        resume_data: {'experience': [...], 'projects': [...], 'skills': {...}}
        """
        self.keyword_tracker = Counter()

        # Count in experience descriptions
        for exp in resume_data.get('experience', []):
            desc_points = exp.get('description', [])
            for point in desc_points:
                if isinstance(point, str):
                    self._count_keywords_in_text(point)

            # Count in technologies
            tech = exp.get('technologies', '')
            if tech:
                self._count_keywords_in_text(tech)

        # Count in projects
        for proj in resume_data.get('projects', []):
            desc_points = proj.get('description', [])
            for point in desc_points:
                if isinstance(point, str):
                    self._count_keywords_in_text(point)

            tech = proj.get('technologies', '')
            if tech:
                self._count_keywords_in_text(tech)

        # Count in skills
        skills_dict = resume_data.get('skills', {})
        if isinstance(skills_dict, dict):
            for skill_list in skills_dict.values():
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        self._count_keywords_in_text(str(skill))
                elif isinstance(skill_list, str):
                    self._count_keywords_in_text(skill_list)

        return self.keyword_tracker

    def _count_keywords_in_text(self, text: str):
        """Count individual keywords in text (case-insensitive)"""
        # Tokenize and normalize
        words = re.findall(r'\b[\w\.\+#]+\b', text.lower())

        # Also handle multi-word tech terms
        text_lower = text.lower()
        multi_word_terms = [
            'react.js', 'node.js', 'next.js', 'd3.js', 'three.js',
            'rest api', 'machine learning', 'data structures',
            'ci/cd', 'microservices', 'cloud computing'
        ]

        for term in multi_word_terms:
            if term in text_lower:
                self.keyword_tracker[term] += 1

        # Count single words
        for word in words:
            if len(word) > 2:  # Ignore very short words
                self.keyword_tracker[word] += 1

    def check_keyword_violations(self, jd_keywords: Dict[str, List[str]]) -> Dict[str, List[Tuple[str, int]]]:
        """
        Check for keywords exceeding max frequency
        Returns: {'violated': [(keyword, count), ...], 'missing': [...]}
        """
        all_jd_keywords = []
        for category in jd_keywords.values():
            all_jd_keywords.extend(category)

        violations = []
        for keyword in set(all_jd_keywords):
            count = self.keyword_tracker.get(keyword.lower(), 0)
            if count > self.MAX_KEYWORD_FREQUENCY:
                violations.append((keyword, count))

        # Check for missing critical keywords
        missing = []
        for keyword in jd_keywords.get('must_have', []):
            if self.keyword_tracker.get(keyword.lower(), 0) == 0:
                missing.append(keyword)

        return {
            'violated': sorted(violations, key=lambda x: x[1], reverse=True),
            'missing': missing
        }

    def score_resume(self, resume_data: Dict, job_data: Dict, resume_text: str = "") -> Dict:
        """
        Calculate comprehensive ATS score (0-100)

        Scoring breakdown:
        - Keyword Match (40 points): Must-have and preferred keywords
        - Keyword Density (20 points): Optimal keyword usage (not too sparse, not stuffed)
        - No Repetition (10 points): Keywords used max 2 times
        - Formatting (20 points): Standard sections, clean structure
        - Contact Info (10 points): Complete contact information

        Returns: {
            'total_score': 85,
            'breakdown': {...},
            'violations': [...],
            'suggestions': [...]
        }
        """
        logger.info("Starting ATS scoring...")

        # Extract JD keywords
        jd_keywords = self.extract_keywords_from_jd(job_data)

        # Count resume keywords
        self.count_keywords_in_resume(resume_data)

        # Initialize scores
        scores = {
            'keyword_match': 0,
            'keyword_density': 0,
            'no_repetition': 0,
            'formatting': 0,
            'contact_info': 0
        }

        suggestions = []

        # 1. KEYWORD MATCH SCORE (40 points)
        must_have_keywords = jd_keywords.get('must_have', [])
        preferred_keywords = jd_keywords.get('preferred', [])
        tech_keywords = jd_keywords.get('technologies', [])

        must_have_found = sum(1 for kw in must_have_keywords if self.keyword_tracker.get(kw.lower(), 0) > 0)
        preferred_found = sum(1 for kw in preferred_keywords if self.keyword_tracker.get(kw.lower(), 0) > 0)
        tech_found = sum(1 for kw in tech_keywords if self.keyword_tracker.get(kw.lower(), 0) > 0)

        total_keywords = len(must_have_keywords) + len(preferred_keywords) + len(tech_keywords)
        total_found = must_have_found + preferred_found + tech_found

        if total_keywords > 0:
            # Must-have weighted more heavily
            must_have_score = (must_have_found / max(len(must_have_keywords), 1)) * 25
            preferred_score = (preferred_found / max(len(preferred_keywords), 1)) * 10
            tech_score = (tech_found / max(len(tech_keywords), 1)) * 5
            scores['keyword_match'] = min(40, must_have_score + preferred_score + tech_score)

        if must_have_found < len(must_have_keywords):
            missing_must_have = [kw for kw in must_have_keywords if self.keyword_tracker.get(kw.lower(), 0) == 0]
            suggestions.append(f"Add must-have keywords: {', '.join(missing_must_have[:5])}")

        # 2. KEYWORD DENSITY SCORE (20 points)
        # Optimal density: 2-4% of total words
        total_words = sum(self.keyword_tracker.values())
        unique_jd_keywords = set(kw.lower() for cat in jd_keywords.values() for kw in cat)
        jd_keyword_occurrences = sum(self.keyword_tracker.get(kw, 0) for kw in unique_jd_keywords)

        if total_words > 0:
            density = (jd_keyword_occurrences / total_words) * 100
            if 2 <= density <= 4:
                scores['keyword_density'] = 20
            elif 1 <= density < 2 or 4 < density <= 6:
                scores['keyword_density'] = 15
            elif density < 1:
                scores['keyword_density'] = 5
                suggestions.append("Keyword density too low - add more relevant keywords")
            else:
                scores['keyword_density'] = 10
                suggestions.append("Keyword density too high - reduce keyword stuffing")

        # 3. NO REPETITION SCORE (10 points)
        violations = self.check_keyword_violations(jd_keywords)
        violated_keywords = violations['violated']

        if not violated_keywords:
            scores['no_repetition'] = 10
        else:
            # Deduct 2 points per violation, min 0
            deduction = min(10, len(violated_keywords) * 2)
            scores['no_repetition'] = max(0, 10 - deduction)
            suggestions.append(f"Reduce repetition of: {', '.join([kw for kw, _ in violated_keywords[:3]])}")

        # 4. FORMATTING SCORE (20 points)
        formatting_score = 0

        # Check required sections
        has_experience = len(resume_data.get('experience', [])) > 0
        has_projects = len(resume_data.get('projects', [])) > 0
        has_skills = bool(resume_data.get('skills', {}))

        if has_experience:
            formatting_score += 8
        if has_projects:
            formatting_score += 6
        if has_skills:
            formatting_score += 6

        scores['formatting'] = formatting_score

        if not has_experience:
            suggestions.append("Add experience section")
        if not has_skills:
            suggestions.append("Add skills section")

        # 5. CONTACT INFO SCORE (10 points)
        # Check from config (would need to pass config here, but approximating)
        contact_score = 10  # Assume contact info is complete (from config)
        scores['contact_info'] = contact_score

        # Calculate total
        total_score = sum(scores.values())

        result = {
            'total_score': round(total_score, 1),
            'breakdown': scores,
            'violations': violated_keywords,
            'missing_keywords': violations['missing'],
            'suggestions': suggestions,
            'keyword_stats': {
                'must_have_match': f"{must_have_found}/{len(must_have_keywords)}",
                'preferred_match': f"{preferred_found}/{len(preferred_keywords)}",
                'tech_match': f"{tech_found}/{len(tech_keywords)}",
                'density': f"{density:.1f}%" if total_words > 0 else "0%"
            }
        }

        logger.info(f"ATS Score: {total_score}/100")
        return result

    def get_optimization_suggestions(self, score_result: Dict) -> List[str]:
        """Generate actionable suggestions to improve ATS score"""
        suggestions = score_result.get('suggestions', [])

        # Add specific suggestions based on scores
        breakdown = score_result.get('breakdown', {})

        if breakdown.get('keyword_match', 0) < 30:
            suggestions.append("CRITICAL: Add more job-specific keywords from the job description")

        if breakdown.get('no_repetition', 0) < 8:
            suggestions.append("Reduce keyword repetition - show variety in your experience")

        if breakdown.get('keyword_density', 0) < 15:
            suggestions.append("Adjust keyword density to 2-4% of total content")

        return suggestions


def test_ats_scorer():
    """Test function for ATS scorer"""
    # Sample job data
    job_data = {
        'job_title': 'Senior Full Stack Engineer',
        'company_name': 'Tech Corp',
        'description': 'We are looking for an experienced developer with Python, React, and AWS. You will develop scalable microservices and deploy to cloud infrastructure.',
        'skills': ['Python', 'React', 'AWS', 'Docker', 'Kubernetes'],
        'qualifications': {
            'mustHave': ['Python', 'React', 'AWS'],
            'preferredHave': ['Docker', 'Kubernetes', 'TypeScript']
        }
    }

    # Sample resume data
    resume_data = {
        'experience': [
            {
                'company': 'Deloitte',
                'description': [
                    'Developed scalable Python microservices deployed on AWS',
                    'Built React dashboards with Redux for data visualization',
                    'Implemented Docker containerization for deployment'
                ],
                'technologies': 'React, Python, AWS, Docker'
            }
        ],
        'projects': [
            {
                'title': 'Project X',
                'description': [
                    'Created React application with Python backend',
                    'Deployed on AWS using Kubernetes orchestration'
                ],
                'technologies': 'React, Python, AWS, Kubernetes'
            }
        ],
        'skills': {
            'skills_list': ['Python', 'React', 'TypeScript', 'AWS', 'Docker', 'Kubernetes']
        }
    }

    scorer = ATSScorer()
    result = scorer.score_resume(resume_data, job_data)

    print(f"\n{'='*60}")
    print(f"ATS SCORE: {result['total_score']}/100")
    print(f"{'='*60}")
    print(f"\nBREAKDOWN:")
    for category, score in result['breakdown'].items():
        print(f"  {category.replace('_', ' ').title()}: {score}")

    print(f"\nKEYWORD STATS:")
    for stat, value in result['keyword_stats'].items():
        print(f"  {stat.replace('_', ' ').title()}: {value}")

    if result['violations']:
        print(f"\nKEYWORD VIOLATIONS (used > 2 times):")
        for kw, count in result['violations'][:5]:
            print(f"  - {kw}: {count} times")

    if result['suggestions']:
        print(f"\nSUGGESTIONS:")
        for suggestion in result['suggestions']:
            print(f"  - {suggestion}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_ats_scorer()
