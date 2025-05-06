import os
import logging
import google.generativeai as genai

# Import utilities, including the escape function
# Assumes utils.py is in the parent directory (project root)
import sys
# Add project root to path if utils is there
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from utils import escape_latex
    import config # To get API key, model name etc.
    # Assuming generator loads templates now, tailor just needs the content parts
    # from document_generator.generator import load_template # If tailor needs to load base
except ImportError as e:
     logging.critical(f"Error importing required modules in tailor.py: {e}", exc_info=True)
     raise

logging.info("resume_tailor/tailor.py module loading...")

# --- Gemini Configuration ---
gemini_model = None
try:
    logging.info("Configuring Gemini API client...")
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    genai.configure(api_key=config.GEMINI_API_KEY)

    logging.info(f"Attempting to initialize Gemini model: {config.GEMINI_MODEL_NAME}...")
    # Configure generation settings if needed
    generation_config = {
        "temperature": 0.7, # Adjust creativity/factualness
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 8192, # Max for Flash 1.5, adjust if needed
    }
    safety_settings = [ # Adjust safety settings as needed
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    gemini_model = genai.GenerativeModel(model_name=config.GEMINI_MODEL_NAME,
                                      generation_config=generation_config,
                                      safety_settings=safety_settings)
    logging.info(f"Gemini API configured successfully with model: {config.GEMINI_MODEL_NAME}")
    gemini_client_status = "Success"
except Exception as e:
    logging.error(f"Failed to configure Gemini API: {e}", exc_info=True)
    gemini_client_status = f"Failed: {e}"

logging.info(f"Gemini client configuration status: {gemini_client_status}")


# --- Constants ---
# Assuming the base template is loaded elsewhere or defined here
# For simplicity, let's define the structure parts here.
# In a real scenario, you might load resume_template.tex and use string formatting.

RESUME_PREAMBLE = r"""%-------------------------
% Resume in Latex
% Author : Jake Gutierrez / Modifications for Job Agent
% Based off of: https://github.com/sb2nov/resume
% License : MIT
%------------------------

\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref} % Keep hidelinks if you prefer no boxes around links
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{xurl} % <<< For better line breaking
% \usepackage{fontawesome5} % Uncomment if you want to use icons in the header
\input{glyphtounicode}

%----------FONT OPTIONS----------
% sans-serif
% \usepackage[sfdefault]{FiraSans}
% \usepackage[sfdefault]{roboto}
% \usepackage[sfdefault]{noto-sans}
% \usepackage[default]{sourcesanspro} % A good, clean sans-serif option

% serif
% \usepackage{CormorantGaramond}
% \usepackage{charter} % A good serif option


\pagestyle{fancy}
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.0in}

% Set URL style - \urlstyle{same} uses the current text font
\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Ensure that generated pdf is machine readable/ATS parsable
\pdfgentounicode=1

%-------------------------
% Custom commands (Keep these as they define the resume structure)
\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubSubheading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

%-------------------------------------------
%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%


\begin{document}
"""

RESUME_HEADER = r"""
%----------HEADING----------
\begin{center}
    \textbf{\Huge \scshape Bhupesh Chikara} \\ \vspace{1pt}
    \small +1 (315) 575 7385 $|$
    \href{mailto:bchikara@syr.edu}{\nolinkurl{bchikara@syr.edu}} $|$
    \href{https://linkedin.com/in/bchikara}{\nolinkurl{linkedin.com/in/bchikara}} $|$
    \href{https://github.com/bchikara}{\nolinkurl{github.com/bchikara}} $|$
    \href{https://leetcode.com/bchikara}{\nolinkurl{leetcode.com/bchikara}}
\end{center}
"""

RESUME_EDUCATION = r"""
%-----------EDUCATION-----------
\section{Education}
  \resumeSubHeadingListStart
    \resumeSubheading
      {Syracuse University}{Syracuse, NY}
      {Master of Science in Computer Science}{Jan 2024 -- Dec 2025}
    \resumeSubheading
      {DIT University}{Dehradun, India}
      {Bachelor of Technology in Computer Science and Engineering}{Aug 2016 -- May 2020}
  \resumeSubHeadingListEnd
"""

RESUME_EXPERIENCE_START = r"""
%-----------EXPERIENCE-----------
\section{Experience}
  \resumeSubHeadingListStart
"""
RESUME_EXPERIENCE_END = r"""
  \resumeSubHeadingListEnd
"""

RESUME_PROJECTS_START = r"""
%-----------PROJECTS-----------
\section{Projects}
    \resumeSubHeadingListStart
"""
RESUME_PROJECTS_END = r"""
    \resumeSubHeadingListEnd
"""

RESUME_SKILLS_START = r"""
%-----------TECHNICAL SKILLS-----------
\section{Technical Skills}
 \begin{itemize}[leftmargin=0.15in, itemsep=1pt, topsep=2pt, parsep=0pt, label={}]
"""
RESUME_SKILLS_END = r"""
 \end{itemize}
"""

RESUME_FOOTER = r"""
%-------------------------------------------
\end{document}
"""

# --- Helper Functions ---

def format_experience_entry(exp_data):
    """Formats a single experience entry into LaTeX, applying escaping."""
    # Extract data safely, provide defaults
    company = exp_data.get('company', 'Unknown Company')
    title = exp_data.get('title', 'Unknown Title')
    dates = exp_data.get('dates', 'Unknown Dates')
    tech = exp_data.get('technologies', '')
    location = exp_data.get('location', '')
    description_points = exp_data.get('description', []) # Expect a list of strings

    # Escape all dynamic content
    escaped_company = escape_latex(company)
    escaped_title = escape_latex(title)
    escaped_dates = escape_latex(dates)
    escaped_tech = escape_latex(tech)
    escaped_location = escape_latex(location)

    # Build the subheading part
    # Note: \textbf and \emph are LaTeX commands, don't escape them
    subheading = f"\\resumeSubheading{{\\textbf{{{escaped_company}}} $|$ \\emph{{{escaped_title}}}}}{{{escaped_dates}}}{{{escaped_tech}}}{{{escaped_location}}}"

    # Build the description items part
    items = "\\resumeItemListStart\n"
    for point in description_points:
        escaped_point = escape_latex(point)
        items += f"  \\resumeItem{{{escaped_point}}}\n"
    items += "\\resumeItemListEnd"

    return f"{subheading}\n{items}"

def format_project_entry(proj_data):
    """Formats a single project entry into LaTeX, applying escaping."""
    title = proj_data.get('title', 'Unknown Project')
    tech = proj_data.get('technologies', '')
    dates = proj_data.get('dates', 'Unknown Dates')
    description_points = proj_data.get('description', [])

    # Escape dynamic content
    escaped_title = escape_latex(title)
    escaped_tech = escape_latex(tech)
    escaped_dates = escape_latex(dates)

    # Build the heading part
    heading = f"\\resumeProjectHeading{{\\textbf{{{escaped_title}}} $|$ \\emph{{{escaped_tech}}}}}{{{escaped_dates}}}"

    # Build the description items part
    items = "\\resumeItemListStart\n"
    for point in description_points:
        escaped_point = escape_latex(point)
        items += f"  \\resumeItem{{{escaped_point}}}\n"
    items += "\\resumeItemListEnd"

    return f"{heading}\n{items}"

def format_skills_section(skills_data):
    """Formats the skills section, applying escaping."""
    # Expect skills_data to be a dict like {'Skills': '...', 'Tools': '...'}
    skills_str = skills_data.get('Skills', '')
    tools_str = skills_data.get('Tools', '')

    escaped_skills = escape_latex(skills_str)
    escaped_tools = escape_latex(tools_str)

    # Using the itemize format from the latest template
    return f"""{RESUME_SKILLS_START}
    \\item \\small \\textbf{{Skills:}} {escaped_skills}
    \\item \\small \\textbf{{Tools:}} {escaped_tools}
{RESUME_SKILLS_END}"""


def generate_tailored_resume_text(job_data):
    """
    Generates the full LaTeX string for a tailored resume.
    Placeholder for actual tailoring logic (e.g., using Gemini).
    Applies LaTeX escaping to dynamic content.
    """
    logging.info(f"Starting resume tailoring for job: {job_data.get('title')} at {job_data.get('company_name')}")

    if gemini_client_status != "Success":
        logging.error("Gemini client not configured. Cannot perform tailoring.")
        # Decide: return base resume? return None? For now, return None.
        return None

    # --- Placeholder Data (Replace with actual data extraction/Gemini calls) ---
    # This data should ideally come from parsing your base resume and then
    # potentially being modified by Gemini based on job_data['description']

    # Example: Static data matching your original resume for structure testing
    experience_data = [
        {
            'company': 'Deloitte', 'title': 'Senior Software Engineer', 'dates': 'Feb 2021 -- Jan 2024',
            'technologies': 'React, D3.js, Node.js, PHP, Three.js, Typescript, AWS', 'location': 'Bangalore, India',
            'description': [
                "Designed & implemented custom responsive fragments & dashboards for Deloitte Insights using React.js, Redux, Custom hooks, and Context API, resulting in a 35% increase in user interaction rates.",
                "Leveraged D3.js to enable real-time exploration of charts, graphs, and maps within dashboards, reducing decision-making time by 25%.",
                "Integrated Three.js for 3D data visualizations, enhancing overall user experience and data accuracy by 20%.",
                "Coordinated cross-functional efforts to execute project initiatives, independently designing and deploying 3 new systems; achieved a significant increase in team efficiency, with the tools now utilized by over 15 departments across the organization."
            ]
        },
        {
            'company': 'ToTheNew Pvt. Ltd.', 'title': 'Software Engineer', 'dates': 'Feb 2020 -- Mar 2021',
            'technologies': 'Angular 4+, Node.js, PHP, MongoDB, Express', 'location': 'Noida, India',
            'description': [
                "Engineered front-end solutions, including a COVID-19 dashboard and e-commerce platforms, using Angular 4 and RxJS, which improved client satisfaction for PWC.",
                "Architected the TCH channel studying portal using Angular 4, REST API, and RxJS, enhancing the learning experience for users.",
                "Implemented RxJS for handling asynchronous tasks, reducing loading times by 50% across key application features; this enhancement improved overall customer satisfaction and increased retention rates among users by 15%."
            ]
        },
         {
            'company': 'Smart Joules Pvt. Ltd.', 'title': 'Joule Fellow', 'dates': 'Sept 2018 -- Dec 2019',
            'technologies': 'Angular, D3.js, TypeScript, RxJS', 'location': 'Dehradun, India',
            'description': [
                "Created various applications, such as D3 dashboards, multi-select autocomplete, and D3 charts, within the Smart Joules track system.",
                "Developed an open-source NPM module for multi-select autocomplete, fostering code reusability and promoting best practices, leading to a 40% increase in community contributions.",
                "Applied Angular and RxJS in constructing D3 dashboards, enhancing functionality and responsiveness."
            ]
        }
    ]

    project_data = [
        {
            'title': 'ScanFeast Mobile Web App', 'technologies': 'React, Redux, D3.js, Firebase', 'dates': 'Aug 2024 -- Present',
            'description': [
                "Developed a React and Redux-powered restaurant app for seamless order placement via QR code scanning, leading to a 20% increase in order processing efficiency.",
                "Integrated Firebase for efficient backend operations, optimizing data storage and retrieval, improving data retrieval speed by 30%.",
                "Incorporated charts and graphs using D3.js in the restaurant dashboard, offering insights for efficient order management."
            ]
        },
        {
            'title': 'MedConnect Mobile Web App', 'technologies': 'React, Redux, Node.js, MongoDB, AWS, Typescript', 'dates': 'Sept 2024 -- Present',
            'description': [
                "Engineered a fully functional mobile web application with Node.js for backend REST API services and React for frontend interactions; successfully integrated real-time data updates, now utilized by over 500 active users weekly.",
                "Deployed JWT authentication for secure data retrieval from users, enhancing security protocols by 40%.",
                "Constructed a search interface using Algolia search to enhance user experience, reducing search times by 25%."
            ]
        }
    ]

    # Example: Make sure skills string includes special chars for testing escape
    skills_data = {
        'Skills': "Angular, React, Next.js, Redux, RxJS, PHP, GraphQL, Jest, Node.js, D3.js, Three.js, JavaScript, TypeScript, HTML/CSS, jQuery, Python, Data Structures & Algorithms, System Design, C#, Java, .NET",
        'Tools': "Git, Firebase, Docker, SharePoint, AWS, Cordova, Selenium_automation, Capacitor, Visual Studio"
    }
    # --- End Placeholder Data ---


    # --- TODO: Actual Tailoring Logic ---
    # 1. Parse your base resume data (from PDF/JSON/DB).
    # 2. Construct a prompt for Gemini using base data and job_data['description'].
    #    Example Prompt: "Given the following base resume sections [Experience, Projects, Skills] and this job description [Job Desc Text], rewrite the experience/project bullet points and select the most relevant skills (max 15 skills, max 10 tools) to best match the job. Output the revised sections in a structured format (e.g., JSON with keys 'experience', 'projects', 'skills'). Ensure bullet points start with action verbs and quantify results where possible. Escape LaTeX special characters like #, %, &, _ in the output text."
    # 3. Send prompt to Gemini:
    #    try:
    #        response = gemini_model.generate_content(prompt)
    #        # Process response.text to extract tailored sections (e.g., parse JSON)
    #        # Update experience_data, project_data, skills_data with Gemini's output
    #        logging.info("Gemini tailoring successful.")
    #    except Exception as e:
    #        logging.error(f"Gemini API call failed during tailoring: {e}", exc_info=True)
    #        # Decide how to handle failure: use base data? return None?
    #        return None # Example: fail if Gemini fails
    # --- End TODO ---


    # --- Assemble LaTeX String with Escaped Data ---
    logging.info("Assembling final LaTeX string with escaped content...")
    experience_section = "\n".join([format_experience_entry(exp) for exp in experience_data])
    project_section = "\n".join([format_project_entry(proj) for proj in project_data])
    skills_section = format_skills_section(skills_data) # Escaping happens inside

    final_latex_string = f"""{RESUME_PREAMBLE}
{RESUME_HEADER}
{RESUME_EDUCATION}
{RESUME_EXPERIENCE_START}
{experience_section}
{RESUME_EXPERIENCE_END}
{RESUME_PROJECTS_START}
{project_section}
{RESUME_PROJECTS_END}
{skills_section}
{RESUME_FOOTER}
"""
    logging.info("Final LaTeX string assembled.")
    # logging.debug(f"Final assembled LaTeX:\n{final_latex_string[:1000]}...") # Optional: Log start of final string

    return final_latex_string

# --- Example Usage (for testing tailor.py directly) ---
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
#     logging.info("--- Running tailor.py directly for testing ---")
#     test_job = {
#         '_id': 'test12345',
#         'title': 'Senior Software Engineer (Backend)',
#         'company_name': 'Test Corp & Co.',
#         'description': 'Looking for experience with Python, AWS, Docker, and microservices. Must handle # and _ characters. Bonus for % and &.'
#     }
#     tailored_latex = generate_tailored_resume_text(test_job)
#     if tailored_latex:
#         print("\n--- Generated LaTeX (first 1000 chars) ---")
#         print(tailored_latex[:1000])
#         print("\n...")
#         # Optionally save to a file for inspection
#         # with open("test_tailored_resume.tex", "w") as f:
#         #     f.write(tailored_latex)
#         # logging.info("Test output saved to test_tailored_resume.tex")
#     else:
#         logging.error("Tailoring test failed.")

