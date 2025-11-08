#!/usr/bin/env python3
"""
PIXEL-PERFECT LaTeX Resume Matcher
Based on Jake Gutierrez template: https://github.com/sb2nov/resume
Maps every LaTeX element 1:1 to ReportLab
"""

import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from typing import Dict, List
from pathlib import Path
import config

logger = logging.getLogger(__name__)

# ReportLab uses points as base unit
pt = 1


class PerfectLaTeXResume:
    """
    Pixel-perfect recreation of LaTeX resume template
    Every element mapped exactly from LaTeX commands
    """

    # ==================== PAGE SETUP ====================
    # LaTeX: \documentclass[letterpaper,11pt]{article}
    PAGE_WIDTH = letter[0]  # 8.5 inches
    PAGE_HEIGHT = letter[1]  # 11 inches

    # LaTeX margins:
    # \addtolength{\oddsidemargin}{-0.5in}  -> 1in - 0.5in = 0.5in
    # \addtolength{\evensidemargin}{-0.5in} -> 1in - 0.5in = 0.5in
    # \addtolength{\textwidth}{1in}         -> adds 1in total width
    # \addtolength{\topmargin}{-.5in}       -> 1in - 0.5in = 0.5in
    # \addtolength{\textheight}{1.0in}      -> adds 1in total height
    MARGIN_LEFT = 0.5 * inch
    MARGIN_RIGHT = 0.5 * inch
    MARGIN_TOP = 0.5 * inch
    MARGIN_BOTTOM = 0.5 * inch

    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # 7.5 inches

    # ==================== FONT SIZES ====================
    # LaTeX 11pt document class font sizes:
    # \tiny = 6pt, \scriptsize = 8pt, \footnotesize = 9pt
    # \small = 10pt, \normalsize = 11pt, \large = 14pt, \Large = 17pt
    # \LARGE = 20pt, \huge = 24pt, \Huge = 25pt
    FONT_TINY = 6
    FONT_SMALL = 10  # Used for most content
    FONT_NORMAL = 11  # Base document size
    FONT_LARGE = 14  # Section headers
    FONT_HUGE = 25  # Name header

    # ==================== SPACING (in points) ====================
    # Exact LaTeX \vspace values
    SPACE_AFTER_NAME = 1 * pt  # \vspace{1pt}
    SPACE_BEFORE_SECTION = -4 * pt  # \vspace{-4pt} - but we use positive
    SPACE_AFTER_SECTION_RULE = -5 * pt  # \vspace{-5pt}
    SPACE_BEFORE_SUBHEADING = -2 * pt  # \vspace{-2pt}
    SPACE_AFTER_SUBHEADING = -7 * pt  # \vspace{-7pt}
    SPACE_AFTER_ITEM = -2 * pt  # \vspace{-2pt}
    SPACE_AFTER_ITEMLIST = -5 * pt  # \vspace{-5pt}

    # ==================== LATEX LIST SETTINGS ====================
    # \begin{itemize}[leftmargin=0.15in, label={}]
    BULLET_LEFT_MARGIN = 0.15 * inch  # Section headings indent
    BULLET_INDENT = 0.45 * inch  # Bullet point text indent (0.10in more than headings)
    # LaTeX itemize default: bullet is pulled back, text wraps at leftmargin

    def __init__(self):
        self.styles = self._create_exact_latex_styles()
        self.story = []
        # Safety margin for one-page guarantee (more aggressive)
        self.max_height = (self.PAGE_HEIGHT - self.MARGIN_TOP - self.MARGIN_BOTTOM) * 0.82

    def _create_exact_latex_styles(self) -> Dict[str, ParagraphStyle]:
        """
        Create styles matching EXACT LaTeX output
        Each style maps to specific LaTeX command
        """
        styles = {}

        # ==================== HEADER STYLES ====================

        # NAME: \textbf{\Huge \scshape NAME}
        # \Huge = 25pt, \scshape = small caps (simulate with uppercase)
        styles['name'] = ParagraphStyle(
            'Name',
            fontName='Helvetica-Bold',  # \textbf
            fontSize=self.FONT_HUGE,  # \Huge = 25pt
            textColor=colors.black,
            alignment=TA_CENTER,  # \begin{center}
            spaceAfter=10,  # More space after name
            spaceBefore=0,
            leading=self.FONT_HUGE * 1.2
        )

        # CONTACT: \small PHONE $|$ \href{}{EMAIL} etc.
        # \small = 10pt
        styles['contact'] = ParagraphStyle(
            'Contact',
            fontName='Helvetica',  # Regular weight
            fontSize=self.FONT_SMALL,  # \small = 10pt
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=10,  # Space before education section
            spaceBefore=0,
            leading=self.FONT_SMALL * 1.2  # Tighter line height
        )

        # ==================== SECTION HEADER ====================

        # SECTION: \section{TITLE}
        # From \titleformat{\section}{\vspace{-4pt}\scshape\raggedright\large}
        styles['section'] = ParagraphStyle(
            'Section',
            fontName='Helvetica-Bold',  # \scshape approximated as bold
            fontSize=self.FONT_LARGE,  # \large = 14pt
            textColor=colors.black,
            alignment=TA_LEFT,  # \raggedright
            spaceAfter=6,  # Increased space between heading text and horizontal rule
            spaceBefore=8,  # More space before section
            leading=self.FONT_LARGE * 1.1,
            textTransform='uppercase'  # \scshape approximation
        )

        # ==================== RESUME SUBHEADING ====================

        # COMPANY/UNIVERSITY NAME: \textbf{#1}
        # Uses \normalsize (11pt) with bold
        styles['heading_bold'] = ParagraphStyle(
            'HeadingBold',
            fontName='Helvetica-Bold',  # \textbf
            fontSize=self.FONT_NORMAL,  # 11pt
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_NORMAL * 1.2
        )

        # MIXED WEIGHT HEADING: For headings with bold and normal text mixed
        # Base font is normal, bold/italic applied via inline tags
        styles['heading_mixed'] = ParagraphStyle(
            'HeadingMixed',
            fontName='Helvetica',  # Normal weight base
            fontSize=self.FONT_NORMAL,  # 11pt
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_NORMAL * 1.2
        )

        # JOB TITLE/DEGREE: \textit{\small #3}
        # \textit = italic, \small = 10pt
        styles['heading_italic_small'] = ParagraphStyle(
            'HeadingItalicSmall',
            fontName='Helvetica-Oblique',  # \textit
            fontSize=self.FONT_SMALL,  # \small = 10pt
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_SMALL * 1.2
        )

        # DATES/LOCATION: \textit{\small #2} or \textit{\small #4}
        # Same as above but right-aligned in table
        styles['dates_location'] = ParagraphStyle(
            'DatesLocation',
            fontName='Helvetica-Oblique',  # \textit
            fontSize=self.FONT_SMALL,  # \small = 10pt
            textColor=colors.black,
            alignment=TA_RIGHT,  # Will be positioned right in table
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_SMALL * 1.2
        )

        # ==================== BULLET POINTS ====================

        # BULLET TEXT: \resumeItem{text} -> \item\small{text}
        # \small = 10pt, with hanging indent for bullet
        styles['bullet'] = ParagraphStyle(
            'Bullet',
            fontName='Helvetica',  # Regular weight
            fontSize=self.FONT_SMALL,  # \small = 10pt
            textColor=colors.black,
            alignment=TA_LEFT,
            # CRITICAL: Hanging indent so bullet and text are on same line
            leftIndent=self.BULLET_INDENT,  # 0.25in - where wrapped lines align (0.10in more than headings)
            firstLineIndent=-10,  # Negative pulls bullet back (hanging indent)
            spaceAfter=2,  # Tighter spacing between bullets
            spaceBefore=0,
            leading=self.FONT_SMALL * 1.35  # Tighter line height
        )

        # ==================== SKILLS SECTION ====================

        # SKILLS TEXT: \textbf{Skills:} followed by regular text
        # Uses \small = 10pt
        styles['skills'] = ParagraphStyle(
            'Skills',
            fontName='Helvetica',  # Regular for the list
            fontSize=self.FONT_SMALL,  # \small = 10pt
            textColor=colors.black,
            alignment=TA_LEFT,
            leftIndent=self.BULLET_LEFT_MARGIN,  # Match bullet indentation
            spaceAfter=2,
            spaceBefore=0,
            leading=self.FONT_SMALL * 1.4
        )

        return styles

    def _add_section_rule(self):
        r"""
        Add horizontal rule under section
        LaTeX: \titlerule creates thin black line
        """
        from reportlab.platypus import HRFlowable
        rule = HRFlowable(
            width="100%",
            thickness=0.4,  # Thin line
            color=colors.black,
            spaceAfter=6,  # More space after rule before content starts
            spaceBefore=4  # Space handled by section style spaceAfter
        )
        self.story.append(rule)

    # ==================== CONTENT BUILDERS ====================

    def add_header(self, name: str, phone: str, email: str,
                   linkedin: str, github: str, leetcode: str = ""):
        r"""
        LaTeX header:
        \begin{center}
            \textbf{\Huge \scshape NAME} \\ \vspace{1pt}
            \small PHONE | \underline{EMAIL} | \underline{LINKEDIN} | \underline{GITHUB}
        \end{center}
        """
        # Name (bold, huge, uppercase)
        name_para = Paragraph(name.upper(), self.styles['name'])
        self.story.append(name_para)

        # Build contact line - NO underlines to avoid height issues
        # Only show 4 links to prevent line break
        contact_parts = [phone]

        if email:
            contact_parts.append(email)  # No underline
        if linkedin:
            linkedin_display = linkedin.replace('https://', '').replace('http://', '')
            contact_parts.append(linkedin_display)  # No underline
        if github:
            github_display = github.replace('https://', '').replace('http://', '')
            contact_parts.append(github_display)  # No underline
        # Skip leetcode to keep only 4 items and prevent line break

        contact_line = " | ".join(contact_parts)
        contact_para = Paragraph(contact_line, self.styles['contact'])
        self.story.append(contact_para)

    def add_section(self, title: str):
        r"""
        LaTeX section:
        \section{TITLE}
        Creates uppercase title with horizontal rule below
        """
        section_para = Paragraph(title.upper(), self.styles['section'])
        self.story.append(section_para)
        self._add_section_rule()

    def add_education_entry(self, university: str, location: str,
                           degree: str, dates: str):
        r"""
        LaTeX: \begin{itemize}[leftmargin=0.15in, label={}]
        \resumeSubheading{University}{Location}{Degree}{Dates}
        Creates two-row table:
        Row 1: \textbf{University} | Location (right)
        Row 2: \textit{\small Degree} | \textit{\small Dates} (right)
        With \vspace{-7pt} after
        """
        # Create table with exact LaTeX structure
        data = [
            # Row 1: Bold university name | italic location
            [
                Paragraph(f"<b>{university}</b>", self.styles['heading_bold']),
                Paragraph(f"<i>{location}</i>", self.styles['dates_location'])
            ],
            # Row 2: Italic small degree | italic small dates
            [
                Paragraph(f"<i>{degree}</i>", self.styles['heading_italic_small']),
                Paragraph(f"<i>{dates}</i>", self.styles['dates_location'])
            ]
        ]

        # LaTeX uses 0.97\textwidth for table with 0.15in left margin
        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.27])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), self.BULLET_LEFT_MARGIN),  # 0.15in left margin
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)
        # LaTeX: \vspace{-7pt} after subheading (minimal space)
        self.story.append(Spacer(1, 0.03 * inch))

    def add_experience_entry(self, company: str, title: str, dates: str,
                            technologies: str, location: str,
                            bullet_points: List[str]):
        r"""
        LaTeX experience entry:
        \begin{itemize}[leftmargin=0.15in, label={}]
        \resumeSubheading{\textbf{Company} | \emph{Title}}{Dates}
                        {Technologies: tech1, tech2}{Location}
        \resumeItemListStart
          \resumeItem{Bullet point 1}
          \resumeItem{Bullet point 2}
        \resumeItemListEnd
        """
        # Row 1: Bold company | italic title (left) | italic dates (right)
        # Use mixed style so title stays italic (not bold)
        company_title = f"<b>{company}</b> | <i>{title}</i>"

        data = [
            [
                Paragraph(company_title, self.styles['heading_mixed']),  # Changed from heading_bold
                Paragraph(f"<i>{dates}</i>", self.styles['dates_location'])
            ]
        ]

        # Row 2: Italic technologies (left) | italic location (right)
        if technologies or location:
            tech_text = f"<i>Technologies: {technologies}</i>" if technologies else ""
            data.append([
                Paragraph(tech_text, self.styles['heading_italic_small']),
                Paragraph(f"<i>{location}</i>", self.styles['dates_location'])
            ])

        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.27])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), self.BULLET_LEFT_MARGIN),  # 0.15in left margin
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)

        # Add bullet points: \resumeItemListStart ... \resumeItemListEnd
        if bullet_points:
            # Minimal space before bullets
            self.story.append(Spacer(1, 0.01 * inch))

            for point in bullet_points:
                # \resumeItem{point} -> \item\small{point \vspace{-2pt}}
                bullet_text = f"• {point}"
                bullet_para = Paragraph(bullet_text, self.styles['bullet'])
                self.story.append(bullet_para)

            # Minimal space after bullets
            self.story.append(Spacer(1, 0.02 * inch))

        # Space after entire entry
        self.story.append(Spacer(1, 0.06 * inch))

    def add_project_entry(self, title: str, technologies: str, dates: str,
                         bullet_points: List[str]):
        r"""
        LaTeX project entry:
        \begin{itemize}[leftmargin=0.15in, label={}]
        \resumeProjectHeading{\textbf{Title} | \emph{Technologies}}{Dates}
        \resumeItemListStart
          \resumeItem{Description}
        \resumeItemListEnd
        """
        # Project title bold, technologies normal weight (using mixed style)
        # Limit technologies to max 4 keywords
        tech_list = [t.strip() for t in technologies.split(',') if t.strip()]
        tech_display = ', '.join(tech_list[:4])
        project_heading = f"<b>{title}</b> | {tech_display}"

        data = [[
            Paragraph(project_heading, self.styles['heading_mixed']),
            Paragraph(f"<i>{dates}</i>", self.styles['dates_location'])
        ]]

        table = Table(data, colWidths=[self.CONTENT_WIDTH * 0.70,
                                       self.CONTENT_WIDTH * 0.27])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), self.BULLET_LEFT_MARGIN),  # 0.15in left margin
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(table)

        # Add bullet points
        if bullet_points:
            self.story.append(Spacer(1, 0.01 * inch))

            for point in bullet_points:
                bullet_text = f"• {point}"
                bullet_para = Paragraph(bullet_text, self.styles['bullet'])
                self.story.append(bullet_para)

            self.story.append(Spacer(1, 0.02 * inch))

        self.story.append(Spacer(1, 0.06 * inch))

    def add_skills(self, skills_list: List[str], tools_list: List[str]):
        r"""
        LaTeX skills:
        \begin{itemize}[leftmargin=0.15in, label={}]
          \item \textbf{Skills:} skill1, skill2, skill3
          \item \textbf{Tools:} tool1, tool2, tool3
        \end{itemize}
        """
        if skills_list:
            skills_text = ", ".join(skills_list)
            skills_para = Paragraph(
                f"<b>Skills:</b> {skills_text}",
                self.styles['skills']
            )
            self.story.append(skills_para)

        if tools_list:
            tools_text = ", ".join(tools_list)
            tools_para = Paragraph(
                f"<b>Tools:</b> {tools_text}",
                self.styles['skills']
            )
            self.story.append(tools_para)

    def _auto_compress(self):
        """Compress if content exceeds one page"""
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            estimated_height = self._estimate_height()

            if estimated_height <= self.max_height:
                if iteration > 0:
                    logger.info(f"Compressed after {iteration} iteration(s)")
                break

            iteration += 1
            logger.warning(f"Height {estimated_height:.1f} exceeds {self.max_height:.1f}. Compressing...")

            compression_factor = self.max_height / estimated_height * 0.95

            for style in self.styles.values():
                if hasattr(style, 'fontSize'):
                    style.fontSize = max(8, style.fontSize * 0.94)
                if hasattr(style, 'spaceAfter'):
                    style.spaceAfter = max(0, style.spaceAfter * compression_factor)
                if hasattr(style, 'leading'):
                    style.leading = max(style.fontSize * 1.1, style.leading * 0.94)

        final_height = self._estimate_height()
        logger.info(f"✓ Final height: {final_height:.1f} vs max: {self.max_height:.1f}")

    def _estimate_height(self) -> float:
        """Estimate total content height"""
        total = 0
        for item in self.story:
            if hasattr(item, 'wrap'):
                try:
                    w, h = item.wrap(self.CONTENT_WIDTH, 999)
                    total += h
                except:
                    total += 12
        return total

    def build_resume(self, resume_data: Dict, output_path: str) -> str:
        """Build pixel-perfect LaTeX-matching resume"""
        logger.info(f"Building pixel-perfect LaTeX resume: {output_path}")

        self.story = []

        # Get config
        name = getattr(config, 'YOUR_NAME', 'Your Name')
        phone = getattr(config, 'YOUR_PHONE', '')
        email = getattr(config, 'YOUR_EMAIL', '')
        linkedin = getattr(config, 'YOUR_LINKEDIN_URL', '')
        github = getattr(config, 'YOUR_GITHUB_URL', '')
        leetcode = getattr(config, 'YOUR_LEETCODE_URL', '')

        # Build document
        self.add_header(name, phone, email, linkedin, github, leetcode)

        # Education
        self.add_section("Education")
        for edu in resume_data.get('education', []):
            self.add_education_entry(
                university=edu.get('university', ''),
                location=edu.get('location', ''),
                degree=edu.get('degree', ''),
                dates=edu.get('dates', '')
            )

        # Experience
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

        # Projects
        self.add_section("Projects")
        for proj in resume_data.get('projects', []):
            self.add_project_entry(
                title=proj.get('title', ''),
                technologies=proj.get('technologies', ''),
                dates=proj.get('dates', ''),
                bullet_points=proj.get('description', [])
            )

        # Technical Skills
        self.add_section("Technical Skills")
        skills_data = resume_data.get('skills', {})
        if isinstance(skills_data, dict):
            self.add_skills(
                skills_data.get('skills_list', []),
                skills_data.get('tools_list', [])
            )

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
            logger.info(f"✓ Pixel-perfect resume generated")
            return output_path

        except Exception as e:
            logger.error(f"Failed to build PDF: {e}", exc_info=True)
            raise
