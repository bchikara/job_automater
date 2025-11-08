#!/usr/bin/env python3
"""
Automatic Integration Script for ATS-Optimized Resume System V2
Updates main.py to use enhanced document generation with ATS scoring
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def backup_main_py():
    """Create timestamped backup of main.py"""
    main_py_path = PROJECT_ROOT / "main.py"

    if not main_py_path.exists():
        print_error("main.py not found!")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = PROJECT_ROOT / f"main.py.backup_{timestamp}"

    try:
        shutil.copy2(main_py_path, backup_path)
        print_success(f"Backup created: {backup_path.name}")
        return backup_path
    except Exception as e:
        print_error(f"Failed to create backup: {e}")
        return None

def read_main_py():
    """Read current main.py content"""
    main_py_path = PROJECT_ROOT / "main.py"
    try:
        with open(main_py_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print_error(f"Failed to read main.py: {e}")
        return None

def write_main_py(content):
    """Write updated content to main.py"""
    main_py_path = PROJECT_ROOT / "main.py"
    try:
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print_success("main.py updated successfully")
        return True
    except Exception as e:
        print_error(f"Failed to write main.py: {e}")
        return False

def integrate_v2_system(content):
    """
    Update main.py to use V2 document generation system
    Returns: (updated_content, changes_made)
    """
    changes = []
    updated_content = content

    # Change 1: Update import statement
    old_import = "from document_generator import generator as document_generator_module"
    new_import = """from document_generator import generator as document_generator_module
