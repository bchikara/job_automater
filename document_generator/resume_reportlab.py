#!/usr/bin/env python3
"""
ReportLab-based Resume Generator
Replicates exact LaTeX resume styling with guaranteed one-page output
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple
import sys

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Import project utilities
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class OnePageResume:
    """
    Generate ATS-friendly one-page resume matching exact LaTeX styling
    """

    # Page dimensions matching LaTeX template
    # Original LaTeX: letterpaper with margins adjusted
    # -0.5in left/right, -0.5in top, +1.0in textheight
    PAGE_WIDTH = letter[0]  # 8.5 inches
    PAGE_HEIGHT = letter[1]  # 11 inches

    # Margins matching LaTeX (after adjustments)
    MARGIN_LEFT = 0.5 * inch  # 1 - 0.5
    MARGIN_RIGHT = 0.5 * inch
    MARGIN_TOP = 0.5 * inch  # 1 - 0.5
    MARGIN_BOTTOM = 0.5 * inch  # Reduced due to +1.0in textheight

    # Content area
    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # 7.5 inches
    CONTENT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM  # 10 inches

    # Font sizes matching LaTeX 11pt document exactly
    FONT_NAME_HEADER = 20  # \Huge (adjusted for ReportLab)
    FONT_CONTACT = 9       # \small
    FONT_SECTION_TITLE = 13  # \large
    FONT_COMPANY = 11      # \textbf default
    FONT_TITLE = 10        # \textit \small
    FONT_BODY = 10         # \small (bullet points)
    FONT_DATES = 10        # \small \textit
    FONT_SCOPE_LABEL = 10  # Bold label for "Scope:", "Technologies:"

    # Spacing matching LaTeX
    SPACE_AFTER_HEADER = 0.1 * inch  # \vspace{1pt} minimal
    SPACE_AFTER_SECTION = 0.05 * inch  # \vspace{-5pt}
    SPACE_BETWEEN_ITEMS = 0.08 * inch  # \vspace{-7pt}
    SPACE_BULLET = 0.03 * inch  # \vspace{-2pt}

    def __init__(self):
        """Initialize resume generator"""
        self.styles = self._create_styles()
        self.story = []
        self.current_height = 0
        # Target 85% of actual content height as safety margin
        # (wrap() estimation is significantly off from actual PDF rendering)
        self.max_height = self.CONTENT_HEIGHT * 0.85

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create paragraph styles matching LaTeX template"""
        styles = {}

        # Header name style (matching \Huge \scshape)
        styles['name'] = ParagraphStyle(
            'Name',
            fontName='Helvetica-Bold',
            fontSize=self.FONT_NAME_HEADER,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=2,
            spaceBefore=0,
            leading=self.FONT_NAME_HEADER + 2
        )

        # Contact info style (matching \small with links)
        styles['contact'] = ParagraphStyle(
            'Contact',
            fontName='Helvetica',
            fontSize=self.FONT_CONTACT,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=self.SPACE_AFTER_HEADER,
            spaceBefore=0,
            leading=self.FONT_CONTACT * 1.3
        )

        # Section heading (matching \scshape\raggedright\large with titlerule)
        styles['section'] = ParagraphStyle(
            'SectionHeading',
            fontName='Helvetica-Bold',
            fontSize=self.FONT_SECTION_TITLE,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=3,
            spaceBefore=6,
            leading=self.FONT_SECTION_TITLE + 2
        )

        # Company/Project name (matching \textbf)
        styles['company'] = ParagraphStyle(
            'Company',
            fontName='Helvetica-Bold',
            fontSize=self.FONT_COMPANY,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0
        )

        # Job title (matching \textit{\small})
        styles['title'] = ParagraphStyle(
            'Title',
            fontName='Helvetica-Oblique',
            fontSize=self.FONT_TITLE,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=2,
            spaceBefore=0
        )

        # Bullet points (matching \small with proper hanging indent)
        # CRITICAL FIX: Use negative firstLineIndent to create hanging indent
        # leftIndent = where wrapped text aligns (0.15in)
        # firstLineIndent = -0.1in pulls bullet back to 0.05in
        # Result: bullet at 0.05in, text starts beside it, wraps align at 0.15in
        styles['bullet'] = ParagraphStyle(
            'Bullet',
            fontName='Helvetica',
            fontSize=self.FONT_BODY,
            textColor=colors.black,
            alignment=TA_LEFT,
            leftIndent=0.15 * inch,  # Where text aligns when it wraps
            firstLineIndent=-0.10 * inch,  # Negative to pull bullet back (hanging indent)
            spaceAfter=self.SPACE_BULLET,
            spaceBefore=0,
            leading=self.FONT_BODY * 1.3  # Good line height for readability
        )

        # Dates (matching \textit{\small})
        styles['dates'] = ParagraphStyle(
            'Dates',
            fontName='Helvetica-Oblique',
            fontSize=self.FONT_DATES,
            textColor=colors.black,
            alignment=TA_LEFT
        )

        # Scope/Technologies label style (bold label)
        styles['scope_label'] = ParagraphStyle(
            'ScopeLabel',
            fontName='Helvetica-Bold',
            fontSize=self.FONT_SCOPE_LABEL,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0
        )

        # Regular text style (for content after labels)
        styles['regular_text'] = ParagraphStyle(
            'RegularText',
            fontName='Helvetica',
            fontSize=self.FONT_BODY,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=3,
            spaceBefore=0,
            leading=self.FONT_BODY * 1.3
        )

        # Technologies style (for tech list after label)
        styles['technologies'] = ParagraphStyle(
            'Technologies',
            fontName='Helvetica',
            fontSize=self.FONT_BODY,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=5,
            spaceBefore=0,
            leading=self.FONT_BODY * 1.2
        )

        return styles

    def _add_horizontal_rule(self):
        """Add section separator line (matching \titlerule)"""
        from reportlab.platypus import HRFlowable
        rule = HRFlowable(
            width=self.CONTENT_WIDTH,
            thickness=0.5,
            color=colors.black,
            spaceAfter=self.SPACE_AFTER_SECTION,
            spaceBefore=0
        )
        self.story.append(rule)

    def add_header(self, name: str, phone: str, email: str,
                   linkedin: str, github: str, leetcode: str = ""):
        """
        Add resume header matching LaTeX format with proper hyperlinks
        LaTeX structure:
        \begin{center}
            \textbf{\Huge \scshape NAME} \\ \vspace{1pt}
            \small PHONE $|$ \href{mailto:EMAIL}{EMAIL} $|$ \href{URL}{LINKEDIN} $|$ \href{URL}{GITHUB}
        \end{center}
        """
        # Name
        name_para = Paragraph(name.upper(), self.styles['name'])
        self.story.append(name_para)
        self.story.append(Spacer(1, 0.05 * inch))

        # Contact info - with proper hyperlinks (underlined)
        contact_parts = [phone]

        # Email with mailto link
        if email:
            email_link = f'<link href="mailto:{email}" color="black"><u>{email}</u></link>'
            contact_parts.append(email_link)

        # LinkedIn with link
        if linkedin:
            # Extract just the display text (e.g., "linkedin.com/in/username")
            linkedin_display = linkedin.replace('https://', '').replace('http://', '')
            linkedin_link = f'<link href="{linkedin}" color="black"><u>{linkedin_display}</u></link>'
            contact_parts.append(linkedin_link)

        # GitHub with link
        if github:
            github_display = github.replace('https://', '').replace('http://', '')
            github_link = f'<link href="{github}" color="black"><u>{github_display}</u></link>'
            contact_parts.append(github_link)

        # LeetCode with link
        if leetcode:
            leetcode_display = leetcode.replace('https://', '').replace('http://', '')
            leetcode_link = f'<link href="{leetcode}" color="black"><u>{leetcode_display}</u></link>'
            contact_parts.append(leetcode_link)

        contact_line = " | ".join(contact_parts)
        contact_para = Paragraph(contact_line, self.styles['contact'])
        self.story.append(contact_para)
        self.story.append(Spacer(1, self.SPACE_AFTER_HEADER))

    def add_section(self, title: str):
        """
        Add section heading with horizontal rule
        Matching LaTeX: \section{TITLE} with \titlerule
        """
        section_para = Paragraph(title.upper(), self.styles['section'])
        self.story.append(section_para)
        self._add_horizontal_rule()

    def add_education(self, university: str, degree: str,
                      location: str, dates: str):
        """
        Add education entry matching LaTeX \resumeSubheading
        Layout: [University] [Location]
                [Degree]     [Dates]
        """
        # Create table for two-column layout
        data = [
            [Paragraph(f"<b>{university}</b>", self.styles['company']),
             Paragraph(location, self.styles['dates'])],
            [Paragraph(f"<i>{degree}</i>", self.styles['title']),
             Paragraph(f"<i>{dates}</i>", self.styles['dates'])]
        ]

        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.30])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)
        self.story.append(Spacer(1, self.SPACE_BETWEEN_ITEMS))

    def add_experience_entry(self, company: str, title: str, dates: str,
                             technologies: str, location: str,
                             description_points: List[str], scope: str = ""):
        """
        Add experience entry matching LaTeX format
        Layout: [Company | Title]                    [Dates]
                [Technologies]                        [Location]
                Scope: description text (if provided)
                • Bullet points
                Technologies: tech1, tech2, tech3
        """
        # First row: Company | Title and Dates
        company_title = f"<b>{company}</b> | <i>{title}</i>"
        data = [
            [Paragraph(company_title, self.styles['company']),
             Paragraph(f"<i>{dates}</i>", self.styles['dates'])]
        ]

        # Second row: Technologies and Location (both italic)
        if technologies or location:
            data.append([
                Paragraph(f"<i>{technologies}</i>", self.styles['title']),
                Paragraph(f"<i>{location}</i>", self.styles['dates'])
            ])

        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.30])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)

        # Add Scope section if provided (bold label + regular text)
        if scope:
            scope_text = f"<b>Scope:</b> {scope}"
            scope_para = Paragraph(scope_text, self.styles['regular_text'])
            self.story.append(scope_para)
            self.story.append(Spacer(1, 0.03 * inch))

        # Add bullet points
        if description_points:
            for point in description_points:
                bullet_text = f"• {point}"
                bullet_para = Paragraph(bullet_text, self.styles['bullet'])
                self.story.append(bullet_para)

        # Add Technologies line at the end (bold label + regular text)
        if technologies:
            tech_text = f"<b>Technologies:</b> {technologies}"
            tech_para = Paragraph(tech_text, self.styles['technologies'])
            self.story.append(tech_para)

        self.story.append(Spacer(1, self.SPACE_BETWEEN_ITEMS))

    def add_project_entry(self, title: str, technologies: str,
                          dates: str, description_points: List[str]):
        """
        Add project entry matching LaTeX \resumeProjectHeading
        Layout: [Title | Technologies] [Dates]
                • Bullet points
        """
        project_heading = f"<b>{title}</b> | <i>{technologies}</i>"
        data = [[Paragraph(project_heading, self.styles['company']),
                 Paragraph(dates, self.styles['dates'])]]

        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.75,
                                       self.CONTENT_WIDTH * 0.25])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)

        # Add bullet points
        if description_points:
            for point in description_points:
                bullet_text = f"• {point}"
                bullet_para = Paragraph(bullet_text, self.styles['bullet'])
                self.story.append(bullet_para)

        self.story.append(Spacer(1, self.SPACE_BETWEEN_ITEMS))

    def add_skills(self, skills_list: List[str], tools_list: List[str]):
        """
        Add skills section matching LaTeX format
        • Skills: skill1, skill2, skill3.
        • Tools: tool1, tool2, tool3.
        """
        if skills_list:
            skills_text = ", ".join(skills_list) + "."
            skills_para = Paragraph(f"<b>Skills:</b> {skills_text}",
                                    self.styles['bullet'])
            self.story.append(skills_para)

        if tools_list:
            tools_text = ", ".join(tools_list) + "."
            tools_para = Paragraph(f"<b>Tools:</b> {tools_text}",
                                   self.styles['bullet'])
            self.story.append(tools_para)

    def _estimate_content_height(self) -> float:
        """
        Estimate total content height to check if it fits on one page
        This is approximate - ReportLab will handle final layout
        """
        # This is a rough estimate - actual rendering may vary
        total_height = 0
        for flowable in self.story:
            if hasattr(flowable, 'wrap'):
                w, h = flowable.wrap(self.CONTENT_WIDTH, self.max_height)
                total_height += h
        return total_height

    def _auto_compress(self):
        """
        Auto-compress content if it exceeds one page
        Iteratively reduces spacing and font sizes until content fits
        """
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            estimated_height = self._estimate_content_height()

            if estimated_height <= self.max_height:
                if iteration > 0:
                    logger.info(f"Content compressed to fit one page after {iteration} iteration(s)")
                break

            iteration += 1
            overage = estimated_height - self.max_height
            logger.warning(f"Content height ({estimated_height:.1f}) exceeds page ({self.max_height:.1f}) by {overage:.1f}. Compressing (iteration {iteration})...")

            # Calculate aggressive compression factor
            compression_factor = self.max_height / estimated_height
            # Make it more aggressive
            compression_factor = compression_factor * 0.95

            # Adjust styles more aggressively
            for style_name, style in self.styles.items():
                current_font_size = style.fontSize if hasattr(style, 'fontSize') else 10

                if hasattr(style, 'fontSize'):
                    # Reduce font more aggressively, min 7pt for body text
                    style.fontSize = max(7, style.fontSize * 0.93)

                if hasattr(style, 'spaceAfter'):
                    # Reduce spacing more
                    style.spaceAfter = max(0, style.spaceAfter * compression_factor)

                if hasattr(style, 'spaceBefore'):
                    style.spaceBefore = max(0, style.spaceBefore * compression_factor)

                if hasattr(style, 'leading'):
                    # Reduce line height but keep it at minimum 1.0x font size for readability
                    new_leading = style.leading * 0.93
                    min_leading = current_font_size * 1.0  # Minimum 1.0x font size
                    style.leading = max(min_leading, new_leading)

        # Final check
        final_height = self._estimate_content_height()
        if final_height > self.max_height:
            logger.error(f"WARNING: Content may still exceed one page (est: {final_height:.1f} vs max: {self.max_height:.1f})")
        else:
            logger.info(f"✓ Content fits on one page (est: {final_height:.1f} vs max: {self.max_height:.1f})")

    def build_resume(self, resume_data: Dict, output_path: str) -> str:
        """
        Build complete one-page resume PDF
        Args:
            resume_data: Dict with 'experience', 'projects', 'skills', 'education'
            output_path: Full path for output PDF
        Returns:
            Path to generated PDF
        """
        logger.info(f"Building one-page resume: {output_path}")

        # Reset story
        self.story = []

        # 1. HEADER
        name = getattr(config, 'YOUR_NAME', 'Your Name') if config else 'Your Name'
        phone = getattr(config, 'YOUR_PHONE', '') if config else ''
        email = getattr(config, 'YOUR_EMAIL', '') if config else ''
        linkedin_text = getattr(config, 'YOUR_LINKEDIN_URL_TEXT', '') if config else ''
        github_text = getattr(config, 'YOUR_GITHUB_URL_TEXT', '') if config else ''
        leetcode_text = getattr(config, 'YOUR_LEETCODE_URL_TEXT', '') if config else ''

        self.add_header(name, phone, email, linkedin_text, github_text, leetcode_text)

        # 2. EDUCATION
        self.add_section("Education")
        education_data = resume_data.get('education', [])
        if education_data and len(education_data) > 0:
            edu = education_data[0]  # Take first education entry
            self.add_education(
                university=edu.get('university', ''),
                degree=edu.get('degree', ''),
                location=edu.get('location', ''),
                dates=edu.get('dates', '')
            )

        # 3. EXPERIENCE
        self.add_section("Experience")
        for exp in resume_data.get('experience', []):
            self.add_experience_entry(
                company=exp.get('company', ''),
                title=exp.get('title', ''),
                dates=exp.get('dates', ''),
                technologies=exp.get('technologies', ''),
                location=exp.get('location', ''),
                description_points=exp.get('description', []),
                scope=exp.get('scope', '')  # Optional scope field
            )

        # 4. PROJECTS
        self.add_section("Projects")
        for proj in resume_data.get('projects', []):
            self.add_project_entry(
                title=proj.get('title', ''),
                technologies=proj.get('technologies', ''),
                dates=proj.get('dates', ''),
                description_points=proj.get('description', [])
            )

        # 5. SKILLS
        self.add_section("Technical Skills")
        skills_data = resume_data.get('skills', {})
        if isinstance(skills_data, dict):
            skills_list = skills_data.get('skills_list', [])
            tools_list = skills_data.get('tools_list', [])
            self.add_skills(skills_list, tools_list)

        # Auto-compress if needed
        self._auto_compress()

        # Build PDF
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                leftMargin=self.MARGIN_LEFT,
                rightMargin=self.MARGIN_RIGHT,
                topMargin=self.MARGIN_TOP,
                bottomMargin=self.MARGIN_BOTTOM,
                title=f"{name} - Resume"
            )

            doc.build(self.story)
            logger.info(f"Successfully generated resume PDF: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to build resume PDF: {e}", exc_info=True)
            return None


