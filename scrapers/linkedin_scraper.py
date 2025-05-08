# scrapers/linkedin_scraper.py
import logging
import datetime
import json

# --- LinkedIn Scraper Imports ---
from linkedin_jobs_scraper import LinkedinScraper
# Config is set globally in config.py
from linkedin_jobs_scraper.events import Events, EventData, EventMetrics
from linkedin_jobs_scraper.query import Query, QueryOptions, QueryFilters
from linkedin_jobs_scraper.filters import RelevanceFilters, TimeFilters, TypeFilters, ExperienceLevelFilters, OnSiteOrRemoteFilters

# --- Project Imports ---
import config # Import config but rely on global setup for LI_AT_COOKIE
from database import store_job_data, normalize_url # Import the storage function

# --- Module State ---
linkedin_scraped_jobs_list = [] # Temporary list for JSON backup if needed
processed_in_run = 0

# --- Event Handlers ---
def on_linkedin_data(data: EventData):
    """Callback for LinkedIn scraper, formats data and calls store_job_data."""
    global processed_in_run
    logging.info(f"[LinkedIn] Processing Job ID: {getattr(data, 'job_id', 'N/A')}, Title: {getattr(data, 'title', 'N/A')}")

    # Determine application type
    apply_link = getattr(data, 'apply_link', None)
    linkedin_link = getattr(data, 'link', None)
    application_type = "unknown"
    application_url = None
    is_easy_apply = False

    if apply_link:
        normalized_apply = normalize_url(apply_link)
        normalized_linkedin = normalize_url(linkedin_link)

        # Check if apply link points to LinkedIn's easy apply flow
        if "linkedin.com/jobs/view" in (normalized_apply or "") and "jobs-apply" in (normalized_apply or ""):
            application_type = "easy_apply"
            is_easy_apply = True
            logging.debug(f"  [LinkedIn] Detected Easy Apply via apply_link structure: {apply_link}")
        # Check if apply link is just the job view link (common failure case or actual easy apply)
        elif normalized_apply == normalized_linkedin:
             application_type = "easy_apply" # Assume easy apply if links match
             is_easy_apply = True
             logging.debug(f"  [LinkedIn] apply_link matches job link, assuming Easy Apply: {apply_link}")
        else:
            # If apply_link is different and not the easy apply structure, assume external
            application_type = "external"
            application_url = apply_link
            logging.debug(f"  [LinkedIn] Detected external apply_link: {apply_link}")
    elif linkedin_link and 'linkedin.com/jobs/view' in linkedin_link:
         # If no apply_link but a valid LinkedIn job link, assume Easy Apply
         application_type = "easy_apply"
         is_easy_apply = True
         logging.debug(f"  [LinkedIn] No distinct apply_link found, assuming Easy Apply for: {linkedin_link}")
    else:
         logging.warning(f"  [LinkedIn] Could not determine application type for job: {getattr(data, 'title', 'N/A')}")


    # Prepare data for database insertion
    job_data = {
        "source_platform": "linkedin",
        "source_job_id": getattr(data, 'job_id', None),
        "source_url": linkedin_link,
        "application_type": application_type,
        "application_url": application_url, # Will be None for Easy Apply
        "job_title": getattr(data, 'title', None),
        "company_name": getattr(data, 'company', None),
        "company_linkedin_url": getattr(data, 'company_link', None),
        "company_website": None,
        "location": getattr(data, 'place', None),
        "is_remote": "remote" in getattr(data, 'place', "").lower() if getattr(data, 'place', None) else None,
        "work_model": "Remote" if "remote" in getattr(data, 'place', "").lower() else ("Hybrid" if "hybrid" in getattr(data, 'place', "").lower() else ("Onsite" if getattr(data, 'place', None) else None)),
        "publish_time": getattr(data, 'date', None),
        "publish_time_desc": getattr(data, 'date_text', None),
        "employment_type": getattr(data, 'employment_type', None),
        "seniority_level": getattr(data, 'seniority_level', None),
        "description": getattr(data, 'description', None),
        "description_html": getattr(data, 'description_html', None),
        "job_summary": None,
        "skills": getattr(data, 'skills', None),
        "qualifications": None,
        "core_responsibilities": None,
        "social_connections": None,
        "personal_social_connections": None,
        # "_raw_data": data.__dict__ # Optional: store original object data if needed for debugging
    }

    # Add to temp list for JSON backup
    linkedin_scraped_jobs_list.append(job_data)

    # Attempt to store in MongoDB
    if store_job_data(job_data):
        processed_in_run += 1


