#!/usr/bin/env python3
"""
Job Agent CLI - Interactive Command Line Interface for Job Application Automation
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import time

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.align import Align
import questionary
from questionary import Style

# Import ASCII art
import cli_art

# Setup project path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import project modules
import config
import database
from utils import setup_logging, create_dir_if_not_exists, sanitize_filename_component
from scrapers import linkedin_scraper, jobright_scraper
from resume_tailor import tailor as resume_tailor_module
from document_generator import generator as document_generator_module
from document_generator.generator_v2 import DocumentGeneratorV2  # V2 with ATS optimization
from job_automator import automator_main

# Initialize rich console
console = Console()

# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#2196f3 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#4caf50'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
])


def setup_cli_logging(verbose=False):
    """Setup logging for CLI with appropriate level"""
    log_level = "DEBUG" if verbose else "INFO"
    log_dir = PROJECT_ROOT / config.LOG_DIR_NAME
    # Disable console output - only log to file for clean UI
    setup_logging(name="job_agent_cli", log_level_str=log_level, log_dir=log_dir, log_filename="cli.log", console_output=verbose)


def display_banner():
    """Display CLI banner with ASCII art"""
    cli_art.display_help_screen()


def display_job_table(jobs, title="Jobs"):
    """Display jobs in a beautiful table"""
    if not jobs:
        console.print(f"[yellow]No jobs found.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")

    table.add_column("#", style="dim", width=4)
    table.add_column("Company", style="cyan", width=20)
    table.add_column("Title", style="green", width=30)
    table.add_column("Status", style="yellow", width=20)
    table.add_column("Date", style="blue", width=12)

    for idx, job in enumerate(jobs, 1):
        company = job.get('company_name', 'N/A')[:20]
        title = job.get('job_title', 'N/A')[:30]
        status = job.get('status', 'N/A')
        date_scraped = job.get('date_scraped', '')

        # Format date
        if date_scraped:
            if hasattr(date_scraped, 'strftime'):
                date_str = date_scraped.strftime('%Y-%m-%d')
            else:
                date_str = str(date_scraped)[:10]
        else:
            date_str = 'N/A'

        # Color code status
        status_color = {
            'new': 'green',
            'docs_ready': 'cyan',
            'applied_success': 'bright_green',
            'application_applied_success': 'bright_green',
            'application_failed_ats': 'red',
            'tailoring_failed': 'red',
            'generation_failed': 'red',
        }.get(status, 'yellow')

        table.add_row(
            str(idx),
            company,
            title,
            f"[{status_color}]{status}[/{status_color}]",
            date_str
        )

    console.print(table)


class CustomGroup(click.Group):
    """Custom Click Group that shows our ASCII art for help"""
    def format_help(self, ctx, formatter):
        """Override help formatting to show ASCII art"""
        # Show our beautiful banner instead of Click's default help
        setup_cli_logging(False)
        cli_art.display_help_screen()


@click.group(invoke_without_command=True, cls=CustomGroup, context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Job Agent CLI - Automate your job applications with AI"""
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose
    setup_cli_logging(verbose)

    # If no command is provided, show help
    if ctx.invoked_subcommand is None:
        display_banner()
        return

    # Connect to database for actual commands
    try:
        database.connect_db()
    except Exception as e:
        console.print(f"[red]Failed to connect to database: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--source', type=click.Choice(['linkedin', 'jobright', 'both']), default='both', help='Job source')
@click.option('--limit', type=int, default=None, help='Max jobs to fetch')
def fetch_jobs(source, limit):
    """Fetch jobs from configured sources"""
    limit = limit or config.SCRAPER_JOB_LIMIT

    # Display fetch jobs header
    cli_art.display_fetch_header(source, limit)

    # Safety warnings for excessive scraping
    if limit > 50:
        console.print(cli_art.WARNING_ART)
        console.print("[bold red]⚠️  DANGER: Fetching {0} jobs![/bold red]".format(limit))
        console.print("[yellow]Fetching more than 50 jobs may trigger rate limiting or account restrictions.[/yellow]")
        console.print("[yellow]Recommended: Fetch 20-30 jobs at a time with delays.[/yellow]\n")

        if not Confirm.ask("[yellow]Do you want to continue?[/yellow]", default=False):
            console.print("\n[yellow]✓ Cancelled. Try with --limit 20 for safety.[/yellow]\n")
            return
        console.clear()
        cli_art.display_fetch_header(source, limit)
    elif limit > 30:
        console.print(f"[yellow]ℹ️  Notice: Fetching {limit} jobs. Stay under 50 to avoid rate limiting.[/yellow]\n")
    elif limit > 20:
        console.print(f"[green]✓ Fetching {limit} jobs. This is within safe limits.[/green]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        if source in ['linkedin', 'both']:
            if config.LINKEDIN_SESSION_COOKIE:
                console.print(cli_art.LINKEDIN_ART)
                task = progress.add_task("[blue]🔍 Fetching from LinkedIn...", total=100)
                try:
                    progress.update(task, advance=25, description="[blue]📡 Connecting to LinkedIn...")
                    time.sleep(0.5)
                    progress.update(task, advance=25, description="[blue]🔍 Searching for jobs...")
                    linkedin_scraper.run_linkedin_scraper(limit=limit)
                    progress.update(task, advance=50, description="[green]✓ LinkedIn scraping complete")
                except Exception as e:
                    progress.update(task, description=f"[red]✗ LinkedIn error: {str(e)[:50]}")
            else:
                console.print("[yellow]⚠ LinkedIn scraper skipped: Cookie not configured[/yellow]")

        if source in ['jobright', 'both']:
            if config.JOBRIGHT_COOKIE_STRING:
                console.print(cli_art.JOBRIGHT_ART)
                task = progress.add_task("[cyan]🔍 Fetching from JobRight...", total=100)
                try:
                    progress.update(task, advance=25, description="[cyan]📡 Connecting to JobRight...")
                    time.sleep(0.5)
                    progress.update(task, advance=25, description="[cyan]🔍 Searching for jobs...")
                    # Convert limit (count) to max_position for pagination
                    # JobRight returns ~10 jobs per page, so max_position should be (limit - 10)
                    max_pos = max(0, limit - 10) if limit >= 10 else 0
                    jobright_scraper.run_jobright_scraper(max_position=max_pos)
                    progress.update(task, advance=50, description="[green]✓ JobRight scraping complete")
                except Exception as e:
                    progress.update(task, description=f"[red]✗ JobRight error: {str(e)[:50]}")
            else:
                console.print("[yellow]⚠ JobRight scraper skipped: Cookie not configured[/yellow]")

    # Show summary with beautiful stats
    console.print("\n")
    display_limit = min(limit, 20)
    jobs = database.get_jobs_by_status(['new'], limit=display_limit)
    total_new = len(database.get_jobs_by_status(['new'], limit=1000))

    # Success panel
    summary_panel = Panel(
        f"[bold green]✓ Fetch operation completed![/bold green]\n\n"
        f"[cyan]New jobs found:[/cyan] {total_new}\n"
        f"[cyan]Requested limit:[/cyan] {limit}\n"
        f"[cyan]Source:[/cyan] {source.upper()}",
        title="[bold green]Scraping Complete[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(summary_panel)

    if jobs:
        console.print(f"\n[bold cyan]Recently Fetched Jobs[/bold cyan] [dim](showing {len(jobs)} of {total_new})[/dim]\n")
        display_job_table(jobs, "")


@cli.command()
@click.option('--status', multiple=True, help='Filter by status (can specify multiple)')
@click.option('--limit', type=int, default=20, help='Max jobs to show')
def list_jobs(status, limit):
    """List jobs from database with filters"""
    cli_art.display_list_header()

    # If no status provided, show common ones
    if not status:
        status = ['new', 'docs_ready', 'processing', 'applied_success', 'application_applied_success']

    console.print(f"[bold cyan]📋 Filtering by status:[/bold cyan] [yellow]{', '.join(status)}[/yellow]\n")

    jobs = database.get_jobs_by_status(list(status), limit=limit)

    if jobs:
        display_job_table(jobs, f"Jobs (showing {len(jobs)})")
    else:
        console.print("[yellow]⚠ No jobs found with the specified filters.[/yellow]")


@cli.command()
@click.option('--job-id', help='Specific job primary_identifier')
@click.option('--interactive', '-i', is_flag=True, help='Interactive job selection')
@click.option('--batch', type=int, help='Generate docs for multiple jobs (specify count)')
def generate_docs(job_id, interactive, batch):
    """Generate resume and cover letter for jobs"""
    cli_art.display_generate_header()

    jobs_to_process = []

    if batch:
        # Batch mode - process multiple jobs
        console.print(f"\n[bold cyan]Fetching up to {batch} jobs for document generation...[/bold cyan]\n")
        jobs_to_process = database.get_jobs_by_status(
            ['new', 'tailoring_failed', 'generation_failed'],
            limit=batch
        )

        if not jobs_to_process:
            console.print("[yellow]No jobs available for document generation.[/yellow]")
            return

        console.print(f"[green]Found {len(jobs_to_process)} jobs for processing[/green]\n")
        display_job_table(jobs_to_process, "Jobs for Document Generation")

        if not Confirm.ask("\n[yellow]Proceed with batch generation?[/yellow]"):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    elif interactive or not job_id:
        # Interactive mode - single job selection
        console.print("\n[bold cyan]Select a job to generate documents:[/bold cyan]\n")

        jobs = database.get_jobs_by_status(
            ['new', 'tailoring_failed', 'generation_failed'],
            limit=50
        )

        if not jobs:
            console.print("[yellow]No jobs available for document generation.[/yellow]")
            return

        # Create choices
        choices = []
        for job in jobs:
            company = job.get('company_name', 'N/A')
            title = job.get('job_title', 'N/A')
            status = job.get('status', 'N/A')
            choices.append({
                'name': f"{company[:30]} - {title[:40]} [{status}]",
                'value': job.get('primary_identifier')
            })

        job_id = questionary.select(
            "Select a job:",
            choices=choices,
            style=custom_style
        ).ask()

        if not job_id:
            console.print("[yellow]No job selected.[/yellow]")
            return

        # Fetch single job data
        job_data = database.get_job_by_primary_id(job_id)
        if not job_data:
            console.print(f"[red]Job not found: {job_id}[/red]")
            return
        jobs_to_process = [job_data]

    else:
        # Direct job ID mode
        job_data = database.get_job_by_primary_id(job_id)
        if not job_data:
            console.print(f"[red]Job not found: {job_id}[/red]")
            return
        jobs_to_process = [job_data]

    # Process each job with clean UI
    job_results = []  # Store results for final table

    # Create overall progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[cyan]{task.completed}/{task.total} jobs"),
        console=console,
        transient=False
    ) as overall_progress:

        overall_task = overall_progress.add_task(
            "📄 Generating documents...",
            total=len(jobs_to_process)
        )

        for idx, job_data in enumerate(jobs_to_process, 1):
            primary_id = job_data.get('primary_identifier')
            company = job_data.get('company_name', 'N/A')
            title = job_data.get('job_title', 'N/A')

            # Update overall progress
            overall_progress.update(
                overall_task,
                description=f"📄 Processing: {company} - {title[:30]}..."
            )

            # Process job silently with V2
            success, error_msg, ats_score = _process_single_job_docs(job_data, primary_id)

            # Store result for summary (including ATS score)
            job_results.append({
                'company': company,
                'title': title,
                'success': success,
                'error': error_msg if not success else None,
                'ats_score': ats_score
            })

            # Update progress
            overall_progress.advance(overall_task)

            # Brief delay between jobs
            if idx < len(jobs_to_process):
                time.sleep(1)

    # Show beautiful summary table
    _display_generation_summary(job_results, len(jobs_to_process))


def _process_single_job_docs(job_data, primary_id):
    """Process document generation for a single job with V2 ATS optimization

    Returns:
        tuple: (success: bool, error_message: str or None, ats_score: int or None)
    """
    try:
        # Create output directory
        base_output_path = PROJECT_ROOT / config.BASE_OUTPUT_DIR_NAME
        create_dir_if_not_exists(base_output_path)

        job_db_id = job_data.get('_id')
        id_part = sanitize_filename_component(str(job_db_id), 24)
        company = sanitize_filename_component(job_data.get('company_name', 'Unknown'))
        title = sanitize_filename_component(job_data.get('job_title', 'Unknown'))

        output_dir = base_output_path / f"{company}_{title}_{id_part}"
        create_dir_if_not_exists(output_dir)

        database.update_job_data(primary_id, {'job_specific_output_dir': str(output_dir)})
        database.update_job_status(primary_id, config.JOB_STATUS_PROCESSING, "Starting V2 generation with ATS optimization.")

        # Use V2 generator (ATS >= 85, one-page, aggressive tailoring)
        gen_v2 = DocumentGeneratorV2()
        results = gen_v2.generate_all_documents(job_data, str(output_dir))

        # Extract results
        resume_path = results.get('resume_pdf')
        cl_path = results.get('cover_letter_pdf')
        details_path = results.get('job_details_pdf')
        ats_score = results.get('ats_score', 0)
        ats_report = results.get('ats_report', {})

        resume_ok = resume_path and Path(resume_path).is_file()
        details_ok = details_path and Path(details_path).is_file()

        if not resume_ok or not details_ok:
            raise ValueError(f"V2 PDF generation failed (ATS: {ats_score}/100)")

        # Store results with ATS data
        database.update_job_data(primary_id, {
            'resume_pdf_path': resume_path,
            'cover_letter_pdf_path': cl_path,
            'job_details_pdf_path': details_path,
            'ats_score': ats_score,
            'ats_keyword_stats': ats_report.get('keyword_stats', {}),
            'status': config.JOB_STATUS_DOCS_READY,
            'status_reason': f'V2 docs generated (ATS: {ats_score}/100) via CLI'
        })

        return (True, None, ats_score)

    except Exception as e:
        error_msg = str(e)[:100]
        database.update_job_status(primary_id, config.JOB_STATUS_GENERATION_FAILED, str(e)[:200])
        return (False, error_msg, None)


def _display_generation_summary(job_results, total):
    """Display beautiful summary table for document generation"""
    console.print("\n")

    # Create summary stats
    success_count = sum(1 for r in job_results if r['success'])
    failed_count = total - success_count
    success_rate = (success_count / total * 100) if total > 0 else 0

    # Success rate panel
    if success_rate == 100:
        panel_style = "green"
        status_text = "✓ All documents generated successfully!"
    elif success_rate >= 50:
        panel_style = "yellow"
        status_text = "⚠ Partial success"
    else:
        panel_style = "red"
        status_text = "✗ Most operations failed"

    summary_panel = Panel(
        f"[bold]{status_text}[/bold]\n\n"
        f"[green]✓ Successful:[/green] {success_count}\n"
        f"[red]✗ Failed:[/red] {failed_count}\n"
        f"[cyan]Success Rate:[/cyan] {success_rate:.1f}%",
        title=f"[bold {panel_style}]Document Generation Complete[/bold {panel_style}]",
        border_style=panel_style,
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(summary_panel)

    # Calculate average ATS score for successful jobs
    successful_jobs = [r for r in job_results if r['success'] and r.get('ats_score')]
    avg_ats = sum(r['ats_score'] for r in successful_jobs) / len(successful_jobs) if successful_jobs else 0

    # Detailed results table
    if total > 1:  # Only show table for batch operations
        console.print("\n[bold]Detailed Results:[/bold]\n")

        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Company", style="cyan", width=22)
        table.add_column("Title", style="blue", width=30)
        table.add_column("ATS Score", style="magenta", width=12)
        table.add_column("Status", style="yellow", width=15)

        for idx, result in enumerate(job_results, 1):
            status_display = "[green]✓ Success[/green]" if result['success'] else "[red]✗ Failed[/red]"

            # ATS score display with color coding
            ats_score = result.get('ats_score')
            if ats_score:
                if ats_score >= 90:
                    ats_display = f"[bold green]{ats_score}/100[/bold green]"
                elif ats_score >= 85:
                    ats_display = f"[green]{ats_score}/100[/green]"
                elif ats_score >= 80:
                    ats_display = f"[yellow]{ats_score}/100[/yellow]"
                else:
                    ats_display = f"[red]{ats_score}/100[/red]"
            else:
                ats_display = "[dim]N/A[/dim]"

            table.add_row(
                str(idx),
                result['company'][:22],
                result['title'][:30],
                ats_display,
                status_display
            )

        console.print(table)

        # Show average ATS score
        if avg_ats > 0:
            console.print(f"\n[bold cyan]Average ATS Score:[/bold cyan] [bold]{avg_ats:.1f}/100[/bold]")

    # Show failed jobs details if any
    failed_jobs = [r for r in job_results if not r['success']]
    if failed_jobs:
        console.print("\n[bold red]Failed Jobs (check logs/cli.log for details):[/bold red]")
        for job in failed_jobs:
            console.print(f"  [red]•[/red] {job['company']} - {job['title'][:40]}")

    console.print()


def _display_application_summary(job_results, total):
    """Display beautiful summary table for job applications"""
    console.print("\n")

    # Create summary stats
    success_count = sum(1 for r in job_results if r['success'])
    failed_count = total - success_count
    success_rate = (success_count / total * 100) if total > 0 else 0

    # Count by status type
    applied = sum(1 for r in job_results if r['status'] == config.JOB_STATUS_APPLIED_SUCCESS)
    manual = sum(1 for r in job_results if r['status'] == config.JOB_STATUS_MANUAL_INTERVENTION_SUBMITTED)
    easy_apply = sum(1 for r in job_results if r['status'] == 'easy_apply_processed')

    # Success rate panel
    if success_rate == 100:
        panel_style = "green"
        status_text = "✓ All applications submitted successfully!"
    elif success_rate >= 50:
        panel_style = "yellow"
        status_text = "⚠ Partial success"
    else:
        panel_style = "red"
        status_text = "✗ Most applications failed"

    summary_panel = Panel(
        f"[bold]{status_text}[/bold]\n\n"
        f"[green]✓ Auto-Applied:[/green] {applied}\n"
        f"[green]✓ Manual Submission:[/green] {manual}\n"
        f"[yellow]⚠ Easy Apply:[/yellow] {easy_apply}\n"
        f"[red]✗ Failed:[/red] {failed_count}\n"
        f"[cyan]Success Rate:[/cyan] {success_rate:.1f}%",
        title=f"[bold {panel_style}]Application Complete[/bold {panel_style}]",
        border_style=panel_style,
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(summary_panel)

    # Detailed results table
    if total > 1:  # Only show table for batch operations
        console.print("\n[bold]Detailed Results:[/bold]\n")

        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Company", style="cyan", width=25)
        table.add_column("Title", style="blue", width=30)
        table.add_column("Result", style="yellow", width=20)

        for idx, result in enumerate(job_results, 1):
            if result['success']:
                status_display = "[green]✓ Submitted[/green]"
            else:
                status_display = f"[red]✗ {result['status'][:15]}[/red]"

            table.add_row(
                str(idx),
                result['company'][:25],
                result['title'][:30],
                status_display
            )

        console.print(table)

    # Show failed jobs details if any
    failed_jobs = [r for r in job_results if not r['success']]
    if failed_jobs:
        console.print("\n[bold red]Failed Applications (check logs/cli.log for details):[/bold red]")
        for job in failed_jobs:
            console.print(f"  [red]•[/red] {job['company']} - {job['title'][:40]} [{job['status']}]")

    console.print()


@cli.command()
@click.option('--job-id', help='Specific job primary_identifier')
@click.option('--interactive', '-i', is_flag=True, help='Interactive job selection')
@click.option('--batch', type=int, help='Apply to multiple jobs (specify count)')
def apply(job_id, interactive, batch):
    """Apply to jobs through automated form filling"""
    cli_art.display_apply_header()

    jobs_to_apply = []

    if batch:
        # Batch mode
        console.print(f"\n[bold cyan]Fetching up to {batch} jobs ready for application...[/bold cyan]\n")
        jobs_to_apply = database.get_jobs_by_status([config.JOB_STATUS_DOCS_READY], limit=batch)

        if not jobs_to_apply:
            console.print("[yellow]No jobs found with status 'docs_ready'[/yellow]")
            return

        console.print(f"[green]Found {len(jobs_to_apply)} jobs ready for application[/green]\n")
        display_job_table(jobs_to_apply, "Jobs to Apply")

        if not Confirm.ask("\n[yellow]Proceed with batch application?[/yellow]"):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    elif interactive or not job_id:
        # Interactive single selection
        console.print("\n[bold cyan]Select a job to apply:[/bold cyan]\n")

        jobs = database.get_jobs_by_status([config.JOB_STATUS_DOCS_READY], limit=50)

        if not jobs:
            console.print("[yellow]No jobs ready for application.[/yellow]")
            console.print("[dim]Tip: Use 'generate-docs' command first[/dim]")
            return

        choices = []
        for job in jobs:
            company = job.get('company_name', 'N/A')
            title = job.get('job_title', 'N/A')
            app_url = job.get('application_url', 'N/A')
            url_display = app_url[:50] + '...' if len(app_url) > 50 else app_url
            choices.append({
                'name': f"{company[:25]} - {title[:35]}\n  └─ {url_display}",
                'value': job.get('primary_identifier')
            })

        job_id = questionary.select(
            "Select a job:",
            choices=choices,
            style=custom_style
        ).ask()

        if not job_id:
            console.print("[yellow]No job selected.[/yellow]")
            return

        job_data = database.get_job_by_primary_id(job_id)
        if job_data:
            jobs_to_apply = [job_data]

    else:
        # Direct job ID
        job_data = database.get_job_by_primary_id(job_id)
        if not job_data:
            console.print(f"[red]Job not found: {job_id}[/red]")
            return
        jobs_to_apply = [job_data]

    # Setup processed directories
    processed_base_path = PROJECT_ROOT / config.PROCESSED_APPS_DIR_NAME
    success_path = processed_base_path / config.SUCCESS_DIR_NAME
    failure_path = processed_base_path / config.FAILURE_DIR_NAME
    easy_apply_path = processed_base_path / config.EASY_APPLY_DIR_NAME

    try:
        for p in [processed_base_path, success_path, failure_path, easy_apply_path]:
            create_dir_if_not_exists(p)
    except Exception as e:
        console.print(f"[red]Failed to create processed directories: {e}[/red]")
        return

    processed_paths = {
        "success": str(success_path),
        "failure": str(failure_path),
        "easy_apply": str(easy_apply_path)
    }

    # Apply to jobs with beautiful progress
    job_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]{task.description}"),
        BarColumn(complete_style="magenta", finished_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[cyan]{task.completed}/{task.total} applications"),
        console=console,
        transient=False
    ) as overall_progress:

        overall_task = overall_progress.add_task(
            "🚀 Submitting applications...",
            total=len(jobs_to_apply)
        )

        for idx, job_data in enumerate(jobs_to_apply, 1):
            primary_id = job_data.get('primary_identifier')
            company = job_data.get('company_name', 'N/A')
            title = job_data.get('job_title', 'N/A')

            # Update progress
            overall_progress.update(
                overall_task,
                description=f"🚀 Applying: {company} - {title[:30]}..."
            )

            try:
                result_status = automator_main.attempt_application(
                    job_data=job_data,
                    processed_paths=processed_paths
                )

                # Store result
                job_results.append({
                    'company': company,
                    'title': title,
                    'status': result_status,
                    'success': result_status in [config.JOB_STATUS_APPLIED_SUCCESS, config.JOB_STATUS_MANUAL_INTERVENTION_SUBMITTED]
                })

            except Exception as e:
                job_results.append({
                    'company': company,
                    'title': title,
                    'status': 'error',
                    'success': False,
                    'error': str(e)[:100]
                })

            # Update progress
            overall_progress.advance(overall_task)

            # Human-like delay between applications (rate limiting)
            if idx < len(jobs_to_apply):
                import random
                delay = random.randint(config.APPLICATION_DELAY_MIN, config.APPLICATION_DELAY_MAX)
                console.print(f"[dim]⏳ Waiting {delay}s before next application (human-like behavior)...[/dim]")
                time.sleep(delay)

    # Show beautiful summary
    _display_application_summary(job_results, len(jobs_to_apply))


@cli.command()
@click.option('--all', 'show_all', is_flag=True, help='Show all status types')
def status(show_all):
    """Show application statistics and status overview"""
    cli_art.display_status_header()

    # Define status categories
    if show_all:
        status_list = [
            'new', 'processing', 'docs_ready', 'application_in_progress',
            'applied_success', 'application_applied_success',
            'application_failed_ats', 'tailoring_failed', 'generation_failed',
            'manual_intervention_submitted', 'manual_intervention_closed_by_user',
            'easy_apply_processed', 'error_unknown'
        ]
    else:
        status_list = [
            'new', 'docs_ready', 'applied_success', 'application_applied_success',
            'application_failed_ats', 'easy_apply_processed'
        ]

    # Create status table
    table = Table(title="Job Status Summary", box=box.ROUNDED)
    table.add_column("Status", style="cyan", width=30)
    table.add_column("Count", style="magenta", justify="right", width=10)

    total = 0
    for status_name in status_list:
        jobs = database.get_jobs_by_status([status_name], limit=1000)
        count = len(jobs)
        total += count

        if count > 0 or show_all:
            # Color code the count
            color = "green" if count > 0 else "dim"
            table.add_row(status_name, f"[{color}]{count}[/{color}]")

    console.print(table)
    console.print(f"\n[bold]Total Jobs in Database:[/bold] {total}")


@cli.command()
def setup():
    """Run interactive setup wizard for first-time configuration"""
    try:
        from setup_wizard import SetupWizard
        wizard = SetupWizard()
        wizard.run()
    except ImportError:
        console.print("[red]Setup wizard not found. Please ensure setup_wizard.py exists.[/red]")
    except Exception as e:
        console.print(f"[red]Setup failed: {e}[/red]")


@cli.command()
def validate_config():
    """Validate your configuration and show any issues"""
    try:
        from config_validator import validate_configuration
        is_valid = validate_configuration(verbose=True, exit_on_error=False)
        if is_valid:
            console.print("\n[bold green]Configuration is valid and ready to use! 🎉[/bold green]\n")
        else:
            console.print("\n[bold red]Please fix the configuration errors above.[/bold red]\n")
    except ImportError:
        console.print("[red]Configuration validator not found.[/red]")


@cli.command(name='config')
def config_command():
    """Validate and check configuration (alias for validate-config)"""
    try:
        from config_validator import validate_configuration
        is_valid = validate_configuration(verbose=True, exit_on_error=False)
        if is_valid:
            console.print("\n[bold green]Configuration is valid and ready to use! 🎉[/bold green]\n")
        else:
            console.print("\n[bold red]Please fix the configuration errors above.[/bold red]\n")
    except ImportError:
        console.print("[red]Configuration validator not found.[/red]")


@cli.command()
def config_info():
    """Display current configuration"""
    display_banner()

    console.print("\n[bold cyan]Configuration Information[/bold cyan]\n")

    panel_content = f"""
[cyan]Database:[/cyan]
  Connection: {'✓ Connected' if database.jobs_collection is not None else '✗ Not Connected'}
  Database: {config.DB_NAME}

[cyan]Scraping:[/cyan]
  LinkedIn: {'✓ Configured' if config.LINKEDIN_SESSION_COOKIE else '✗ Not Configured'}
  JobRight: {'✓ Configured' if config.JOBRIGHT_COOKIE_STRING else '✗ Not Configured'}
  Job Limit: {config.SCRAPER_JOB_LIMIT}

[cyan]AI:[/cyan]
  Gemini API: {'✓ Configured' if config.GEMINI_API_KEY else '✗ Not Configured'}
  Model: {config.GEMINI_MODEL_NAME}

[cyan]User Profile:[/cyan]
  Name: {config.YOUR_NAME or '[red]Not set[/red]'}
  Email: {config.YOUR_EMAIL or '[red]Not set[/red]'}
  Phone: {config.YOUR_PHONE or '[red]Not set[/red]'}

[cyan]Directories:[/cyan]
  Output: {PROJECT_ROOT / config.BASE_OUTPUT_DIR_NAME}
  Processed: {PROJECT_ROOT / config.PROCESSED_APPS_DIR_NAME}
  Logs: {PROJECT_ROOT / config.LOG_DIR_NAME}
    """

    console.print(Panel(panel_content, title="Configuration", border_style="cyan"))

    # Suggest validation
    if not all([config.YOUR_NAME, config.YOUR_EMAIL, config.GEMINI_API_KEY]):
        console.print("\n[yellow]⚠ Some required fields appear to be missing.[/yellow]")
        console.print(f"[cyan]Run:[/cyan] python cli.py validate-config")
        console.print(f"[cyan]Or run:[/cyan] python cli.py setup\n")


@cli.command()
def interactive():
    """Launch interactive mode with a menu"""
    display_banner()

    while True:
        console.print()
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                {'name': '📥 Fetch Jobs (from LinkedIn/JobRight)', 'value': 'fetch'},
                {'name': '📋 List Jobs (view fetched jobs)', 'value': 'list'},
                {'name': '📄 Generate Documents (resume + cover letter)', 'value': 'generate'},
                {'name': '🚀 Apply to Jobs (automated)', 'value': 'apply'},
                {'name': '📊 View Status', 'value': 'status'},
                {'name': '❌ Exit', 'value': 'exit'}
            ],
            style=custom_style
        ).ask()

        if choice == 'exit' or not choice:
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            break
        elif choice == 'fetch':
            source = questionary.select(
                "Select source:",
                choices=['both', 'linkedin', 'jobright'],
                style=custom_style
            ).ask()

            limit_str = questionary.text(
                "How many jobs to fetch? (recommended: 20)",
                default="20",
                style=custom_style
            ).ask()

            if source and limit_str and limit_str.isdigit():
                from click.testing import CliRunner
                runner = CliRunner()
                runner.invoke(fetch_jobs, ['--source', source, '--limit', limit_str])
        elif choice == 'list':
            from click.testing import CliRunner
            runner = CliRunner()
            runner.invoke(list_jobs)
        elif choice == 'generate':
            from click.testing import CliRunner
            runner = CliRunner()
            runner.invoke(generate_docs, ['--interactive'])
        elif choice == 'apply':
            mode = questionary.select(
                "Application mode:",
                choices=[
                    {'name': 'Single job (interactive)', 'value': 'single'},
                    {'name': 'Batch (multiple jobs)', 'value': 'batch'}
                ],
                style=custom_style
            ).ask()

            if mode == 'single':
                from click.testing import CliRunner
                runner = CliRunner()
                runner.invoke(apply, ['--interactive'])
            elif mode == 'batch':
                count = questionary.text(
                    "How many jobs to apply to?",
                    default="5",
                    style=custom_style
                ).ask()
                if count and count.isdigit():
                    from click.testing import CliRunner
                    runner = CliRunner()
                    runner.invoke(apply, ['--batch', count])
        elif choice == 'status':
            from click.testing import CliRunner
            runner = CliRunner()
            runner.invoke(status)


if __name__ == '__main__':
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        logging.error(f"Fatal CLI error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        try:
            database.close_db()
        except:
            pass
