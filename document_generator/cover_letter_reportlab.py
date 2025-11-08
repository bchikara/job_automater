#!/usr/bin/env python3
"""
One-Page Cover Letter Generator using ReportLab
Matches LaTeX styling and ensures ATS compatibility
"""

import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class OnePageCoverLetter:
    """
    Generate ATS-friendly one-page cover letter matching LaTeX styling
    """

    # Page dimensions matching LaTeX template
    PAGE_WIDTH = letter[0]  # 8.5 inches
    PAGE_HEIGHT = letter[1]  # 11 inches

    # Margins matching LaTeX
    MARGIN_LEFT = 0.75 * inch
    MARGIN_RIGHT = 0.75 * inch
    MARGIN_TOP = 0.75 * inch
    MARGIN_BOTTOM = 0.75 * inch

    # Content area
    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    CONTENT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM

    # Font sizes
    FONT_NAME = 11  # Body text
    FONT_HEADER = 16  # Name header
    FONT_CONTACT = 9  # Contact info
    FONT_DATE = 10  # Date
    FONT_COMPANY = 11  # Company address
    FONT_GREETING = 11  # Dear Hiring Manager
    FONT_CLOSING = 11  # Sincerely

    def __init__(self):
        """Initialize cover letter generator"""
        self.styles = self._create_styles()
        self.story = []
        self.current_height = 0
        # Target 85% of actual content height as safety margin
        self.max_height = self.CONTENT_HEIGHT * 0.85

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create paragraph styles matching LaTeX template"""
        styles = {}

        # Header name style
        styles['name'] = ParagraphStyle(
            'Name',
            fontName='Helvetica-Bold',
            fontSize=self.FONT_HEADER,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=2,
            spaceBefore=0,
            leading=self.FONT_HEADER * 1.2
        )

        # Contact info style
        styles['contact'] = ParagraphStyle(
            'Contact',
            fontName='Helvetica',
            fontSize=self.FONT_CONTACT,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0.15 * inch,
            spaceBefore=0,
            leading=self.FONT_CONTACT * 1.3
        )

        # Date style
        styles['date'] = ParagraphStyle(
            'Date',
            fontName='Helvetica',
            fontSize=self.FONT_DATE,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0.15 * inch,
            spaceBefore=0,
            leading=self.FONT_DATE * 1.2
        )

        # Company address style
        styles['company'] = ParagraphStyle(
            'Company',
            fontName='Helvetica',
            fontSize=self.FONT_COMPANY,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0.15 * inch,
            spaceBefore=0,
            leading=self.FONT_COMPANY * 1.3
        )

        # Greeting style
        styles['greeting'] = ParagraphStyle(
            'Greeting',
            fontName='Helvetica',
            fontSize=self.FONT_GREETING,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0.1 * inch,
            spaceBefore=0,
            leading=self.FONT_GREETING * 1.2
        )

        # Body paragraph style
        styles['body'] = ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=self.FONT_NAME,
            textColor=colors.black,
            alignment=TA_JUSTIFY,
            spaceAfter=0.12 * inch,
            spaceBefore=0,
            leading=self.FONT_NAME * 1.4,  # Slightly more spacious for readability
            firstLineIndent=0
        )

        # Closing style
        styles['closing'] = ParagraphStyle(
            'Closing',
            fontName='Helvetica',
            fontSize=self.FONT_CLOSING,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0.5 * inch,  # Space for signature
            spaceBefore=0.1 * inch,
            leading=self.FONT_CLOSING * 1.2
        )

        # Signature style
        styles['signature'] = ParagraphStyle(
            'Signature',
            fontName='Helvetica',
            fontSize=self.FONT_NAME,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=0,
            spaceBefore=0,
            leading=self.FONT_NAME * 1.2
        )

        return styles

    def add_header(self, name: str, phone: str, email: str,
                   linkedin: str = "", location: str = ""):
        """Add applicant header (name and contact info)"""
        # Name
        name_para = Paragraph(name, self.styles['name'])
        self.story.append(name_para)

        # Contact info (all on one line or multiple lines)
        contact_parts = [phone, email]
        if linkedin:
            contact_parts.append(linkedin)
        if location:
            contact_parts.append(location)

        contact_text = " | ".join(contact_parts)
        contact_para = Paragraph(contact_text, self.styles['contact'])
        self.story.append(contact_para)

    def add_date(self):
        """Add current date"""
        today = datetime.now().strftime("%B %d, %Y")
        date_para = Paragraph(today, self.styles['date'])
        self.story.append(date_para)

    def add_company_address(self, hiring_manager: str, company_name: str,
                           company_address: str = ""):
        """Add company/recipient address"""
        if hiring_manager:
            para = Paragraph(hiring_manager, self.styles['company'])
            self.story.append(para)

        para = Paragraph(company_name, self.styles['company'])
        self.story.append(para)

        if company_address:
            para = Paragraph(company_address, self.styles['company'])
            self.story.append(para)

    def add_greeting(self, hiring_manager_name: str = ""):
        """Add greeting"""
        if hiring_manager_name:
            greeting_text = f"Dear {hiring_manager_name},"
        else:
            greeting_text = "Dear Hiring Manager,"

        greeting_para = Paragraph(greeting_text, self.styles['greeting'])
        self.story.append(greeting_para)

    def add_body_paragraph(self, text: str):
        """Add body paragraph"""
        body_para = Paragraph(text, self.styles['body'])
        self.story.append(body_para)

    def add_closing(self, name: str):
        """Add closing and signature"""
        closing_para = Paragraph("Sincerely,", self.styles['closing'])
        self.story.append(closing_para)

        signature_para = Paragraph(name, self.styles['signature'])
        self.story.append(signature_para)

    def _estimate_content_height(self) -> float:
        """Estimate total content height"""
        total_height = 0
        for flowable in self.story:
            if hasattr(flowable, 'wrap'):
                w, h = flowable.wrap(self.CONTENT_WIDTH, self.max_height)
                total_height += h
        return total_height

    def _auto_compress(self):
        """Auto-compress content if it exceeds one page"""
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            estimated_height = self._estimate_content_height()

            if estimated_height <= self.max_height:
                if iteration > 0:
                    logger.info(f"Cover letter compressed to fit one page after {iteration} iteration(s)")
                break

            iteration += 1
            overage = estimated_height - self.max_height
            logger.warning(f"Cover letter height ({estimated_height:.1f}) exceeds page ({self.max_height:.1f}) by {overage:.1f}. Compressing (iteration {iteration})...")

            # Calculate compression factor
            compression_factor = self.max_height / estimated_height
            compression_factor = compression_factor * 0.95

            # Adjust styles
            for style_name, style in self.styles.items():
                current_font_size = style.fontSize if hasattr(style, 'fontSize') else 11

                if hasattr(style, 'fontSize'):
                    # Reduce font, min 8pt
                    style.fontSize = max(8, style.fontSize * 0.93)

                if hasattr(style, 'spaceAfter'):
                    style.spaceAfter = max(0, style.spaceAfter * compression_factor)

                if hasattr(style, 'spaceBefore'):
                    style.spaceBefore = max(0, style.spaceBefore * compression_factor)

                if hasattr(style, 'leading'):
                    # Reduce line height but maintain readability
                    new_leading = style.leading * 0.93
                    min_leading = current_font_size * 1.0
                    style.leading = max(min_leading, new_leading)

        # Final check
        final_height = self._estimate_content_height()
        if final_height > self.max_height:
            logger.error(f"WARNING: Cover letter may still exceed one page (est: {final_height:.1f} vs max: {self.max_height:.1f})")
        else:
            logger.info(f"✓ Cover letter fits on one page (est: {final_height:.1f} vs max: {self.max_height:.1f})")

    def build_cover_letter(self, cover_letter_data: Dict, output_path: str) -> str:
        """
        Build complete one-page cover letter PDF
        Args:
            cover_letter_data: Dict with 'paragraphs', 'company_name', 'hiring_manager', etc.
            output_path: Full path for output PDF
        Returns:
            Path to generated PDF
        """
        logger.info(f"Building one-page cover letter: {output_path}")

        # Extract data
        applicant_name = cover_letter_data.get('applicant_name', 'Your Name')
        phone = cover_letter_data.get('phone', '')
        email = cover_letter_data.get('email', '')
        linkedin = cover_letter_data.get('linkedin', '')
        location = cover_letter_data.get('location', '')

        company_name = cover_letter_data.get('company_name', '')
        hiring_manager = cover_letter_data.get('hiring_manager', '')
        company_address = cover_letter_data.get('company_address', '')

        paragraphs = cover_letter_data.get('paragraphs', [])

        # Build content
        self.add_header(applicant_name, phone, email, linkedin, location)
        self.add_date()
        self.add_company_address(hiring_manager, company_name, company_address)
        self.add_greeting(hiring_manager)

        # Add body paragraphs
        for paragraph in paragraphs:
            self.add_body_paragraph(paragraph)

        self.add_closing(applicant_name)

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
                title=f"{applicant_name} - Cover Letter"
            )

            doc.build(self.story)
            logger.info(f"Successfully generated cover letter PDF: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate cover letter PDF: {e}", exc_info=True)
            raise


def generate_cover_letter_pdf(cover_letter_data: Dict, output_path: str) -> str:
    """
    Main entry point for cover letter PDF generation
    """
    generator = OnePageCoverLetter()
    return generator.build_cover_letter(cover_letter_data, output_path)


# Test
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    test_data = {
        'applicant_name': 'John Doe',
        'phone': '555-123-4567',
        'email': 'john.doe@email.com',
        'linkedin': 'linkedin.com/in/johndoe',
        'location': 'New York, NY',
        'company_name': 'Tech Innovations Inc',
        'hiring_manager': 'Jane Smith',
        'company_address': 'Hiring Manager',
        'paragraphs': [
            "I am writing to express my strong interest in the Senior Software Engineer position at Tech Innovations Inc. With over 5 years of experience in full-stack development and a proven track record of delivering scalable solutions, I am excited about the opportunity to contribute to your team.",
            "In my current role at XYZ Corp, I have led the development of microservices architecture using React, Node.js, and AWS, resulting in a 40% improvement in system performance. My experience aligns perfectly with your requirements for expertise in modern web technologies and cloud infrastructure.",
            "I am particularly drawn to Tech Innovations Inc's commitment to innovation and excellence. I am confident that my technical skills, leadership experience, and passion for problem-solving make me an ideal candidate for this role.",
            "Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team's success."
        ]
    }

    generate_cover_letter_pdf(test_data, '/tmp/test_cover_letter.pdf')
    print("✓ Cover letter generated successfully!")
