"""
ASCII Art and UI Elements for Job Agent CLI
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

# Main Banner with ASCII Art
MAIN_BANNER = """
[bold cyan]

     ██╗ ██████╗ ██████╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗
     ██║██╔═══██╗██╔══██╗    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
     ██║██║   ██║██████╔╝    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
██   ██║██║   ██║██╔══██╗    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
╚█████╔╝╚██████╔╝██████╔╝    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
 ╚════╝  ╚═════╝ ╚═════╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
                                                                                               
[/bold cyan]
[dim]                    AI-Powered Job Application Automation[/dim]
"""

FETCH_JOBS_BANNER = """
[bold yellow]

███████╗███████╗████████╗ ██████╗██╗  ██╗         ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██╔════╝╚══██╔══╝██╔════╝██║  ██║         ██║██╔═══██╗██╔══██╗██╔════╝
█████╗  █████╗     ██║   ██║     ███████║         ██║██║   ██║██████╔╝███████╗
██╔══╝  ██╔══╝     ██║   ██║     ██╔══██║    ██   ██║██║   ██║██╔══██╗╚════██║
██║     ███████╗   ██║   ╚██████╗██║  ██║    ╚█████╔╝╚██████╔╝██████╔╝███████║
╚═╝     ╚══════╝   ╚═╝    ╚═════╝╚═╝  ╚═╝     ╚════╝  ╚═════╝ ╚═════╝ ╚══════╝                                                                          

[/bold yellow]
[dim]                    Scraping jobs from LinkedIn & JobRight...[/dim]
"""

GENERATE_DOCS_BANNER = """
[bold green]

 ██████╗ ███████╗███╗   ██╗███████╗██████╗  █████╗ ████████╗███████╗    ██████╗  ██████╗  ██████╗███████╗
██╔════╝ ██╔════╝████╗  ██║██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝    ██╔══██╗██╔═══██╗██╔════╝██╔════╝
██║  ███╗█████╗  ██╔██╗ ██║█████╗  ██████╔╝███████║   ██║   █████╗      ██║  ██║██║   ██║██║     ███████╗
██║   ██║██╔══╝  ██║╚██╗██║██╔══╝  ██╔══██╗██╔══██║   ██║   ██╔══╝      ██║  ██║██║   ██║██║     ╚════██║
╚██████╔╝███████╗██║ ╚████║███████╗██║  ██║██║  ██║   ██║   ███████╗    ██████╔╝╚██████╔╝╚██████╗███████║
 ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝    ╚═════╝  ╚═════╝  ╚═════╝╚══════╝                                                                                                      
                                                                                                              
[/bold green]
        [dim]📄 Creating tailored resume & cover letter with AI...[/dim]
"""

APPLY_JOBS_BANNER = """
[bold magenta]

 █████╗ ██████╗ ██████╗ ██╗  ██╗   ██╗         ██╗ ██████╗ ██████╗ ███████╗
██╔══██╗██╔══██╗██╔══██╗██║  ╚██╗ ██╔╝         ██║██╔═══██╗██╔══██╗██╔════╝
███████║██████╔╝██████╔╝██║   ╚████╔╝          ██║██║   ██║██████╔╝███████╗
██╔══██║██╔═══╝ ██╔═══╝ ██║    ╚██╔╝      ██   ██║██║   ██║██╔══██╗╚════██║
██║  ██║██║     ██║     ███████╗██║       ╚█████╔╝╚██████╔╝██████╔╝███████║
╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚═╝        ╚════╝  ╚═════╝ ╚═════╝ ╚══════╝                                                               
                                                                                                                                                  
[/bold magenta]
                    [dim]🚀 Automated application in progress...[/dim]
"""

STATUS_BANNER = """
[bold blue]

██╗     ██╗███████╗████████╗         ██╗ ██████╗ ██████╗ ███████╗
██║     ██║██╔════╝╚══██╔══╝         ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║███████╗   ██║            ██║██║   ██║██████╔╝███████╗
██║     ██║╚════██║   ██║       ██   ██║██║   ██║██╔══██╗╚════██║
███████╗██║███████║   ██║       ╚█████╔╝╚██████╔╝██████╔╝███████║
╚══════╝╚═╝╚══════╝   ╚═╝        ╚════╝  ╚═════╝ ╚═════╝ ╚══════╝                                                             
                                                                                                                                                                                                                                       
[/bold blue]
        [dim]📊 Application statistics & overview[/dim]
