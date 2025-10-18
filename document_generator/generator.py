# document_generator/generator.py
import os
import subprocess
import logging
from pathlib import Path # Use Path for consistency
import json
import re
import shutil # For shutil.which

# ReportLab imports
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# Import utilities and config
import sys
# Assume generator.py is in 'document_generator' which is in project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    from utils import escape_latex, decode_html_to_text
    import config
except ImportError as e:
     print(f"CRITICAL [generator.py]: Error importing modules: {e}. Check paths.", file=sys.stderr)
     raise SystemExit(f"Critical import error in generator.py: {e}.")

logger = logging.getLogger(__name__)

def compile_latex_to_pdf(latex_content, target_output_dir, base_filename):
    """Compiles LaTeX string to PDF using pdflatex in the specified directory."""
    target_output_dir = Path(target_output_dir)
    # Directory should exist, created by caller (main.py)
    if not target_output_dir.is_dir():
        logger.error(f"Target output directory does not exist: {target_output_dir}. Cannot compile LaTeX.")
        return None

    latex_filename = f"{base_filename}.tex"
    pdf_filename = f"{base_filename}.pdf"
    log_filename = f"{base_filename}.log"
    full_latex_path = target_output_dir / latex_filename
    full_pdf_path = target_output_dir / pdf_filename
    full_log_path = target_output_dir / log_filename

    if not latex_content:
        logger.error(f"Received empty LaTeX content for {base_filename}. Skipping compilation.")
        return None
    try:
        with open(full_latex_path, 'w', encoding='utf-8') as f: f.write(latex_content)
        logger.info(f"Temp .tex written: {full_latex_path.name} in {target_output_dir.name}")
    except Exception as e:
        logger.error(f"Failed to write .tex file {full_latex_path}: {e}", exc_info=True)
        return None

    pdflatex_cmd = getattr(config, 'PDFLATEX_PATH', None) or 'pdflatex'
    if not shutil.which(pdflatex_cmd):
        logger.critical(f"'{pdflatex_cmd}' command not found. Check TeX/PATH/config.")
        if full_latex_path.exists(): os.remove(full_latex_path)
        return None

    compiled_successfully = False
    for i in range(2):
        command = [pdflatex_cmd, '-interaction=nonstopmode', '-output-directory', str(target_output_dir), str(full_latex_path)]
        try:
            logger.info(f"Running pdflatex pass {i+1} for {latex_filename}...")
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=90, check=True)
            if i == 1 and full_pdf_path.exists(): compiled_successfully = True; break
            # Add other checks as needed
        except subprocess.CalledProcessError as e:
            logger.error(f"LaTeX failed (Pass {i+1}) for {latex_filename}. Code: {e.returncode}. Log: {full_log_path.name}")
            compiled_successfully = False; break
        except Exception as e: # Catch other errors like Timeout
            logger.critical(f"Error during PDF compilation (Pass {i+1}) for {latex_filename}: {e}", exc_info=True)
            compiled_successfully = False; break

    # Cleanup aux files, keep .tex on failure
    aux_extensions = ['.aux', '.log', '.out', '.toc', '.synctex.gz']
    extensions_to_remove = aux_extensions + ['.tex'] if compiled_successfully else aux_extensions
    if not compiled_successfully and full_latex_path.exists(): logger.warning(f"LaTeX failed. Keeping faulty .tex: {full_latex_path.name}")
    for ext in extensions_to_remove:
        aux_file = target_output_dir / f"{base_filename}{ext}"
        if aux_file.exists():
            try: os.remove(aux_file)
            except Exception as e_clean: logger.warning(f"Could not remove {aux_file.name}: {e_clean}")

    if compiled_successfully: logger.info(f"Successfully generated PDF: {full_pdf_path.name}")
    return str(full_pdf_path) if compiled_successfully else None

