import os
import logging
import google.generativeai as genai
import json # To parse Gemini's JSON output

# Import utilities, including the escape function and template loader
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from utils import escape_latex, decode_html_to_text, load_template # Import utils
    import config # To get API key, model name etc.
except ImportError as e:
     logging.critical(f"Error importing required modules in tailor.py: {e}", exc_info=True)
     raise SystemExit(f"Critical import error in tailor.py: {e}. Ensure 'utils.py' and 'config.py' are accessible.")

logging.info("resume_tailor/tailor.py module loading...")

# --- Gemini Configuration ---
gemini_model = None
gemini_client_status = "Not Configured" # Default status
try:
    logging.info("Configuring Gemini API client...")
    if not hasattr(config, 'GEMINI_API_KEY') or not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found or is empty in configuration.")
    if not hasattr(config, 'GEMINI_MODEL_NAME') or not config.GEMINI_MODEL_NAME:
        raise ValueError("GEMINI_MODEL_NAME not found or is empty in configuration.")

    genai.configure(api_key=config.GEMINI_API_KEY)
    logging.info(f"Attempting to initialize Gemini model: {config.GEMINI_MODEL_NAME}...")
    generation_config = {
        "temperature": 0.5, # Slightly more deterministic for factual tailoring
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    gemini_model = genai.GenerativeModel(model_name=config.GEMINI_MODEL_NAME,
                                      generation_config=generation_config,
                                      safety_settings=safety_settings)
    logging.info(f"Gemini API configured successfully with model: {config.GEMINI_MODEL_NAME} for JSON output.")
    gemini_client_status = "Success"
except ValueError as ve:
    logging.error(f"Configuration error for Gemini API: {ve}")
    gemini_client_status = f"Config Error: {ve}"
except Exception as e:
    logging.error(f"Failed to configure Gemini API: {e}", exc_info=True)
    gemini_client_status = f"Failed: {e}"

logging.info(f"Gemini client configuration status: {gemini_client_status}")


# --- File Paths & Constants ---
ACHIEVEMENTS_FILE_PATH = os.path.join(PROJECT_ROOT, 'info', 'achievements.txt')
BASE_RESUME_JSON_PATH = os.path.join(PROJECT_ROOT, 'base_resume.json') # Path to your base resume JSON

# Define template structure parts (Ensure these match your base template exactly)
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
      \small\textbf{#1} & #2 \\
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
# MODIFIED: Escaped literal % signs with %%
RESUME_HEADER = r"""
%%----------HEADING----------
%% Replace placeholders with actual data from config
\begin{center}
    \textbf{\Huge \scshape %(YOUR_NAME)s} \\ \vspace{1pt}
    \small %(YOUR_PHONE)s $|$
    \href{mailto:%(YOUR_EMAIL)s}{\nolinkurl{%(YOUR_EMAIL)s}} $|$
    \href{%(YOUR_LINKEDIN_URL)s}{\nolinkurl{%(YOUR_LINKEDIN_URL_TEXT)s}} $|$
    \href{%(YOUR_GITHUB_URL)s}{\nolinkurl{%(YOUR_GITHUB_URL_TEXT)s}}
    %(YOUR_LEETCODE_LINE)s
\end{center}
""" % { # Get from config - NO FALLBACK VALUES
    'YOUR_NAME': config.YOUR_NAME if hasattr(config, 'YOUR_NAME') and config.YOUR_NAME else "[YOUR_NAME]",
    'YOUR_PHONE': config.YOUR_PHONE if hasattr(config, 'YOUR_PHONE') and config.YOUR_PHONE else "[YOUR_PHONE]",
    'YOUR_EMAIL': config.YOUR_EMAIL if hasattr(config, 'YOUR_EMAIL') and config.YOUR_EMAIL else "[YOUR_EMAIL]",
    'YOUR_LINKEDIN_URL': config.YOUR_LINKEDIN_URL if hasattr(config, 'YOUR_LINKEDIN_URL') and config.YOUR_LINKEDIN_URL else "https://linkedin.com/in/",
    'YOUR_LINKEDIN_URL_TEXT': config.YOUR_LINKEDIN_URL_TEXT if hasattr(config, 'YOUR_LINKEDIN_URL_TEXT') and config.YOUR_LINKEDIN_URL_TEXT else "linkedin.com/in/",
    'YOUR_GITHUB_URL': config.YOUR_GITHUB_URL if hasattr(config, 'YOUR_GITHUB_URL') and config.YOUR_GITHUB_URL else "https://github.com/",
    'YOUR_GITHUB_URL_TEXT': config.YOUR_GITHUB_URL_TEXT if hasattr(config, 'YOUR_GITHUB_URL_TEXT') and config.YOUR_GITHUB_URL_TEXT else "github.com/",
    'YOUR_LEETCODE_LINE': f"$|$ \\href{{{config.YOUR_LEETCODE_URL}}}{{\\nolinkurl{{{config.YOUR_LEETCODE_URL_TEXT}}}}}" if hasattr(config, 'YOUR_LEETCODE_URL') and config.YOUR_LEETCODE_URL and hasattr(config, 'YOUR_LEETCODE_URL_TEXT') and config.YOUR_LEETCODE_URL_TEXT else ""
}


# RESUME_EDUCATION is now generated dynamically from config or base_resume.json
def get_education_section():
    """Generate education section from config values."""
    university = escape_latex(config.UNIVERSITY if hasattr(config, 'UNIVERSITY') and config.UNIVERSITY else "[Your University]")
    degree = escape_latex(config.DEGREE if hasattr(config, 'DEGREE') and config.DEGREE else "[Degree Program]")
    edu_location = escape_latex(config.EDUCATION_LOCATION if hasattr(config, 'EDUCATION_LOCATION') and config.EDUCATION_LOCATION else "[City, State]")
    edu_dates = escape_latex(config.EDUCATION_DATES if hasattr(config, 'EDUCATION_DATES') and config.EDUCATION_DATES else "[Start Date -- End Date]")

    return f"""%-----------EDUCATION-----------
\\section{{Education}}
  \\resumeSubHeadingListStart
    \\resumeSubheading
      {{{university}}}{{{edu_location}}}
      {{{degree}}}{{{edu_dates}}}
  \\resumeSubHeadingListEnd
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

# --- Helper: Load Achievements ---
def load_achievements():
    """Loads text from the achievements file."""
    if not os.path.exists(ACHIEVEMENTS_FILE_PATH):
        logging.warning(f"Achievements file not found at: {ACHIEVEMENTS_FILE_PATH}. Proceeding without it.")
        return ""
    try:
        with open(ACHIEVEMENTS_FILE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read achievements file {ACHIEVEMENTS_FILE_PATH}: {e}", exc_info=True)
        return ""

# --- Helper: Load Base Resume Data ---
def load_base_resume_data(filepath=BASE_RESUME_JSON_PATH):
    """Loads base resume data from a JSON file."""
    logging.info(f"Loading base resume data from: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info("Base resume data loaded successfully.")
        # Validate basic structure
        if not isinstance(data.get("experience"), list) or \
           not isinstance(data.get("projects"), list) or \
           not isinstance(data.get("skills"), dict):
            logging.error(f"Base resume JSON ({filepath}) has incorrect top-level structure.")
            return [], [], {} # Return empty structures on error
        return data.get("experience", []), data.get("projects", []), data.get("skills", {})
    except FileNotFoundError:
        logging.error(f"Base resume JSON file not found at {filepath}. Using empty data.")
        return [], [], {}
    except json.JSONDecodeError:
        logging.error(f"Error decoding base resume JSON from {filepath}. Using empty data.")
        return [], [], {}
    except Exception as e:
        logging.error(f"Error loading base resume data: {e}", exc_info=True)
        return [], [], {}


# --- Helper: Format LaTeX Sections ---
def format_experience_section_from_json(experience_list):
    """Formats experience section from a list of dicts (parsed from JSON)."""
    latex_string = RESUME_EXPERIENCE_START
    if not isinstance(experience_list, list):
         logging.error("Invalid experience data received (not a list). Skipping section.")
         return latex_string + "\n% Experience data missing or invalid\n" + RESUME_EXPERIENCE_END

    for exp in experience_list:
        if not isinstance(exp, dict):
            logging.warning(f"Skipping invalid experience entry (not a dict): {exp}")
            continue
        company = exp.get('company', '')
        title = exp.get('title', '')
        dates = exp.get('dates', '')
        tech = exp.get('technologies', '')
        location = exp.get('location', '')
        description_points = exp.get('description', [])

        escaped_company = escape_latex(company)
        escaped_title = escape_latex(title)
        escaped_dates = escape_latex(dates)
        escaped_tech = escape_latex(tech)
        escaped_location = escape_latex(location)

        subheading = f"\\resumeSubheading{{\\textbf{{{escaped_company}}} $|$ \\emph{{{escaped_title}}}}}{{{escaped_dates}}}{{{escaped_tech}}}{{{escaped_location}}}"
        latex_string += f"\n{subheading}\n"

        if description_points and isinstance(description_points, list):
            latex_string += "  \\resumeItemListStart\n"
            for point in description_points:
                if isinstance(point, str) and point.strip():
                    escaped_point = escape_latex(point)
                    latex_string += f"    \\resumeItem{{{escaped_point}}}\n"
            latex_string += "  \\resumeItemListEnd\n"
    latex_string += RESUME_EXPERIENCE_END
    return latex_string

def format_projects_section_from_json(project_list):
    """Formats project section from a list of dicts (parsed from JSON)."""
    latex_string = RESUME_PROJECTS_START
    if not isinstance(project_list, list):
         logging.error("Invalid project data received (not a list). Skipping section.")
         return latex_string + "\n% Project data missing or invalid\n" + RESUME_PROJECTS_END

    for proj in project_list:
        if not isinstance(proj, dict):
            logging.warning(f"Skipping invalid project entry (not a dict): {proj}")
            continue
        title = proj.get('title', '')
        tech = proj.get('technologies', '')
        dates = proj.get('dates', '')
        description_points = proj.get('description', [])

        escaped_title = escape_latex(title)
        escaped_tech = escape_latex(tech)
        escaped_dates = escape_latex(dates)

        heading = f"\\resumeProjectHeading{{\\textbf{{{escaped_title}}} $|$ \\emph{{{escaped_tech}}}}}{{{escaped_dates}}}"
        latex_string += f"\n{heading}\n"

        if description_points and isinstance(description_points, list):
            latex_string += "  \\resumeItemListStart\n"
            for point in description_points:
                 if isinstance(point, str) and point.strip():
                    escaped_point = escape_latex(point)
                    latex_string += f"    \\resumeItem{{{escaped_point}}}\n"
            latex_string += "  \\resumeItemListEnd\n"
    latex_string += RESUME_PROJECTS_END
    return latex_string

def format_skills_section_from_json(skills_dict):
    """Formats skills section from a dict (parsed from JSON)."""
    if not isinstance(skills_dict, dict):
        logging.error("Invalid skills data received (not a dict). Skipping section.")
        return RESUME_SKILLS_START + "\n% Skills data missing or invalid\n" + RESUME_SKILLS_END

    skills_list = skills_dict.get('skills_list', [])
    tools_list = skills_dict.get('tools_list', [])

    skills_list = [s for s in skills_list if isinstance(s, str) and s.strip()] if isinstance(skills_list, list) else []
    tools_list = [t for t in tools_list if isinstance(t, str) and t.strip()] if isinstance(tools_list, list) else []

    escaped_skills_str = escape_latex(", ".join(skills_list)) + ("." if skills_list else "")
    escaped_tools_str = escape_latex(", ".join(tools_list)) + ("." if tools_list else "")
    
    items = []
    if escaped_skills_str and escaped_skills_str != ".": 
        items.append(f"    \\item \\small \\textbf{{Skills:}} {escaped_skills_str}")
    if escaped_tools_str and escaped_tools_str != ".":
        items.append(f"    \\item \\small \\textbf{{Tools:}} {escaped_tools_str}")

    if not items: 
        return f"{RESUME_SKILLS_START}\n    % No skills or tools listed.\n{RESUME_SKILLS_END}"

    return f"{RESUME_SKILLS_START}\n" + "\n".join(items) + f"\n{RESUME_SKILLS_END}"


# --- Combined Tailoring Function ---
def generate_tailored_latex_docs(job_data):
    """
    Generates tailored LaTeX strings for BOTH resume and cover letter using Gemini.
    Returns a dictionary: {'resume': str|None, 'cover_letter': str|None}
    """
    job_title_display = job_data.get('job_title', 'N/A')
    company_name_display = job_data.get('company_name', 'N/A')
    logging.info(f"Starting combined tailoring for job: '{job_title_display}' at '{company_name_display}'")

    final_resume_latex = None
    final_cl_latex = None

    if gemini_client_status != "Success" or gemini_model is None:
        logging.error("Gemini client not configured. Cannot perform tailoring.")
        return {'resume': None, 'cover_letter': None}

    # 1. Load Base Resume Data and Achievements
    logging.info("Loading base resume data and achievements...")
    base_experience_data, base_project_data, base_skills_data_dict = load_base_resume_data()
    achievements_text = load_achievements()

    if not base_experience_data and not base_project_data and not base_skills_data_dict:
        logging.error("Base resume data is empty. Cannot effectively tailor. Check base_resume.json.")
        return {'resume': None, 'cover_letter': None}


    # 2. Prepare Job Data for Prompt
    job_description_html = job_data.get('description', '')
    job_description_text = decode_html_to_text(job_description_html) if job_description_html else ""
    if not job_description_text:
        logging.warning("Job description is empty. Tailoring quality may be reduced.")

    qualifications_data = job_data.get('qualifications', {}) # Default to empty dict
    must_have_qualifications = qualifications_data.get('mustHave', []) if isinstance(qualifications_data, dict) and isinstance(qualifications_data.get('mustHave'), list) else []
    preferred_qualifications = qualifications_data.get('preferredHave', []) if isinstance(qualifications_data, dict) and isinstance(qualifications_data.get('preferredHave'), list) else []
    
    job_skills_list = job_data.get('skills', []) if isinstance(job_data.get('skills'), list) else []
    core_responsibilities = job_data.get('core_responsibilities', []) if isinstance(job_data.get('core_responsibilities'), list) else []

    base_skills_list_profile = [s.strip() for s in base_skills_data_dict.get('Skills', '').split(',') if s.strip()]
    base_tools_list_profile = [t.strip() for t in base_skills_data_dict.get('Tools', '').split(',') if t.strip()]
    target_skills_count_low = len(base_skills_list_profile)
    target_skills_count_high = len(base_skills_list_profile) + 5 # Allow adding up to 5 new skills
    target_tools_count_low = len(base_tools_list_profile)
    target_tools_count_high = len(base_tools_list_profile) + 3 # Allow adding up to 3 new tools


    # 3. Construct Resume Prompt for Gemini
    logging.info("Constructing resume prompt for Gemini...")
    resume_prompt = f"""
    You are an expert resume writer and ATS optimization specialist. Your task is to tailor this candidate's resume to maximize relevance for this specific job posting while maintaining 100% truthfulness to their actual experience.

    I. CANDIDATE PROFILE:
       1. Base Resume Experience (List of Dictionaries): {json.dumps(base_experience_data, indent=2)}
       2. Base Resume Projects (List of Dictionaries): {json.dumps(base_project_data, indent=2)}
       3. Candidate's Core Skills List: {json.dumps(base_skills_list_profile)}
       4. Candidate's Core Tools List: {json.dumps(base_tools_list_profile)}
       5. Candidate's Key Achievements/Awards (Text): "{achievements_text}"

    II. TARGET JOB OPPORTUNITY:
       1. Job Title: "{job_data.get('job_title', 'N/A')}"
       2. Company: "{job_data.get('company_name', 'N/A')}"
       3. Full Job Description Text: "{job_description_text}"
       4. Core Responsibilities (List): {json.dumps(core_responsibilities)}
       5. Must-Have Qualifications (List): {json.dumps(must_have_qualifications)}
       6. Preferred Qualifications (List): {json.dumps(preferred_qualifications)}
       7. Key Skills Listed in Job Posting (List): {json.dumps(job_skills_list)}

    CRITICAL TAILORING REQUIREMENTS:
    Your primary goal is to STRATEGICALLY REWRITE every bullet point to directly address this specific job posting while staying 100% truthful.
    This is NOT a generic resume - this MUST be laser-focused on THIS job at THIS company.

    1.  TAILORED EXPERIENCE SECTION:
        -   Iterate through each entry in "Base Resume Experience".
        -   Keep the original "company", "title", "dates", and "location" fields unchanged.
        -   For "technologies": Keep the original list, but you MAY reorder it to bring the most job-relevant technologies to the front. You MAY also add 3-4 highly relevant technologies IF they are explicitly mentioned in the "JOB OPPORTUNITY" (Job Description, Skills, Qualifications, Responsibilities) AND are a natural fit for the described experience.
        -   For "description" (bullet points):
            * **CRITICAL: You MUST COMPLETELY REWRITE EACH bullet point from scratch.** Do not copy or lightly edit - REWRITE to be job-specific.
            * STEP 1: Identify which "Core Responsibilities", "Must-Have Qualifications", or "Key Skills" from the job posting each bullet point should address.
            * STEP 2: Rewrite the bullet point to EXPLICITLY demonstrate how this experience addresses that specific requirement.
            * STEP 3: Mirror the language and terminology used in the job description. If the JD says "develop scalable systems", use "developed scalable systems" (not "built software").
            * Use strong, specific action verbs that match the job description's tone.
            * ALWAYS quantify results with specific metrics, percentages, or numbers from the original bullet points.
            * Include the exact technical terms, frameworks, and tools mentioned in the job posting where truthfully applicable.
            * **KEYWORD OPTIMIZATION:** Each bullet should contain 2-3 keywords from the job posting. Use the EXACT phrasing from the JD.
            * **Keyword Frequency Constraint:** Avoid using the same keyword more than twice across ALL bullets to show breadth of experience.
            * Ensure the total number of bullet points for each experience entry remains the same as the original.

    2.  TAILORED PROJECTS SECTION:
        -   Iterate through each entry in "Base Resume Projects".
        -   Keep the original "title" and "dates" fields unchanged.
        -   For "technologies": Similar to experience, keep original but reorder or add 3-4 highly relevant technologies from the "JOB OPPORTUNITY" if appropriate.
        -   For "description" (bullet points):
            * **CRITICAL: You MUST COMPLETELY REWRITE EACH bullet point to match the job requirements.**
            * STEP 1: Identify which requirements from the job posting this project demonstrates.
            * STEP 2: Rewrite to emphasize how this project shows relevant skills for THIS specific job.
            * STEP 3: Use the EXACT terminology from the job description (if JD mentions "microservices architecture", use that exact phrase).
            * Highlight technologies and methodologies mentioned in the job posting.
            * ALWAYS include quantifiable metrics (users, performance improvements, scale, etc.).
            * **KEYWORD OPTIMIZATION:** Each bullet should demonstrate 2-3 specific requirements from the job posting.
            * **Keyword Frequency Constraint:** Apply the same keyword frequency constraint (max twice across all bullets).
            * Ensure the total number of bullet points for each project entry remains the same as the original.

    3.  TAILORED SKILLS SECTION:
        -   Create a "skills_list": Combine "Candidate's Core Skills List" with "Key Skills Listed in Job Posting", and any other critical skills clearly implied by "Core Responsibilities" or "Must-Have Qualifications". Remove duplicates. Prioritize and order this list by high relevance to the "JOB OPPORTUNITY". Aim for a concise yet comprehensive list, approximately {target_skills_count_low}-{target_skills_count_high} skills.
        -   Create a "tools_list": Combine "Candidate's Core Tools List" with any specific tools mentioned in the "JOB OPPORTUNITY". Prioritize and order by relevance. Aim for approximately {target_tools_count_low}-{target_tools_count_high} tools.

    OUTPUT FORMAT:
    Return ONLY a single, valid JSON object. The top-level keys MUST be exactly "tailored_experience", "tailored_projects", and "tailored_skills".
    {{
      "tailored_experience": [
        {{
          "company": "Original Company Name",
          "title": "Original Job Title",
          "dates": "Original Dates",
          "technologies": "Original or slightly adjusted tech list",
          "location": "Original Location",
          "description": ["FULLY REWRITTEN bullet point 1 for relevance...", "FULLY REWRITTEN bullet point 2..."]
        }},
        // ... (repeat for all original experience entries)
      ],
      "tailored_projects": [
        {{
          "title": "Original Project Title",
          "technologies": "Original or slightly adjusted tech list",
          "dates": "Original Dates",
          "description": ["FULLY REWRITTEN bullet point 1 for relevance...", "FULLY REWRITTEN bullet point 2..."]
        }},
         // ... (repeat for all original project entries)
      ],
      "tailored_skills": {{
        "skills_list": ["Highly relevant skill 1", "Highly relevant skill 2", ...],
        "tools_list": ["Relevant tool 1", "Relevant tool 2", ...]
      }}
    }}

    CRITICAL INSTRUCTIONS:
    - Output plain text in JSON values. NO LaTeX special characters (like #, %, &, _, \\, {{, }}) unless part of a standard technical term (e.g., C#). The script will handle LaTeX escaping later.
    - Ensure rewritten descriptions are impactful and directly support the application for THIS job.
    - The number of experience and project entries in the output MUST match the input.
    """

    # 4. Call Gemini for Resume
    logging.info("Sending resume tailoring request to Gemini API...")
    tailored_resume_json_data = None
    try:
        response = gemini_model.generate_content(resume_prompt)
        logging.debug(f"Raw Gemini Resume Response Text (first 500 chars): {response.text[:500]}...")
        
        raw_text = response.text
        if raw_text.strip().startswith("```json"):
             raw_text = raw_text.strip()[7:-3].strip() 
        elif raw_text.strip().startswith("```"):
             raw_text = raw_text.strip()[3:-3].strip() 
        
        tailored_resume_json_data = json.loads(raw_text)
        logging.info("Successfully received and parsed tailored resume data from Gemini.")

        if not all(k in tailored_resume_json_data for k in ['tailored_experience', 'tailored_projects', 'tailored_skills']):
             raise ValueError("Gemini response for resume missing required top-level keys.")
        if not isinstance(tailored_resume_json_data.get('tailored_experience'), list) or \
           not isinstance(tailored_resume_json_data.get('tailored_projects'), list) or \
           not isinstance(tailored_resume_json_data.get('tailored_skills'), dict) or \
           not all(k in tailored_resume_json_data['tailored_skills'] for k in ['skills_list', 'tools_list']):
            raise ValueError("Gemini response for resume has invalid structure for sections or skills/tools lists.")
        logging.info("Gemini resume response structure validated.")

    except json.JSONDecodeError as json_e:
        logging.error(f"Failed to parse JSON response from Gemini for resume: {json_e}", exc_info=True)
        logging.error(f"Gemini Raw Response (Resume): {response.text if 'response' in locals() else 'N/A'}")
    except ValueError as val_e: 
         logging.error(f"Invalid JSON structure received from Gemini for resume: {val_e}")
         logging.error(f"Gemini Raw Response (Resume): {response.text if 'response' in locals() else 'N/A'}")
    except Exception as e: 
        logging.error(f"Gemini API call or processing failed during resume tailoring: {e}", exc_info=True)
        if 'response' in locals() and hasattr(response, 'candidates') and response.candidates:
            try: logging.error(f"Gemini Finish Reason (Resume): {response.candidates[0].finish_reason}")
            except Exception: pass
        tailored_resume_json_data = None 

    # 5. Assemble Final Resume LaTeX String (if tailoring succeeded)
    if tailored_resume_json_data:
        logging.info("Assembling final resume LaTeX string...")
        try:
            experience_section = format_experience_section_from_json(tailored_resume_json_data.get('tailored_experience', []))
            project_section = format_projects_section_from_json(tailored_resume_json_data.get('tailored_projects', []))
            skills_section = format_skills_section_from_json(tailored_resume_json_data.get('tailored_skills', {}))
            
            education_section = get_education_section()
            final_resume_latex = f"{RESUME_PREAMBLE}\n{RESUME_HEADER}\n{education_section}\n{experience_section}\n{project_section}\n{skills_section}\n{RESUME_FOOTER}"
            logging.info("Final tailored resume LaTeX string assembled.")
        except Exception as assembly_err:
            logging.error(f"Error assembling final resume LaTeX string: {assembly_err}", exc_info=True)
            final_resume_latex = None 
    else:
        logging.error("Cannot assemble resume LaTeX because tailored data generation/parsing failed.")
        final_resume_latex = None

    # 6. Generate Cover Letter Text (using Gemini again)
    logging.info("Proceeding to cover letter generation...")
    cl_template_content = None
    final_cl_latex = None
    try:
        cl_template_content = load_template("cover_letter_template.tex") # Use simple filename
        if not cl_template_content:
            raise FileNotFoundError("Cover letter template loaded as empty or None.")
    except Exception as e:
        logging.error(f"Failed to load cover letter template: {e}", exc_info=True)
        cl_template_content = None 

    if cl_template_content:
        company_name = job_data.get('company_name', '[Company Name]')
        job_title_cl = job_data.get('job_title', '[Job Title]') 
        hiring_manager = job_data.get('hiring_manager', 'Hiring Team')
        source_platform = job_data.get('source_platform', 'your website') 
        company_address_cl = job_data.get('company_address', job_data.get('address', '[Company Address]'))
        company_location_cl = job_data.get('company_location', job_data.get('location', '[Company Location]'))
        hiring_manager_title_cl = job_data.get('hiring_manager_title', '')


        salutation = "Dear Hiring Team"
        if hiring_manager and hiring_manager != 'Hiring Team':
            try: manager_last_name = hiring_manager.split(' ')[-1]; salutation = f"Dear Mr./Ms./Mx. {manager_last_name}"
            except IndexError: salutation = f"Dear {hiring_manager}"

        resume_context_for_cl = ""
        if tailored_resume_json_data: 
            exp_summary_parts = []
            for exp_item in tailored_resume_json_data.get('tailored_experience', [])[:2]: 
                if exp_item.get('description'):
                    desc_snippet = ' '.join(exp_item.get('description', [])[:1]) # First bullet point
                    exp_summary_parts.append(f"- At {exp_item.get('company', '')} as {exp_item.get('title', '')}: {desc_snippet[:100]}...") 
            exp_summary = "\n".join(exp_summary_parts)
            skills_summary = ", ".join(tailored_resume_json_data.get('tailored_skills', {}).get('skills_list', [])[:5])
            resume_context_for_cl = f"Key points from tailored resume:\nExperience Highlights:\n{exp_summary}\nTop Skills: {skills_summary}"
        else:
            resume_context_for_cl = "[Resume information not available for tailoring CL]"

        cl_prompt = f"""
        You are an expert cover letter writer specializing in crafting compelling, job-specific narratives that demonstrate perfect candidate-role alignment. Your task is to generate 3 body paragraphs for a professional cover letter that is HIGHLY TAILORED to this specific job posting.

        I. CANDIDATE INFORMATION:
           1. Candidate's Key Achievements/Awards (Text): "{achievements_text}"
           2. Snippets from Candidate's Tailored Resume (for context): "{resume_context_for_cl}"

        II. JOB OPPORTUNITY DETAILS:
           1. Job Title: "{job_title_cl}"
           2. Company Name: "{company_name}"
           3. Full Job Description Text: "{job_description_text}"
           4. Core Responsibilities: {json.dumps(core_responsibilities)}
           5. Must-Have Qualifications: {json.dumps(must_have_qualifications)}
           6. Preferred Qualifications: {json.dumps(preferred_qualifications)}
           7. Key Skills Listed in Job Posting: {json.dumps(job_skills_list)}
           8. Job seen on: "{source_platform}"

        CRITICAL COVER LETTER REQUIREMENTS:
        This is NOT a generic cover letter template. Every sentence must demonstrate understanding of THIS specific role at THIS company.
        Your goal is to create a compelling narrative showing why this candidate is the perfect fit for THIS position.

        Paragraph 1 (Strong Opening - Immediate Relevance):
            - STEP 1: Open with the specific position title "{job_title_cl}" at "{company_name}", mentioning "{source_platform}".
            - STEP 2: Identify the TOP 2 "Must-Have Qualifications" or "Core Responsibilities" from the job posting.
            - STEP 3: Craft 2-3 sentences that IMMEDIATELY demonstrate you meet these top requirements using specific examples from the resume context.
            - **KEYWORD INTEGRATION:** Use the EXACT terminology from the job posting (if JD says "scalable backend systems", say "scalable backend systems").
            - Express genuine enthusiasm that connects your background to their specific needs.
            - Avoid generic phrases like "I am writing to apply" - be direct and value-focused.

        Paragraph 2 (Evidence & Value Proposition - The Core Pitch):
            - This is the MOST CRITICAL paragraph - it must prove you can deliver results for THIS role.
            - STEP 1: Select 2-3 specific achievements from "Candidate's Key Achievements/Awards" or "Snippets from Candidate's Tailored Resume".
            - STEP 2: For EACH achievement, explicitly map it to a specific requirement from "Core Responsibilities", "Must-Have Qualifications", or "Preferred Qualifications".
            - STEP 3: Structure each point as: [Your specific experience] → [How it directly addresses their need] → [Quantified impact if available]
            - **REQUIREMENT MAPPING:** Make explicit connections. Example: "Your requirement for [X] aligns perfectly with my experience doing [Y], where I achieved [Z]."
            - **KEYWORD DENSITY:** Each sentence should contain 1-2 keywords from the job posting. Use their exact phrasing.
            - Focus on OUTCOMES and VALUE you delivered, not just responsibilities.
            - Paint a picture of how you'll solve THEIR specific challenges.

        Paragraph 3 (Company Alignment & Strong Close):
            - STEP 1: Reference something specific about "{company_name}" - their mission, values, recent projects, industry position, or technology stack mentioned in the JD.
            - STEP 2: Explain why YOU specifically are drawn to THIS company and THIS role (connect to your career goals or values from achievements).
            - STEP 3: Reiterate fit for the "{job_title_cl}" position by referencing one final key requirement.
            - Close with confidence and forward momentum - express eagerness to discuss how you'll contribute to their specific goals.
            - Avoid generic statements like "I look forward to hearing from you" - be specific about contributing to their team/projects.

        OUTPUT FORMAT:
        Return ONLY a valid JSON object with keys "paragraph1", "paragraph2", and "paragraph3".
        Output ONLY plain text for the paragraphs. Do NOT include any LaTeX special characters (like #, %, &, _, \\, {{, }}).
        {{
          "paragraph1": "Job-specific opening paragraph text with immediate relevance and keyword integration...",
          "paragraph2": "Evidence-based qualification match paragraph with explicit requirement mapping and quantified achievements...",
          "paragraph3": "Company-specific alignment paragraph with strong, confident closing..."
        }}

        CRITICAL INSTRUCTIONS:
        - Every sentence must be tailored to THIS job posting - NO generic template language.
        - Use the EXACT terminology and phrasing from the job description.
        - Make explicit connections between candidate experience and job requirements.
        - Focus on value and outcomes, not just listing skills.
        - Be specific, confident, and forward-looking.
        """
        cl_paragraph1_text = f"I am writing to express my enthusiastic interest in the {job_title_cl} position at {company_name}, as advertised on {source_platform}. My background in [relevant field/skill] and proven ability to [key achievement verb + result] align well with your requirements, and I am confident I can make significant contributions to your team."
        cl_paragraph2_text = "In my previous roles, I have consistently [verb relevant to JD, e.g., 'delivered impactful solutions by leveraging skills such as X and Y']. For example, [specific achievement from resume/achievements.txt that matches a core responsibility or qualification]. This experience has prepared me to effectively tackle the challenges outlined in your job description, particularly [mention a specific responsibility/qualification from JD]."
        cl_paragraph3_text = f"I am particularly drawn to {company_name}'s commitment to [mention a company value/project if known, otherwise 'innovation and excellence in its field']. The opportunity to contribute to [mention a specific aspect of the role or company] is very appealing. I am eager to discuss how my skills and experiences can benefit your team. Thank you for your time and consideration."

        logging.info("Attempting Gemini API call for cover letter body...")
        try:
            response = gemini_model.generate_content(cl_prompt)
            logging.debug(f"Raw Gemini CL Response (first 500 chars): {response.text[:500]}...")
            
            cleaned_cl_response_text = response.text.strip().removeprefix('```json').removesuffix('```').strip()
            parsed_cl_json = json.loads(cleaned_cl_response_text)

            cl_paragraph1_text = parsed_cl_json.get("paragraph1", cl_paragraph1_text)
            cl_paragraph2_text = parsed_cl_json.get("paragraph2", cl_paragraph2_text)
            cl_paragraph3_text = parsed_cl_json.get("paragraph3", cl_paragraph3_text)
            logging.info("Successfully generated and parsed cover letter body from Gemini.")

        except json.JSONDecodeError as json_e:
            logging.error(f"Failed to parse JSON response from Gemini for CL: {json_e}", exc_info=True)
            logging.error(f"Gemini Raw Response (CL): {response.text if 'response' in locals() else 'N/A'}")
            logging.warning("Using placeholder text for cover letter body due to JSON parsing error.")
        except Exception as e:
            logging.error(f"Gemini API call or processing for cover letter failed: {e}", exc_info=True)
            if 'response' in locals() and hasattr(response, 'candidates') and response.candidates:
                try:
                    logging.error(f"Gemini CL Finish Reason: {response.candidates[0].finish_reason}")
                except Exception: pass
            logging.warning("Using placeholder text for cover letter body due to Gemini API error.")
        
        cl_replacements = {
             "[YOUR_NAME]": escape_latex(config.YOUR_NAME if (hasattr(config, 'YOUR_NAME') and config.YOUR_NAME) else "[YOUR_NAME]"),
             "[YOUR_PHONE]": escape_latex(config.YOUR_PHONE if (hasattr(config, 'YOUR_PHONE') and config.YOUR_PHONE) else "[YOUR_PHONE]"),
             "[YOUR_EMAIL]": escape_latex(config.YOUR_EMAIL if (hasattr(config, 'YOUR_EMAIL') and config.YOUR_EMAIL) else "[YOUR_EMAIL]"),
             "[YOUR_LINKEDIN_URL]": escape_latex(config.YOUR_LINKEDIN_URL if (hasattr(config, 'YOUR_LINKEDIN_URL') and config.YOUR_LINKEDIN_URL) else "https://linkedin.com/in/"),
             "[YOUR_LINKEDIN_URL_TEXT]": escape_latex(config.YOUR_LINKEDIN_URL_TEXT if (hasattr(config, 'YOUR_LINKEDIN_URL_TEXT') and config.YOUR_LINKEDIN_URL_TEXT) else "linkedin.com/in/"),
             "[YOUR_GITHUB_URL]": escape_latex(config.YOUR_GITHUB_URL if (hasattr(config, 'YOUR_GITHUB_URL') and config.YOUR_GITHUB_URL) else "https://github.com/"),
             "[YOUR_GITHUB_URL_TEXT]": escape_latex(config.YOUR_GITHUB_URL_TEXT if (hasattr(config, 'YOUR_GITHUB_URL_TEXT') and config.YOUR_GITHUB_URL_TEXT) else "github.com/"),
             "[YOUR_NAME_SIGNATURE]": escape_latex(config.YOUR_NAME if (hasattr(config, 'YOUR_NAME') and config.YOUR_NAME) else "[YOUR_NAME]"),
             # Date is handled by \today in template
             "[HIRING_MANAGER_NAME]": escape_latex(hiring_manager),
             "[HIRING_MANAGER_TITLE]": escape_latex(hiring_manager_title_cl), # Use specific var
             "[COMPANY_NAME_RECIPIENT]": escape_latex(company_name),
             "[COMPANY_ADDRESS]": escape_latex(company_address_cl), # Use specific var
             "[COMPANY_LOCATION]": escape_latex(company_location_cl), # Use specific var
             "[SALUTATION_RECIPIENT]": escape_latex(salutation),
             # Static placeholders for body paragraphs
             "[BODY_PARAGRAPH_1]": escape_latex(cl_paragraph1_text),
             "[BODY_PARAGRAPH_2]": escape_latex(cl_paragraph2_text),
             "[BODY_PARAGRAPH_3]": escape_latex(cl_paragraph3_text),
             # Also replace dynamic parts in the closing paragraph
             "[COMPANY_NAME_CLOSING]": escape_latex(company_name)
         }

        final_cl_latex = cl_template_content # Start with loaded template content
        for placeholder, value in cl_replacements.items():
            if placeholder in final_cl_latex:
                 final_cl_latex = final_cl_latex.replace(placeholder, value)
            # else: # Reduced logging verbosity for missing placeholders unless critical
                 # known_static_placeholders = ["[BODY_PARAGRAPH_1]", "[BODY_PARAGRAPH_2]", "[BODY_PARAGRAPH_3]"]
                 # if placeholder not in known_static_placeholders and "[" in placeholder:
                      # logging.warning(f"Cover letter template placeholder not found: {placeholder[:50]}...")

        logging.info("Cover letter LaTeX string assembled.")
    else:
        logging.error("Cover letter template not loaded, cannot generate cover letter LaTeX.")
        final_cl_latex = None


    # 6. Return Dictionary
    logging.info("Exiting generate_tailored_latex_docs function.")
    return {'resume': final_resume_latex, 'cover_letter': final_cl_latex}

# --- Example Usage (for testing tailor.py directly) ---
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
#     logging.info("--- Running tailor.py directly for testing ---")
#     test_job = {
#         '_id': 'test12345',
#         'job_title': 'Senior Software Engineer (Backend)', # Changed to job_title
#         'company_name': 'Test Corp & Co.',
#         'description': 'Looking for experience with Python, AWS, Docker, and microservices. Must handle # and _ characters. Bonus for % and &. Also need Kubernetes.',
#         'qualifications': {'mustHave': ['Python', 'AWS'], 'preferredHave': ['Kubernetes']},
#         'skills': ['Python', 'AWS', 'Docker', 'Microservices', 'SQL'],
#         'core_responsibilities': ['Develop backend services', 'Deploy to cloud']
#     }
#     tailored_docs = generate_tailored_latex_docs(test_job)
#     if tailored_docs:
#         print("\n--- Generated Resume LaTeX (first 1000 chars) ---")
#         print(tailored_docs.get('resume', 'FAILED TO GENERATE RESUME')[:1000])
#         print("\n--- Generated Cover Letter LaTeX (first 1000 chars) ---")
#         print(tailored_docs.get('cover_letter', 'FAILED TO GENERATE CL')[:1000])
#         # Optionally save to files for inspection
#         # if tailored_docs.get('resume'):
#         #     with open("test_tailored_resume.tex", "w", encoding='utf-8') as f: f.write(tailored_docs['resume'])
#         # if tailored_docs.get('cover_letter'):
#         #     with open("test_tailored_cl.tex", "w", encoding='utf-8') as f: f.write(tailored_docs['cover_letter'])
#     else:
#         logging.error("Tailoring test failed.")
