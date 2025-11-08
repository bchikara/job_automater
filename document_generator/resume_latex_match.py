#!/usr/bin/env python3
"""
LaTeX-Matching Resume Generator using ReportLab
Pixel-perfect recreation of Jake Gutierrez LaTeX resume template
"""

import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, ListStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
from typing import Dict, List
import config

logger = logging.getLogger(__name__)


class LaTeXMatchingResume:
    """
    Generate resume that exactly matches LaTeX template
    Based on: https://github.com/sb2nov/resume
    """

    # LaTeX uses letterpaper with these exact margins
    PAGE_WIDTH = letter[0]  # 8.5 inches
    PAGE_HEIGHT = letter[1]  # 11 inches

    # Margins from LaTeX: \addtolength{\oddsidemargin}{-0.5in} etc.
    # Default LaTeX margins are 1in, so: 1 - 0.5 = 0.5in
    MARGIN_LEFT = 0.5 * inch
    MARGIN_RIGHT = 0.5 * inch
    MARGIN_TOP = 0.5 * inch  # 1 - 0.5
    MARGIN_BOTTOM = 0.5 * inch  # Actually gets more space due to \textheight increase

    # Content area
    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # 7.5 inches
    CONTENT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM + 1.0 * inch  # +1.0in from \textheight

    # LaTeX 11pt document font sizes (in points)
    # \Huge at 11pt base = ~25pt, \large = ~14pt, \small = ~10pt, \tiny = ~6pt
    FONT_SIZE_HUGE = 25  # \Huge \scshape NAME
    FONT_SIZE_LARGE = 14  # \large for section headers
    FONT_SIZE_NORMAL = 11  # Base font size
    FONT_SIZE_SMALL = 10  # \small for most content
    FONT_SIZE_TINY = 6  # \tiny for bullets (actually uses normal small bullet)

    # Spacing from LaTeX
    VSPACE_AFTER_NAME = 1  # \vspace{1pt}
    VSPACE_BEFORE_SECTION = -4  # \vspace{-4pt}
    VSPACE_AFTER_SECTION_RULE = -5  # \vspace{-5pt}
    VSPACE_BEFORE_SUBHEADING = -2  # \vspace{-2pt}
    VSPACE_AFTER_SUBHEADING = -7  # \vspace{-7pt}
    VSPACE_AFTER_ITEM = -2  # \vspace{-2pt}
    VSPACE_AFTER_ITEMLIST = -5  # \vspace{-5pt}

    # Bullet list settings from LaTeX: [leftmargin=0.15in, label={}]
    BULLET_LEFT_MARGIN = 0.15 * inch
    BULLET_INDENT = 0  # Bullet at margin
    BULLET_TEXT_INDENT = 0.15 * inch  # Text indent after bullet

    def __init__(self):
        """Initialize resume generator with LaTeX-matching styles"""
        self.styles = self._create_latex_styles()
        self.story = []
        # Target 93% of content height for safety
        self.max_height = self.CONTENT_HEIGHT * 0.90

    def _create_latex_styles(self) -> Dict[str, ParagraphStyle]:
        """Create paragraph styles that exactly match LaTeX output"""
        styles = {}

        # NAME: \textbf{\Huge \scshape NAME}
        # \scshape = small caps, \Huge = 25pt
        styles['name'] = ParagraphStyle(
            'Name',
            fontName='Helvetica-Bold',  # Closest to LaTeX bold
            fontSize=self.FONT_SIZE_HUGE,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=self.VSPACE_AFTER_NAME,
            spaceBefore=0,
            leading=self.FONT_SIZE_HUGE * 1.2,
            textTransform='uppercase'  # Simulate small caps
        )

        # Contact info: \small with underline for links
        styles['contact'] = ParagraphStyle(
            'Contact',
            fontName='Helvetica',
            fontSize=self.FONT_SIZE_SMALL,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_SIZE_SMALL * 1.3
        )

        # Section header: \scshape\raggedright\large
        styles['section'] = ParagraphStyle(
            'SectionHeading',
            fontName='Helvetica-Bold',
            fontSize=self.FONT_SIZE_LARGE,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=self.VSPACE_AFTER_SECTION_RULE,
            spaceBefore=self.VSPACE_BEFORE_SECTION,
            leading=self.FONT_SIZE_LARGE * 1.2,
            textTransform='uppercase'
        )

        # Company/Project name: \textbf
        styles['heading_bold'] = ParagraphStyle(
            'HeadingBold',
            fontName='Helvetica-Bold',
            fontSize=self.FONT_SIZE_NORMAL,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_SIZE_NORMAL * 1.2
        )

        # Job title/technologies: \textit{\small}
        styles['heading_italic'] = ParagraphStyle(
            'HeadingItalic',
            fontName='Helvetica-Oblique',
            fontSize=self.FONT_SIZE_SMALL,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_SIZE_SMALL * 1.2
        )

        # Dates: \textit{\small} (right-aligned)
        styles['dates'] = ParagraphStyle(
            'Dates',
            fontName='Helvetica-Oblique',
            fontSize=self.FONT_SIZE_SMALL,
            textColor=colors.black,
            alignment=TA_LEFT,  # Will be right-aligned via table
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_SIZE_SMALL * 1.2
        )

        # Bullet point text: \item\small
        styles['bullet'] = ParagraphStyle(
            'Bullet',
            fontName='Helvetica',
            fontSize=self.FONT_SIZE_SMALL,
            textColor=colors.black,
            alignment=TA_LEFT,
            leftIndent=0,
            spaceAfter=abs(self.VSPACE_AFTER_ITEM),  # Tiny space after each item
            spaceBefore=0,
            leading=self.FONT_SIZE_SMALL * 1.3,  # Slightly more than LaTeX for readability
            bulletIndent=0
        )

        # Skills text: \small
        styles['skills'] = ParagraphStyle(
            'Skills',
            fontName='Helvetica',
            fontSize=self.FONT_SIZE_SMALL,
            textColor=colors.black,
            alignment=TA_LEFT,
            leftIndent=0,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_SIZE_SMALL * 1.3
        )

        return styles

    def _add_horizontal_rule(self):
        """Add section separator line: \titlerule"""
        from reportlab.platypus import HRFlowable
        # LaTeX \titlerule creates a thin line
        rule = HRFlowable(
            width=self.CONTENT_WIDTH,
            thickness=0.4,  # Very thin line
            color=colors.black,
            spaceAfter=abs(self.VSPACE_AFTER_SECTION_RULE),
            spaceBefore=0
        )
        self.story.append(rule)

    def add_header(self, name: str, phone: str, email: str,
                   linkedin: str, github: str, leetcode: str = ""):
        """
        Add header matching LaTeX:
        \textbf{\Huge \scshape NAME}
        \small PHONE | EMAIL | LINKEDIN | GITHUB
        """
        # Name (uppercase, bold, huge)
        name_para = Paragraph(name.upper(), self.styles['name'])
        self.story.append(name_para)

        # Contact line with underlined links
        contact_parts = []

        # Phone (no link)
        contact_parts.append(phone)

        # Email with underline
        if email:
            contact_parts.append(f'<u>{email}</u>')

        # LinkedIn with underline
        if linkedin:
            linkedin_display = linkedin.replace('https://', '').replace('http://', '')
            contact_parts.append(f'<u>{linkedin_display}</u>')

        # GitHub with underline
        if github:
            github_display = github.replace('https://', '').replace('http://', '')
            contact_parts.append(f'<u>{github_display}</u>')

        # LeetCode with underline
        if leetcode:
            leetcode_display = leetcode.replace('https://', '').replace('http://', '')
            contact_parts.append(f'<u>{leetcode_display}</u>')

        contact_line = " | ".join(contact_parts)
        contact_para = Paragraph(contact_line, self.styles['contact'])
        self.story.append(contact_para)
        self.story.append(Spacer(1, 0.1 * inch))

    def add_section(self, title: str):
        """
        Add section header with underline:
        \section{TITLE} -> creates \large title with \titlerule
        """
        # Add small space before section (LaTeX \vspace{-4pt} is negative, but we need some space)
        self.story.append(Spacer(1, 0.05 * inch))

        section_para = Paragraph(title.upper(), self.styles['section'])
        self.story.append(section_para)
        self._add_horizontal_rule()

    def add_education_entry(self, university: str, location: str,
                           degree: str, dates: str):
        """
        Add education entry matching \resumeSubheading:
        \textbf{University} & Location
        \textit{\small Degree} & \textit{\small Dates}
        """
        # Row 1: University (bold) | Location
        # Row 2: Degree (italic small) | Dates (italic small)
        data = [
            [Paragraph(f"<b>{university}</b>", self.styles['heading_bold']),
             Paragraph(location, self.styles['dates'])],
            [Paragraph(f"<i>{degree}</i>", self.styles['heading_italic']),
             Paragraph(f"<i>{dates}</i>", self.styles['dates'])]
        ]

        # LaTeX uses 0.97\textwidth for table
        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.27])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)
        # LaTeX: \vspace{-7pt} after subheading
        self.story.append(Spacer(1, 0.05 * inch))

    def add_experience_entry(self, company: str, title: str, dates: str,
                            technologies: str, location: str,
                            bullet_points: List[str]):
        """
        Add experience entry matching LaTeX format:
        \textbf{Company | Title} & Dates
        \textit{Technologies} & \textit{Location}
        \resumeItemListStart
          \resumeItem{...}
        \resumeItemListEnd
        """
        # Row 1: Company | Title (both bold/italic) | Dates
        company_title = f"<b>{company}</b> | <i>{title}</i>"

        data = [
            [Paragraph(company_title, self.styles['heading_bold']),
             Paragraph(f"<i>{dates}</i>", self.styles['dates'])]
        ]

        # Row 2: Technologies (italic) | Location (italic)
        if technologies or location:
            data.append([
                Paragraph(f"<i>Technologies: {technologies}</i>", self.styles['heading_italic']),
                Paragraph(f"<i>{location}</i>", self.styles['dates'])
            ])

        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.27])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)

        # Add bullet points using paragraphs with proper indentation
        if bullet_points:
            # LaTeX: \resumeItemListStart = \begin{itemize}
            # Add small space before list
            self.story.append(Spacer(1, 0.02 * inch))

            for point in bullet_points:
                # Create bullet text with proper formatting
                # Use bullet character • followed by space
                bullet_text = f"• {point}"

                # Create paragraph with left indent for the bullet effect
                # The bullet and text will be on the same line
                bullet_para = Paragraph(bullet_text, self.styles['bullet'])
                self.story.append(bullet_para)

            # Add small space after list (LaTeX: \vspace{-5pt})
            self.story.append(Spacer(1, abs(self.VSPACE_AFTER_ITEMLIST) / 72.0 * inch))

        # Space after entry
        self.story.append(Spacer(1, 0.05 * inch))

    def add_project_entry(self, title: str, technologies: str, dates: str,
                         bullet_points: List[str]):
        """
        Add project entry matching \resumeProjectHeading:
        \textbf{Title | Technologies} & Dates
        \resumeItemListStart...
        """
        # Project heading with technologies
        project_heading = f"<b>{title}</b> | <i>{technologies}</i>"

        data = [[
            Paragraph(project_heading, self.styles['heading_bold']),
            Paragraph(f"<i>{dates}</i>", self.styles['dates'])
        ]]

        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.27])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)

        # Add bullet points
        if bullet_points:
            bullet_items = []
            for point in bullet_points:
                item = ListItem(
                    Paragraph(point, self.styles['bullet']),
                    leftIndent=self.BULLET_LEFT_MARGIN,
                    bulletOffsetY=-2
                )
                bullet_items.append(item)

            bullet_list = ListFlowable(
                bullet_items,
                bulletType='bullet',
                bulletFontSize=6,
                bulletOffsetY=-1,
                leftIndent=self.BULLET_LEFT_MARGIN,
                spaceBefore=2,
                spaceAfter=abs(self.VSPACE_AFTER_ITEMLIST)
            )
            self.story.append(bullet_list)

        self.story.append(Spacer(1, 0.05 * inch))

    def add_skills(self, skills_list: List[str], tools_list: List[str]):
        """
        Add skills section matching LaTeX:
        \textbf{Skills:} skill1, skill2, skill3
        \textbf{Tools:} tool1, tool2, tool3
        """
        if skills_list:
            skills_text = ", ".join(skills_list)
            skills_para = Paragraph(
                f"<b>Skills:</b> {skills_text}",
                self.styles['skills']
            )
            # Use list item with no bullet for proper indentation
            skill_item = ListItem(
                skills_para,
                leftIndent=self.BULLET_LEFT_MARGIN,
                bulletType='1'  # No bullet
            )
            self.story.append(skill_item)

        if tools_list:
            tools_text = ", ".join(tools_list)
            tools_para = Paragraph(
                f"<b>Tools:</b> {tools_text}",
                self.styles['skills']
            )
            tool_item = ListItem(
                tools_para,
                leftIndent=self.BULLET_LEFT_MARGIN,
                bulletType='1'  # No bullet
            )
            self.story.append(tool_item)

    def _estimate_content_height(self) -> float:
        """Estimate total content height"""
        total_height = 0
        for flowable in self.story:
            if hasattr(flowable, 'wrap'):
                try:
                    w, h = flowable.wrap(self.CONTENT_WIDTH, self.max_height * 2)
                    total_height += h
                except:
                    total_height += 20  # Default height for items that fail to wrap
        return total_height

    def _auto_compress(self):
        """Compress content if needed"""
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            estimated_height = self._estimate_content_height()

            if estimated_height <= self.max_height:
                if iteration > 0:
                    logger.info(f"Content compressed after {iteration} iteration(s)")
                break

            iteration += 1
            logger.warning(f"Content height ({estimated_height:.1f}) exceeds ({self.max_height:.1f}). Compressing...")

            compression_factor = self.max_height / estimated_height * 0.95

            for style_name, style in self.styles.items():
                if hasattr(style, 'fontSize'):
                    style.fontSize = max(8, style.fontSize * 0.94)
                if hasattr(style, 'spaceAfter'):
                    style.spaceAfter = max(0, style.spaceAfter * compression_factor)
                if hasattr(style, 'leading'):
                    style.leading = max(style.fontSize * 1.1, style.leading * 0.94)

        final_height = self._estimate_content_height()
        if final_height <= self.max_height:
            logger.info(f"✓ Content fits (est: {final_height:.1f} vs max: {self.max_height:.1f})")
        else:
            logger.warning(f"⚠ Content may exceed one page (est: {final_height:.1f})")

    def build_resume(self, resume_data: Dict, output_path: str) -> str:
        """Build complete resume PDF matching LaTeX template"""
        logger.info(f"Building LaTeX-matching resume: {output_path}")

        self.story = []

        # 1. HEADER
        name = getattr(config, 'YOUR_NAME', 'Your Name')
        phone = getattr(config, 'YOUR_PHONE', '')
        email = getattr(config, 'YOUR_EMAIL', '')
        linkedin = getattr(config, 'YOUR_LINKEDIN_URL', '')
        github = getattr(config, 'YOUR_GITHUB_URL', '')
        leetcode = getattr(config, 'YOUR_LEETCODE_URL', '')

        self.add_header(name, phone, email, linkedin, github, leetcode)

        # 2. EDUCATION
        self.add_section("Education")
        education_data = resume_data.get('education', [])
        if education_data:
            for edu in education_data:
                self.add_education_entry(
                    university=edu.get('university', ''),
                    location=edu.get('location', ''),
                    degree=edu.get('degree', ''),
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
                bullet_points=exp.get('description', [])
            )

        # 4. PROJECTS
        self.add_section("Projects")
        for proj in resume_data.get('projects', []):
            self.add_project_entry(
                title=proj.get('title', ''),
                technologies=proj.get('technologies', ''),
                dates=proj.get('dates', ''),
                bullet_points=proj.get('description', [])
            )

        # 5. TECHNICAL SKILLS
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
            logger.info(f"✓ LaTeX-matching resume PDF generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}", exc_info=True)
            raise


def generate_latex_matching_resume(resume_data: Dict, output_path: str) -> str:
    """Main entry point for LaTeX-matching resume generation"""
    generator = LaTeXMatchingResume()
    return generator.build_resume(resume_data, output_path)