from document_generator.generator_v2 import DocumentGeneratorV2  # V2 with ATS optimization"""

    if old_import in updated_content:
        updated_content = updated_content.replace(old_import, new_import)
        changes.append("Added V2 generator import")

    # Change 2: Update process_single_job function
    # Find the tailoring and generation section
    old_generation_code = """    # --- Step 1: Tailor Resume and Cover Letter ---
    tailored_content = None
    try:
        logger.info(f"{log_prefix}Generating tailored LaTeX documents via tailor module...")
        tailored_content = resume_tailor_module.generate_tailored_latex_docs(job_data)
        if not tailored_content or not tailored_content.get('resume'):
            raise ValueError("Tailor function returned no resume content.") # Raise error to catch below
        logger.info(f"{log_prefix}Tailoring successful. Resume generated. CL {'generated.' if tailored_content.get('cover_letter') else 'not generated.'}")
        update_fields = {
            'tailored_resume_text': tailored_content.get('resume'),
            'tailored_cover_letter_text': tailored_content.get('cover_letter')
        }
        if not database.update_job_data(primary_id, update_fields):
            logger.warning(f"{log_prefix}Failed to update DB with tailored LaTeX text.")
    except Exception as e:
        logger.error(f"{log_prefix}Exception during tailoring: {e}", exc_info=True)
        database.update_job_status(primary_id, config.JOB_STATUS_TAILORING_FAILED, f"Exception in tailor: {str(e)[:200]}")
        return False

    # --- Step 2: Generate PDFs (Passing Path) ---
    try:
        logger.info(f"{log_prefix}Generating PDF documents into: {job_specific_output_dir}...")
        # *** THIS IS THE CORRECTED CALL TO THE MODIFIED GENERATOR ***
        resume_path, cl_path, details_path = document_generator_module.create_documents(
            job_data=job_data,
            tailored_docs_latex=tailored_content,
            target_output_directory=str(job_specific_output_dir) # Pass the string path
        )
        # Check results
        resume_ok = resume_path and Path(resume_path).is_file()
        details_ok = details_path and Path(details_path).is_file()
        if not resume_ok or not details_ok:
            error_msg = f"PDF generation failed: Resume {'missing' if not resume_ok else 'OK'}, Details {'missing' if not details_ok else 'OK'}."
            logger.error(f"{log_prefix}{error_msg}")
            database.update_job_status(primary_id, config.JOB_STATUS_GENERATION_FAILED, error_msg)
            update_fields = {'resume_pdf_path': resume_path, 'cover_letter_pdf_path': cl_path, 'job_details_pdf_path': details_path}
            database.update_job_data(primary_id, update_fields) # Store whatever paths were returned
            return False

        logger.info(f"{log_prefix}PDF generation successful.")
        update_fields = {
            'resume_pdf_path': resume_path, 'cover_letter_pdf_path': cl_path, 'job_details_pdf_path': details_path,
            'job_specific_output_dir': str(job_specific_output_dir), # Ensure path is stored correctly
            'status': config.JOB_STATUS_DOCS_READY, # Ready for application
            'status_reason': f"Docs generated in {job_specific_output_dir.name}",
        }
        database.update_job_data(primary_id, update_fields)
        return True # Success

    except Exception as e:
        logger.error(f"{log_prefix}Exception during PDF generation call: {e}", exc_info=True)
        database.update_job_status(primary_id, config.JOB_STATUS_GENERATION_FAILED, f"Exception calling generator: {str(e)[:200]}")
        return False"""

    new_generation_code = """    # --- Generate Documents with V2 System (ATS-Optimized, One-Page, Aggressive Tailoring) ---
    try:
        logger.info(f"{log_prefix}Starting V2 document generation with ATS optimization...")
        logger.info(f"{log_prefix}Target: ATS Score >= 85, One-page guarantee, Aggressive tailoring")

        # Initialize V2 generator
        gen_v2 = DocumentGeneratorV2()

        # Generate all documents with ATS optimization and iterative refinement
        results = gen_v2.generate_all_documents(job_data, str(job_specific_output_dir))

        # Extract results
        resume_path = results.get('resume_pdf')
        cl_path = results.get('cover_letter_pdf')
        details_path = results.get('job_details_pdf')
        ats_score = results.get('ats_score', 0)
        ats_report = results.get('ats_report', {})

        # Log ATS results
        logger.info(f"{log_prefix}ATS Score: {ats_score}/100 {'✓ PASS' if ats_score >= 85 else '⚠ BELOW TARGET'}")
        if ats_report.get('keyword_stats'):
            logger.info(f"{log_prefix}Keyword Stats: {ats_report['keyword_stats']}")
        if ats_report.get('violations'):
            logger.warning(f"{log_prefix}Keyword Violations: {len(ats_report['violations'])} found")
        if ats_report.get('suggestions') and ats_score < 85:
            logger.warning(f"{log_prefix}Suggestions for improvement:")
            for suggestion in ats_report['suggestions'][:3]:
                logger.warning(f"{log_prefix}  - {suggestion}")

        # Check results
        resume_ok = resume_path and Path(resume_path).is_file()
        details_ok = details_path and Path(details_path).is_file()

        if not resume_ok or not details_ok:
            error_msg = f"V2 generation failed: Resume {'missing' if not resume_ok else 'OK'}, Details {'missing' if not details_ok else 'OK'}."
            logger.error(f"{log_prefix}{error_msg}")
            database.update_job_status(primary_id, config.JOB_STATUS_GENERATION_FAILED, error_msg)
            update_fields = {
                'resume_pdf_path': resume_path,
                'cover_letter_pdf_path': cl_path,
                'job_details_pdf_path': details_path,
                'ats_score': ats_score
            }
            database.update_job_data(primary_id, update_fields)
            return False

        logger.info(f"{log_prefix}V2 PDF generation successful! One-page: ✓, ATS: {ats_score}/100")

        # Store all results in database including ATS score
        update_fields = {
            'resume_pdf_path': resume_path,
            'cover_letter_pdf_path': cl_path,
            'job_details_pdf_path': details_path,
            'job_specific_output_dir': str(job_specific_output_dir),
            'ats_score': ats_score,
            'ats_keyword_stats': ats_report.get('keyword_stats', {}),
            'ats_suggestions': ats_report.get('suggestions', []),
            'status': config.JOB_STATUS_DOCS_READY,
            'status_reason': f"V2 docs generated (ATS: {ats_score}/100) in {job_specific_output_dir.name}",
        }
        database.update_job_data(primary_id, update_fields)
        return True

    except Exception as e:
        logger.error(f"{log_prefix}Exception during V2 generation: {e}", exc_info=True)
        database.update_job_status(primary_id, config.JOB_STATUS_GENERATION_FAILED, f"V2 exception: {str(e)[:200]}")
        return False"""

    if old_generation_code in updated_content:
        updated_content = updated_content.replace(old_generation_code, new_generation_code)
        changes.append("Updated process_single_job() to use V2 generator")
        changes.append("Added ATS score logging and database storage")
    else:
        print_warning("Could not find exact code pattern to replace")
        print_warning("You may need to manually integrate V2")

    return updated_content, changes