"""

LIST_JOBS_BANNER = """
[bold cyan]

     ██╗ ██████╗ ██████╗     ███████╗████████╗ █████╗ ████████╗██╗   ██╗███████╗
     ██║██╔═══██╗██╔══██╗    ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██║   ██║██╔════╝
     ██║██║   ██║██████╔╝    ███████╗   ██║   ███████║   ██║   ██║   ██║███████╗
██   ██║██║   ██║██╔══██╗    ╚════██║   ██║   ██╔══██║   ██║   ██║   ██║╚════██║
╚█████╔╝╚██████╔╝██████╔╝    ███████║   ██║   ██║  ██║   ██║   ╚██████╔╝███████║
 ╚════╝  ╚═════╝ ╚═════╝     ╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚══════╝
                                                                                                                                                     
[/bold cyan]
        [dim]📋 Browse and filter your job applications[/dim]
"""

# Loading animations
LOADING_FRAMES = [
    "[cyan]⣾[/cyan]",
    "[cyan]⣽[/cyan]",
    "[cyan]⣻[/cyan]",
    "[cyan]⢿[/cyan]",
    "[cyan]⡿[/cyan]",
    "[cyan]⣟[/cyan]",
    "[cyan]⣯[/cyan]",
    "[cyan]⣷[/cyan]",
]

FETCH_LOADING = [
    "[yellow]🌐 Connecting to LinkedIn...[/yellow]",
    "[yellow]🔍 Searching for jobs...[/yellow]",
    "[yellow]📥 Fetching job listings...[/yellow]",
    "[yellow]💾 Saving to database...[/yellow]",
]

GENERATE_LOADING = [
    "[green]🤖 Analyzing job description...[/green]",
    "[green]📝 Tailoring resume sections...[/green]",
    "[green]✍️  Writing cover letter...[/green]",
    "[green]📄 Generating PDF documents...[/green]",
]

APPLY_LOADING = [
    "[magenta]🎯 Identifying ATS platform...[/magenta]",
    "[magenta]📋 Analyzing form fields...[/magenta]",
    "[magenta]⌨️  Filling out application...[/magenta]",
    "[magenta]📤 Submitting application...[/magenta]",
]

# Success/Error symbols
SUCCESS = "[bold green]✓[/bold green]"
ERROR = "[bold red]✗[/bold red]"
WARNING = "[bold yellow]⚠[/bold yellow]"
INFO = "[bold cyan]ℹ[/bold cyan]"
ROCKET = "🚀"
ROBOT = "🤖"
DOCUMENT = "📄"
CHECKMARK = "✓"
CROSSMARK = "✗"

# Box styles for different sections
FETCH_BOX = box.DOUBLE
GENERATE_BOX = box.ROUNDED
APPLY_BOX = box.HEAVY
STATUS_BOX = box.SIMPLE
LIST_BOX = box.MINIMAL

def display_help_screen():
    """Display beautiful help screen with ASCII art"""
    console.clear()
    console.print(MAIN_BANNER)

    help_text = """
[bold white]USAGE:[/bold white]
    [cyan]job-agent[/cyan] [yellow]<COMMAND>[/yellow] [dim][OPTIONS][/dim]

[bold white]COMMANDS:[/bold white]
    [yellow]fetch-jobs[/yellow]        Fetch jobs from LinkedIn & JobRight
    [yellow]list-jobs[/yellow]         Browse and filter saved jobs
    [yellow]generate-docs[/yellow]     Create tailored resume & cover letter
    [yellow]apply[/yellow]             Apply to jobs automatically
    [yellow]status[/yellow]            View application statistics
    [yellow]interactive[/yellow]       Launch interactive menu mode

[bold white]OPTIONS:[/bold white]
    [dim]-v, --verbose[/dim]      Enable detailed logging
    [dim]-h, --help[/dim]         Show this help message

[bold white]EXAMPLES:[/bold white]
    [dim]# Fetch 20 jobs from LinkedIn (safe limit)[/dim]
    [cyan]$[/cyan] job-agent fetch-jobs --limit 20 --source linkedin

    [dim]# Generate documents for a specific job (interactive)[/dim]
    [cyan]$[/cyan] job-agent generate-docs --interactive

    [dim]# Generate documents for multiple jobs in batch[/dim]
    [cyan]$[/cyan] job-agent generate-docs --batch 5

    [dim]# Apply to multiple jobs in batch[/dim]
    [cyan]$[/cyan] job-agent apply --batch 5

    [dim]# Check application status[/dim]
    [cyan]$[/cyan] job-agent status

