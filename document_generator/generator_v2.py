#!/usr/bin/env python3
"""
Enhanced Document Generator V2
Integrates ReportLab, ATS scoring, and aggressive tailoring
"""

import os
import logging
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    from document_generator.resume_reportlab import create_resume_reportlab
    from document_generator.generator import create_job_details_pdf_reportlab  # Keep old job details
    from resume_tailor.tailor_enhanced import generate_tailored_resume_enhanced
    from ats_scorer import ATSScorer
    import config
except ImportError as e:
    logging.critical(f"Import error in generator_v2: {e}")
    raise SystemExit(f"Critical import error: {e}")

logger = logging.getLogger(__name__)


class DocumentGeneratorV2:
    """
    Enhanced document generator with:
    - ReportLab one-page resumes
    - ATS scoring >= 85
    - Aggressive tailoring
    - Cover letter generation
    """

    def __init__(self):
        self.ats_scorer = ATSScorer()

    def generate_all_documents(self, job_data: dict, target_output_dir: str) -> dict:
        """
        Generate all documents with ATS optimization

        Args:
            job_data: Job posting data from database
            target_output_dir: Directory to save generated PDFs

        Returns:
            {
                'resume_pdf': '/path/to/resume.pdf',
                'cover_letter_pdf': '/path/to/cover.pdf',
                'job_details_pdf': '/path/to/details.pdf',
                'ats_score': 87.5,
                'ats_report': {...}
            }
        """
        logger.info(f"Starting enhanced document generation for: {job_data.get('job_title', 'Unknown')} at {job_data.get('company_name', 'Unknown')}")

        target_dir = Path(target_output_dir)
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        # Prepare filenames
        first_name = getattr(config, 'FIRST_NAME', 'Resume').strip() or 'Resume'
        company_name = job_data.get('company_name', 'Company').strip().replace(' ', '_')[:30]

        resume_filename = f"{first_name}_{company_name}_Resume"
        cover_letter_filename = f"{first_name}_{company_name}_CoverLetter"
        job_details_filename = f"{first_name}_{company_name}_JobDetails"

        results = {
            'resume_pdf': None,
            'cover_letter_pdf': None,
            'job_details_pdf': None,
            'ats_score': 0,
            'ats_report': None
        }

        # STEP 1: Generate tailored resume with ATS optimization
        logger.info("=" * 60)
        logger.info("STEP 1: Tailoring Resume (Target ATS Score: 85+)")
        logger.info("=" * 60)

        tailored_resume_data = generate_tailored_resume_enhanced(job_data)

        if not tailored_resume_data:
            logger.error("Failed to generate tailored resume")
            return results

        # Add education from config or base_resume
        tailored_resume_data['education'] = [{
            'university': getattr(config, 'UNIVERSITY', 'Syracuse University'),
            'degree': getattr(config, 'DEGREE', 'Master of Science in Computer Science'),
            'location': getattr(config, 'EDUCATION_LOCATION', 'Syracuse, NY'),
            'dates': getattr(config, 'EDUCATION_DATES', 'Aug 2024 -- Dec 2025')
        }]

        ats_score = tailored_resume_data.get('ats_score', 0)
        logger.info(f"✓ Resume tailored with ATS score: {ats_score}/100")

        # Get full ATS report
        ats_report = self.ats_scorer.score_resume(
            {
                'experience': tailored_resume_data['experience'],
                'projects': tailored_resume_data['projects'],
                'skills': tailored_resume_data['skills']
            },
            job_data
        )

        results['ats_score'] = ats_score
        results['ats_report'] = ats_report

        # STEP 2: Generate one-page PDF using ReportLab
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Generating One-Page PDF (ReportLab)")
        logger.info("=" * 60)

        resume_pdf_path = create_resume_reportlab(
            tailored_resume_data,
            str(target_dir),
            resume_filename
        )

        if resume_pdf_path:
            logger.info(f"✓ Resume PDF created: {Path(resume_pdf_path).name}")
            results['resume_pdf'] = resume_pdf_path
        else:
            logger.error("Failed to create resume PDF")

        # STEP 3: Generate Cover Letter (using original LaTeX method for now)
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Generating Cover Letter")
        logger.info("=" * 60)

        cover_letter_pdf = self._generate_cover_letter(
            job_data,
            tailored_resume_data,
            target_dir,
            cover_letter_filename
        )

        if cover_letter_pdf:
            logger.info(f"✓ Cover Letter PDF created: {Path(cover_letter_pdf).name}")
            results['cover_letter_pdf'] = cover_letter_pdf

        # STEP 4: Generate Job Details PDF
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Generating Job Details PDF")
        logger.info("=" * 60)

        job_details_pdf = create_job_details_pdf_reportlab(
            job_data,
            target_dir,
            job_details_filename
        )

        if job_details_pdf:
            logger.info(f"✓ Job Details PDF created: {Path(job_details_pdf).name}")
            results['job_details_pdf'] = job_details_pdf

        # FINAL REPORT
        logger.info("\n" + "=" * 80)
        logger.info("GENERATION COMPLETE - SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Job: {job_data.get('job_title')} at {job_data.get('company_name')}")
        logger.info(f"ATS Score: {ats_score}/100 {'✓ PASS' if ats_score >= 85 else '✗ NEEDS IMPROVEMENT'}")
        logger.info(f"Resume: {'✓' if results['resume_pdf'] else '✗'} {resume_filename}.pdf")
        logger.info(f"Cover Letter: {'✓' if results['cover_letter_pdf'] else '✗'} {cover_letter_filename}.pdf")
        logger.info(f"Job Details: {'✓' if results['job_details_pdf'] else '✗'} {job_details_filename}.pdf")

        if ats_report and ats_report.get('suggestions'):
            logger.info("\nATS Optimization Suggestions:")
            for suggestion in ats_report['suggestions'][:5]:
                logger.info(f"  • {suggestion}")

        logger.info("=" * 80)

        return results

    def _generate_cover_letter(self, job_data: dict, tailored_resume: dict,
                               target_dir: Path, filename_base: str) -> str:
        """
        Generate ATS-optimized one-page cover letter using ReportLab
        """
        try:
            from resume_tailor.cover_letter_tailor import generate_ats_optimized_cover_letter
            from document_generator.cover_letter_reportlab import generate_cover_letter_pdf

            # Generate ATS-optimized cover letter content
            logger.info("Generating ATS-optimized cover letter content...")
            cl_result = generate_ats_optimized_cover_letter(job_data)

            if not cl_result:
                logger.error("Cover letter generation failed")
                return None

            cl_ats_score = cl_result.get('ats_score', 0)
            logger.info(f"Cover Letter ATS Score: {cl_ats_score}/100")

            # Prepare cover letter data for PDF generation
            cover_letter_data = {
                'applicant_name': tailored_resume.get('name', config.YOUR_NAME if hasattr(config, 'YOUR_NAME') else 'Your Name'),
                'phone': config.YOUR_PHONE if hasattr(config, 'YOUR_PHONE') else '',
                'email': config.YOUR_EMAIL if hasattr(config, 'YOUR_EMAIL') else '',
                'linkedin': config.YOUR_LINKEDIN_URL_TEXT if hasattr(config, 'YOUR_LINKEDIN_URL_TEXT') else '',
                'location': '',
                'company_name': job_data.get('company_name', ''),
                'hiring_manager': '',
                'company_address': '',
                'paragraphs': cl_result['paragraphs']
            }

            # Generate PDF
            cl_pdf_path = str(target_dir / f"{filename_base}.pdf")
            generate_cover_letter_pdf(cover_letter_data, cl_pdf_path)

            logger.info(f"✓ Cover letter PDF created with ATS score: {cl_ats_score}/100")
            return cl_pdf_path

        except Exception as e:
            logger.error(f"Cover letter generation error: {e}", exc_info=True)
            return None