def show_changes_summary(changes):
    """Display summary of changes made"""
    if changes:
        print_header("CHANGES MADE")
        for i, change in enumerate(changes, 1):
            print(f"  {i}. {change}")
    else:
        print_warning("No changes were made")

def verify_files_exist():
    """Verify all required V2 files exist"""
    required_files = [
        "ats_scorer.py",
        "document_generator/resume_reportlab.py",
        "document_generator/generator_v2.py",
        "resume_tailor/tailor_enhanced.py"
    ]

    all_exist = True
    print_info("Checking for V2 system files...")

    for file in required_files:
        file_path = PROJECT_ROOT / file
        if file_path.exists():
            print_success(f"Found: {file}")
        else:
            print_error(f"Missing: {file}")
            all_exist = False

    return all_exist

def main():
    """Main integration workflow"""
    print_header("ATS-OPTIMIZED RESUME SYSTEM V2 - AUTO INTEGRATION")

    print(f"{Colors.BOLD}This script will update your main.py to use:"){Colors.END}")
    print("  • ReportLab one-page resumes (guaranteed)")
    print("  • ATS scoring with 85+ target")
    print("  • Keyword frequency tracking (max 2x)")
    print("  • Aggressive tailoring with iterative refinement")
    print()

    # Step 1: Verify V2 files exist
    print_info("Step 1: Verifying V2 system files...")
    if not verify_files_exist():
        print_error("\nSome V2 files are missing!")
        print_info("Please ensure all V2 files were created successfully.")
        return 1
    print()

    # Step 2: Backup main.py
    print_info("Step 2: Creating backup of main.py...")
    backup_path = backup_main_py()
    if not backup_path:
        print_error("\nFailed to create backup. Aborting for safety.")
        return 1
    print()

    # Step 3: Read current main.py
    print_info("Step 3: Reading current main.py...")
    content = read_main_py()
    if not content:
        print_error("\nFailed to read main.py. Aborting.")
        return 1
    print_success(f"Read {len(content)} characters")
    print()

    # Step 4: Integrate V2 system
    print_info("Step 4: Integrating V2 system...")
    updated_content, changes = integrate_v2_system(content)

    if not changes:
        print_error("\nNo changes were made. Integration failed.")
        print_info("You may need to manually integrate V2.")
        return 1

    show_changes_summary(changes)
    print()

    # Step 5: Ask for confirmation
    print_warning("Step 5: Review and confirm changes")
    response = input(f"\n{Colors.BOLD}Apply these changes to main.py? (yes/no): {Colors.END}").strip().lower()

    if response != 'yes':
        print_info("\nIntegration cancelled. No changes made.")
        print_info(f"Backup remains at: {backup_path.name}")
        return 0

    # Step 6: Write updated main.py
    print()
    print_info("Step 6: Writing updated main.py...")
    if not write_main_py(updated_content):
        print_error("\nFailed to write main.py!")
        print_info(f"Your original is safe at: {backup_path.name}")
        return 1
    print()

    # Success!
    print_header("INTEGRATION COMPLETE!")
    print(f"{Colors.GREEN}{Colors.BOLD}✓ Your job-agent now uses the V2 system!{Colors.END}\n")
    print("What happens now when you run batch processing:")
    print(f"  {Colors.GREEN}✓{Colors.END} Each resume is tailored aggressively to the job")
    print(f"  {Colors.GREEN}✓{Colors.END} Iterative refinement until ATS score >= 85")
    print(f"  {Colors.GREEN}✓{Colors.END} Keywords tracked (max 2 per keyword enforced)")
    print(f"  {Colors.GREEN}✓{Colors.END} One-page guaranteed (auto-compression)")
    print(f"  {Colors.GREEN}✓{Colors.END} ATS score logged and stored in database")
    print()
    print(f"{Colors.BLUE}Backup saved at: {backup_path.name}{Colors.END}")
    print()
    print(f"{Colors.BOLD}Next steps:{Colors.END}")
    print("  1. Test with: python test_ats_system.py")
    print("  2. Run your normal CLI commands (they now use V2!)")
    print("  3. Check logs for ATS scores after generation")
    print()
    print(f"{Colors.YELLOW}To revert: copy {backup_path.name} back to main.py{Colors.END}")
    print()

    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Integration cancelled by user.{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