[bold white]LEARN MORE:[/bold white]
    Documentation: [link]README_CLI.md[/link]
    Quick Start:   [link]GETTING_STARTED.md[/link]
    """

    panel = Panel(
        help_text,
        title="[bold cyan]Job Agent CLI - Help[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    )

    console.print(panel)
    console.print("\n[dim]Run 'job-agent interactive' for guided menu system[/dim]\n")


def display_fetch_header(source, limit):
    """Display fetch jobs header"""
    console.clear()
    console.print(FETCH_JOBS_BANNER)

    info = f"""
[bold]Source:[/bold] [yellow]{source.upper()}[/yellow]
[bold]Limit:[/bold]  [yellow]{limit} jobs[/yellow]
[bold]Safety:[/bold] {'[green]✓ Safe[/green]' if limit <= 30 else '[yellow]⚠ Caution[/yellow]' if limit <= 50 else '[red]⚠ WARNING[/red]'}
    """

    panel = Panel(
        info,
        title="[yellow]Configuration[/yellow]",
        border_style="yellow",
        box=FETCH_BOX,
        padding=(0, 2)
    )
    console.print(panel)
    console.print()


def display_generate_header():
    """Display generate docs header"""
    console.clear()
    console.print(GENERATE_DOCS_BANNER)
    console.print()


def display_apply_header():
    """Display apply jobs header"""
    console.clear()
    console.print(APPLY_JOBS_BANNER)
    console.print()


def display_status_header():
    """Display status header"""
    console.clear()
    console.print(STATUS_BANNER)
    console.print()


def display_list_header():
    """Display list jobs header"""
    console.clear()
    console.print(LIST_JOBS_BANNER)
    console.print()


# LinkedIn-specific art
LINKEDIN_ART = """
[bold blue]

██╗     ██╗███╗   ██╗██╗  ██╗███████╗██████╗ ██╗███╗   ██╗
██║     ██║████╗  ██║██║ ██╔╝██╔════╝██╔══██╗██║████╗  ██║
██║     ██║██╔██╗ ██║█████╔╝ █████╗  ██║  ██║██║██╔██╗ ██║
██║     ██║██║╚██╗██║██╔═██╗ ██╔══╝  ██║  ██║██║██║╚██╗██║
███████╗██║██║ ╚████║██║  ██╗███████╗██████╔╝██║██║ ╚████║
╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═══╝

[/bold blue]
"""

# JobRight-specific art
JOBRIGHT_ART = """
[bold cyan]

     ██╗ ██████╗ ██████╗ ██████╗ ██╗ ██████╗ ██╗  ██╗████████╗
     ██║██╔═══██╗██╔══██╗██╔══██╗██║██╔════╝ ██║  ██║╚══██╔══╝
     ██║██║   ██║██████╔╝██████╔╝██║██║  ███╗███████║   ██║   
██   ██║██║   ██║██╔══██╗██╔══██╗██║██║   ██║██╔══██║   ██║   
╚█████╔╝╚██████╔╝██████╔╝██║  ██║██║╚██████╔╝██║  ██║   ██║   
 ╚════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   

[/bold cyan]
"""

# Progress bar art
PROGRESS_BAR = """
[cyan]╔════════════════════════════════════════════════════════╗
║ {bar}  {percent}% ║
╚════════════════════════════════════════════════════════╝[/cyan]
"""


def create_progress_bar(percent):
    """Create a fancy progress bar"""
    filled = int(percent / 2)
    bar = "█" * filled + "░" * (50 - filled)
    return PROGRESS_BAR.format(bar=bar, percent=percent)


# Application result art
SUCCESS_ART = """
[bold green]
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║          ✓ SUCCESS!                   ║
    ║                                       ║
    ║     Application Submitted             ║
    ║                                       ║
    ╚═══════════════════════════════════════╝
[/bold green]
"""

FAILURE_ART = """
[bold red]
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║          ✗ FAILED                     ║
    ║                                       ║
    ║     Application Not Completed         ║
    ║                                       ║
    ╚═══════════════════════════════════════╝
[/bold red]
"""

WARNING_ART = """
[bold yellow]
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║          ⚠ WARNING                    ║
    ║                                       ║
    ║     Rate Limit Exceeded!              ║
    ║                                       ║
    ╚═══════════════════════════════════════╝
[/bold yellow]
"""