def create_documents_v2(job_data: dict, target_output_directory: str) -> tuple:
    """
    Main entry point for V2 document generation
    Compatible with existing main.py interface

    Args:
        job_data: Job posting data
        target_output_directory: Output directory path

    Returns:
        (resume_pdf_path, cover_letter_pdf_path, job_details_pdf_path)
    """
    generator = DocumentGeneratorV2()
    results = generator.generate_all_documents(job_data, target_output_directory)

    return (
        results.get('resume_pdf'),
        results.get('cover_letter_pdf'),
        results.get('job_details_pdf')
    )


if __name__ == '__main__':
    # Test the V2 generator
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
    )

    test_job = {
        '_id': 'test123',
        'job_title': 'Senior Full Stack Engineer',
        'company_name': 'TechCorp Inc',
        'description': '''
        We are seeking a talented Senior Full Stack Engineer to join our team.
        You will design and build scalable web applications using React, Node.js, and AWS.
        Experience with TypeScript, Docker, and microservices architecture is required.

        Responsibilities:
        - Develop responsive frontends using React and Redux
        - Build RESTful APIs with Node.js and Express
        - Deploy applications to AWS using Docker containers
        - Implement CI/CD pipelines
        - Collaborate with cross-functional teams

        Requirements:
        - 5+ years of experience with React and Node.js
        - Strong knowledge of AWS services (EC2, S3, Lambda)
        - Experience with Docker and Kubernetes
        - TypeScript proficiency
        - Excellent problem-solving skills
        ''',
        'skills': ['React', 'Node.js', 'AWS', 'Docker', 'TypeScript', 'Kubernetes', 'MongoDB'],
        'qualifications': {
            'mustHave': ['React', 'Node.js', 'AWS', 'Docker', 'TypeScript'],
            'preferredHave': ['Kubernetes', 'GraphQL', 'Redis']
        },
        'core_responsibilities': [
            'Develop responsive frontends',
            'Build RESTful APIs',
            'Deploy to cloud infrastructure',
            'Implement CI/CD pipelines'
        ]
    }

    output_dir = '/tmp/job_agent_test'
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("TESTING ENHANCED DOCUMENT GENERATOR V2")
    print("=" * 80 + "\n")

    results = create_documents_v2(test_job, output_dir)

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"Resume: {results[0]}")
    print(f"Cover Letter: {results[1]}")
    print(f"Job Details: {results[2]}")