def on_linkedin_error(error):
    logging.error(f'[LinkedIn ON_ERROR] {error}')

def on_linkedin_end():
    logging.info('[LinkedIn ON_END] Scraping finished.')
    logging.info(f'--- LinkedIn Jobs Processed/Stored in this run: {processed_in_run} ---')
    # Optional: Save LinkedIn backup JSON
    if linkedin_scraped_jobs_list:
        try:
            with open(config.OUTPUT_FILENAME_LINKEDIN, "w", encoding="utf-8") as f:
                 # Convert datetime objects if they exist before saving JSON
                serializable_list = []
                for job in linkedin_scraped_jobs_list:
                    serializable_job = job.copy()
                    for key, value in serializable_job.items():
                        if isinstance(value, datetime.datetime):
                            serializable_job[key] = value.isoformat()
                    serializable_list.append(serializable_job)
                json.dump(serializable_list, f, ensure_ascii=False, indent=4)
            logging.info(f"--- Saved LinkedIn backup data to {config.OUTPUT_FILENAME_LINKEDIN} ---")
        except Exception as e:
            logging.error(f"--- Error saving LinkedIn backup data to JSON: {e} ---")


def run_linkedin_scraper(limit=None):
    """
    Initializes and runs the LinkedIn job scraper.
    :param limit: Max number of jobs to process for this run. Uses config default if None.
    """
    global processed_in_run, linkedin_scraped_jobs_list
    processed_in_run = 0 # Reset counter for this run
    linkedin_scraped_jobs_list = [] # Reset backup list

    if not config.LINKEDIN_SESSION_COOKIE:
        logging.error("LinkedIn session cookie not configured. Skipping LinkedIn scraping.")
        return

    logging.info("--- Starting LinkedIn Scraper ---")

    # Use limit from args or config file
    job_limit = limit if limit is not None else config.LINKEDIN_JOB_LIMIT_PER_QUERY

    # Initialize scraper
    scraper = LinkedinScraper(
        chrome_executable_path=None,  # Custom Chrome executable path (e.g. /foo/bar/bin/chromedriver)
        chrome_binary_location=None,
        chrome_options=None, # Add options if needed (e.g., proxy)
        headless=True,
        max_workers=1,
        slow_mo=5,
        page_load_timeout=120
    )

    # Add event listeners
    scraper.on(Events.DATA, on_linkedin_data)
    scraper.on(Events.ERROR, on_linkedin_error)
    scraper.on(Events.END, on_linkedin_end)

    # Define search queries - TODO: Make these configurable?
    queries = [
        Query(
            query='Frontend Software Engineer', # Example query
            options=QueryOptions(
                locations=['New York City','California','Seattle'], # Example location
                apply_link=True,
                skip_promoted_jobs=True,
                page_offset=2,
                limit=job_limit, # Use the determined limit
                filters=QueryFilters(
                    relevance=RelevanceFilters.RECENT,
                    time=TimeFilters.MONTH,
                    # Add more filters as needed
                    # on_site_or_remote=[OnSiteOrRemoteFilters.REMOTE]
                )
            )
        ),
        # Add more Query objects for different searches
    ]

    logging.info(f"Starting LinkedIn scraper run for {len(queries)} queries, limit per query: {job_limit}...")
    try:
        scraper.run(queries)
    except Exception as e:
        logging.error(f"An exception occurred during LinkedIn scraper execution: {e}", exc_info=True)
        # Ensure on_end is called even if scraper.run crashes early
        on_linkedin_end()

    logging.info("LinkedIn scraper run process completed or exited.")