def create_resume_reportlab(resume_data: Dict, output_dir: str, filename_base: str) -> str:
    """
    Main function to create resume using ReportLab
    Replicates exact LaTeX styling with one-page guarantee

    Args:
        resume_data: Tailored resume data from tailor.py
        output_dir: Directory to save PDF
        filename_base: Base filename (without extension)

    Returns:
        Full path to generated PDF
    """
    output_path = Path(output_dir) / f"{filename_base}.pdf"

    # Use pixel-perfect LaTeX matcher
    from document_generator.resume_perfect_latex import PerfectLaTeXResume
    generator = PerfectLaTeXResume()
    result = generator.build_resume(resume_data, str(output_path))

    return result


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Test data
    test_resume = {
        'education': [{
            'university': 'Syracuse University',
            'degree': 'Master of Science in Computer Science',
            'location': 'Syracuse, NY',
            'dates': 'Aug 2024 -- Dec 2025'
        }],
        'experience': [
            {
                'company': 'Deloitte',
                'title': 'Senior Software Engineer',
                'dates': 'Feb 2021 – Jan 2024',
                'technologies': 'React, D3.js, Node.js, TypeScript, AWS',
                'location': 'Bangalore, India',
                'description': [
                    'Designed and implemented responsive dashboards using React.js and Redux, increasing user interaction by 35%',
                    'Leveraged D3.js for real-time data visualizations, reducing decision-making time by 25%',
                ]
            }
        ],
        'projects': [
            {
                'title': 'ScanFeast Mobile App',
                'technologies': 'React, Redux, Firebase',
                'dates': 'Aug 2024 – Present',
                'description': [
                    'Developed React app for restaurant ordering, increasing efficiency by 20%',
                    'Integrated Firebase for backend operations, improving data retrieval by 30%'
                ]
            }
        ],
        'skills': {
            'skills_list': ['Python', 'JavaScript', 'React', 'Node.js', 'AWS'],
            'tools_list': ['Docker', 'Git', 'MongoDB', 'Redis']
        }
    }

    output_path = create_resume_reportlab(
        test_resume,
        '/tmp',
        'Test_Resume'
    )

    if output_path:
        print(f"\n✓ Resume generated: {output_path}")
