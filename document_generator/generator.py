import os
import subprocess
import logging
from datetime import date # Example if you only need date

# Import utilities, including the escape function
# Assumes utils.py is in the parent directory (project root)
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from utils import escape_latex
except ImportError as e:
     logging.critical(f"Error importing escape_latex from utils in generator.py: {e}", exc_info=True)
     raise # Cannot proceed without escape function

# --- Configuration ---
CURRENT_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(CURRENT_DIR, 'templates')
BASE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output_documents') # Adjusted path

# --- Helper Functions ---

def load_template(template_filename):
    """Loads a LaTeX template file from the templates directory."""
    filepath = os.path.join(TEMPLATE_DIR, template_filename)
    logging.info(f"Attempting to load template: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Template file not found at {filepath}")
        raise FileNotFoundError(f"Template file missing: {filepath}")
    except Exception as e:
        logging.error(f"Could not read template file {filepath}: {e}", exc_info=True)
        raise e

def compile_latex_to_pdf(latex_content, target_output_dir, base_filename):
    """
    Compiles a LaTeX string to a PDF file using pdflatex.
    Saves PDF and temporary files to the specified target_output_dir.
    Uses base_filename (e.g., "Resume" or "CoverLetter") for naming.
    Returns the full path to the PDF if successful, otherwise None.
    """
    latex_filename = f"{base_filename}.tex"
    pdf_filename = f"{base_filename}.pdf"
    log_filename = f"{base_filename}.log"

    full_latex_path = os.path.join(target_output_dir, latex_filename)
    full_pdf_path = os.path.join(target_output_dir, pdf_filename)
    full_log_path = os.path.join(target_output_dir, log_filename)

    os.makedirs(target_output_dir, exist_ok=True)

    try:
        with open(full_latex_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        logging.info(f"Temporary .tex file written to {full_latex_path}")
    except Exception as e:
        logging.error(f"Failed to write .tex file {full_latex_path}: {e}", exc_info=True)
        return None

    pdflatex_cmd = '/usr/local/texlive/2025/bin/universal-darwin/pdflatex' # Hardcoded path

    command = [pdflatex_cmd,
               '-interaction=nonstopmode',
               '-output-directory', target_output_dir,
               full_latex_path]
    try:
        logging.info(f"Running command: {' '.join(command)}")
        process = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

        if os.path.exists(full_pdf_path):
            logging.info(f"Successfully generated PDF: {full_pdf_path}")
            return full_pdf_path
        else:
            logging.error(f"pdflatex ran successfully but PDF file not found at {full_pdf_path}.")
            logging.error("----- pdflatex STDOUT -----")
            logging.error(process.stdout)
            logging.error("----- pdflatex STDERR -----")
            logging.error(process.stderr)
            logging.error("--------------------------")
            return None

    except subprocess.CalledProcessError as e:
        logging.error(f"LaTeX compilation failed for {latex_filename} with return code {e.returncode}.")
        logging.error("----- pdflatex STDOUT -----")
        logging.error(e.stdout)
        logging.error("----- pdflatex STDERR -----")
        logging.error(e.stderr)
        logging.error("--------------------------")
        logging.warning(f"Check the log file: {full_log_path}")
        logging.warning(f"Faulty .tex file saved at: {full_latex_path}")
        return None
    except FileNotFoundError:
        logging.critical(f"CRITICAL ERROR: '{pdflatex_cmd}' command not found.")
        logging.critical("Ensure TeX Live (or MiKTeX) is installed and its 'bin' directory is in your system's PATH, or the hardcoded path is correct.")
        return None
    except Exception as e:
        logging.critical(f"An unexpected error occurred during PDF compilation for {latex_filename}: {e}", exc_info=True)
        return None
    finally:
        logging.debug(f"Cleaning up auxiliary files for {base_filename} in {target_output_dir}...")
        for ext in ['.aux', '.log', '.out', '.toc']:
             aux_file = os.path.join(target_output_dir, f"{base_filename}{ext}")
             if os.path.exists(aux_file):
                 try:
                     os.remove(aux_file)
                 except Exception as e_clean:
                     logging.warning(f"Could not remove aux file {aux_file}: {e_clean}")
        if not os.path.exists(full_pdf_path) and os.path.exists(full_latex_path):
             logging.info(f"Keeping faulty .tex file for debugging: {full_latex_path}")
        elif os.path.exists(full_pdf_path) and os.path.exists(full_latex_path):
             try:
                 os.remove(full_latex_path)
                 logging.debug(f"Removed temporary .tex file: {full_latex_path}")
             except Exception as e_clean:
                 logging.warning(f"Could not remove temporary .tex file {full_latex_path}: {e_clean}")


def generate_cover_letter_text(job_data, tailored_resume_text):
     """
     Generates the text content for the cover letter.
     Applies LaTeX escaping to placeholder values using utils.escape_latex.
     """
     logging.info("Entering generate_cover_letter_text function...")

     try:
         cl_template = load_template("cover_letter_template.tex")
     except Exception as e:
         logging.error(f"Failed to load cover letter template: {e}", exc_info=True)
         return None

     # --- Placeholder Population ---
     company_name = job_data.get('company_name', '[Company Name Placeholder]')
     job_title = job_data.get('title', '[Job Title Placeholder]')
     hiring_manager = job_data.get('hiring_manager', 'Hiring Team')
     hiring_manager_title = job_data.get('hiring_manager_title', '')
     company_address = job_data.get('company_address', job_data.get('address', '[Company Address Placeholder]'))
     company_location = job_data.get('company_location', job_data.get('location', '[Location Placeholder]'))
     source_platform = job_data.get('source_platform', 'your website')

     if hiring_manager != 'Hiring Team' and hiring_manager:
         manager_last_name = hiring_manager.split(' ')[-1]
         salutation = f"Dear Mr./Ms./Mx. {manager_last_name}"
     else:
         salutation = "Dear Hiring Team"

     # *** TODO: Gemini API Integration Point ***
     # tailored_para1 = call_gemini_api(...) # Remember to escape Gemini output if needed

     replacements = {
         "[Hiring Manager Name (if known), or \"Hiring Team\"]": escape_latex(hiring_manager),
         "[Hiring Manager Title (if known)]": escape_latex(hiring_manager_title),
         "[Company Name]": escape_latex(company_name),
         "[Company Address Placeholder]": escape_latex(company_address),
         "[Location Placeholder]": escape_latex(company_location),
         "[Mr./Ms./Mx. Last Name of Hiring Manager, or Hiring Team]": escape_latex(salutation),
         "[Job Title]": escape_latex(job_title),
         "[Platform where you saw the job posting, e.g., LinkedIn, company website]": escape_latex(source_platform),
         # Add Gemini-generated paragraphs here, ensuring they are also escaped:
         # "I am writing...your team.": escape_latex(tailored_para1),
     }

     populated_cl_tex = cl_template
     for placeholder, value in replacements.items():
         populated_cl_tex = populated_cl_tex.replace(placeholder, value) # Value is already escaped

     logging.info("Exiting generate_cover_letter_text function...")
     return populated_cl_tex


def create_documents(job_data, tailored_resume_text):
    """
    Orchestrates the generation of resume and cover letter PDFs into job-specific folders.
    Assumes tailored_resume_text is already properly escaped by the caller (resume_tailor.py).
    """
    logging.info("Entering create_documents function...")

    # --- 1. Use Pre-Escaped Resume LaTeX Content ---
    populated_resume_tex = tailored_resume_text
    logging.info("Using pre-escaped tailored_resume_text for resume.")

    logging.debug("--- Start of tailored_resume_text (first 500 chars) ---")
    logging.debug(populated_resume_tex[:500])
    logging.debug("--- End of tailored_resume_text snippet ---")

    # --- 2. Generate Populated Cover Letter LaTeX ---
    populated_cl_tex = generate_cover_letter_text(job_data, tailored_resume_text)
    cover_letter_pdf_path = None

    # --- 3. Define Job-Specific Output Directory and Filenames ---
    company_name = job_data.get('company_name', 'UnknownCompany')
    job_title_raw = job_data.get('title')
    job_title = job_title_raw if job_title_raw is not None else 'UnknownJob'
    job_id = str(job_data.get('_id', 'UnknownID'))

    safe_company_name = "".join(c if c.isalnum() else "_" for c in company_name)
    safe_job_title = "".join(c if c.isalnum() else "_" for c in job_title)
    safe_job_id = "".join(c if c.isalnum() else "_" for c in job_id)
    safe_job_title = safe_job_title[:40]
    safe_company_name = safe_company_name[:40]

    job_specific_folder_name = f"{safe_company_name}_{safe_job_title}_{safe_job_id}"
    job_specific_output_dir = os.path.join(BASE_OUTPUT_DIR, job_specific_folder_name)

    try:
        os.makedirs(job_specific_output_dir, exist_ok=True)
        logging.info(f"Ensured job-specific output directory exists: {job_specific_output_dir}")
    except OSError as e:
        logging.error(f"Failed to create job-specific output directory {job_specific_output_dir}: {e}", exc_info=True)
        return None, None

    # --- 4. Compile Documents to PDF ---
    logging.info(f"Attempting compilation in directory: {job_specific_output_dir}")
    resume_pdf_path = compile_latex_to_pdf(populated_resume_tex, job_specific_output_dir, "Resume")

    if populated_cl_tex:
        cover_letter_pdf_path = compile_latex_to_pdf(populated_cl_tex, job_specific_output_dir, "CoverLetter")
    else:
         logging.warning("Skipping cover letter PDF compilation because content generation failed.")

    # --- 5. Return Paths ---
    logging.info(f"Exiting create_documents. Resume PDF: {resume_pdf_path}, Cover Letter PDF: {cover_letter_pdf_path}")
    return resume_pdf_path, cover_letter_pdf_path