def create_job_details_pdf_reportlab(job_data, target_output_dir, base_filename="Job_Details_Report"):
    """Creates a Job Details PDF using ReportLab in the specified directory."""
    target_output_dir = Path(target_output_dir)
    if not target_output_dir.is_dir():
        logger.error(f"Target output directory does not exist: {target_output_dir}. Cannot create Job Details PDF.")
        return None

    pdf_filename = f"{base_filename}.pdf"
    full_pdf_path = target_output_dir / pdf_filename
    logger.info(f"Attempting Job Details PDF creation: {full_pdf_path.name} in {target_output_dir.name}")
    story = []
    try:
        doc = SimpleDocTemplate(str(full_pdf_path), pagesize=letter, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        # Define styles...
        title_style = ParagraphStyle('JobTitle', parent=styles['h1'], alignment=TA_CENTER, spaceAfter=6, fontSize=18, textColor=colors.HexColor("#1E3A8A"))
        company_style = ParagraphStyle('CompanyName', parent=styles['h2'], alignment=TA_CENTER, spaceAfter=12, fontSize=15, textColor=colors.HexColor("#4B5563"))
        section_heading_style = ParagraphStyle('SectionHeading', parent=styles['h3'], spaceBefore=12, spaceAfter=4, fontSize=13, textColor=colors.HexColor("#1E3A8A"), borderPadding=2, leading=16)
        body_style = ParagraphStyle('Body', parent=styles['BodyText'], spaceAfter=6, leading=14, alignment=TA_JUSTIFY)
        link_style_body = ParagraphStyle('LinkStyleBody', parent=body_style, textColor=colors.blue)
        list_item_style = ParagraphStyle('ListItem', parent=body_style, leftIndent=0.25*inch, bulletIndent=0.1*inch, spaceBefore=2, spaceAfter=2)

        # Extract Data...
        title = job_data.get('job_title', 'N/A').strip()
        company = job_data.get('company_name', 'N/A').strip()
        application_url = job_data.get('application_url', '').strip()
        source_url = job_data.get('source_url', '').strip()
        description_text = decode_html_to_text(job_data.get('description', '')) or "No description."
        skills_from_jd = job_data.get('skills', []) or []

        # Build Story...
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(company, company_style))
        # Add links, skills, description etc. using Paragraph, Spacer, ListFlowable...
        # Example Description section
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("Full Job Description:", section_heading_style))
        desc_paras = description_text.split('\n')
        for para_text in desc_paras:
            cleaned_para = para_text.strip()
            if cleaned_para:
                escaped_para = cleaned_para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(escaped_para, body_style))
                story.append(Spacer(1, 0.05*inch))

        # Generate PDF
        logger.debug("Building ReportLab PDF...")
        doc.build(story)
        logger.info(f"Successfully generated Job Details PDF: {full_pdf_path.name}")
        return str(full_pdf_path)
    except Exception as e:
        logger.error(f"Failed ReportLab PDF generation for {full_pdf_path.name}: {e}", exc_info=True)
        return None

# --- Main Function (Signature Changed) ---
def create_documents(job_data, tailored_docs_latex, target_output_directory):
    """
    Orchestrates generation of PDFs into the *specified* target directory.
    Args:
        job_data (dict): Job data from DB.
        tailored_docs_latex (dict): Dict from tailor {'resume': str|None, 'cover_letter': str|None}.
        target_output_directory (str or Path): The specific directory where PDFs should be saved.
    Returns:
        tuple: (resume_pdf_path, cover_letter_pdf_path, job_details_pdf_path) - Paths can be None.
    """
    logger.info(f"Entering create_documents. Target dir: {target_output_directory}")
    target_dir = Path(target_output_directory)

    # Ensure target directory exists (created by caller, but double-check)
    if not target_dir.is_dir():
         logger.error(f"Target directory '{target_dir}' does not exist. Cannot generate documents.")
         return None, None, None

    populated_resume_tex = tailored_docs_latex.get('resume')
    populated_cl_tex = tailored_docs_latex.get('cover_letter')

    if not populated_resume_tex:
         logger.error("Missing 'resume' LaTeX content. Cannot generate resume PDF.")
         details_path = create_job_details_pdf_reportlab(job_data, target_dir)
         return None, None, details_path

    # Create filenames with firstname_companyname format
    first_name = getattr(config, 'FIRST_NAME', '').strip() or 'Resume'
    company_name = job_data.get('company_name', 'Company').strip().replace(' ', '_')[:30]

    resume_filename = f"{first_name}_{company_name}_Resume"
    cover_letter_filename = f"{first_name}_{company_name}_CoverLetter"
    job_details_filename = f"{first_name}_{company_name}_JobDetails"

    # Compile/Generate Documents into the target_dir
    resume_pdf_path = compile_latex_to_pdf(populated_resume_tex, target_dir, resume_filename)
    cover_letter_pdf_path = compile_latex_to_pdf(populated_cl_tex, target_dir, cover_letter_filename) if populated_cl_tex else None
    job_details_pdf_path = create_job_details_pdf_reportlab(job_data, target_dir, job_details_filename)

    # Check results
    if not resume_pdf_path: logger.error("Resume PDF compilation FAILED.")
    if populated_cl_tex and not cover_letter_pdf_path: logger.error("Cover Letter PDF compilation FAILED.")
    if not job_details_pdf_path: logger.error("Job Details PDF generation FAILED.")

    logger.info(f"Exiting create_documents.")
    return resume_pdf_path, cover_letter_pdf_path, job_details_pdf_path