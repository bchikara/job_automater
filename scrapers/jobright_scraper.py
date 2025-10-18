# scrapers/jobright_scraper.py
import logging
import requests
import json
import datetime
import time # Import time for delay

# --- Project Imports ---
import config
# Import the storage function and potentially other db utils if needed later
from database import store_job_data

# --- Module State ---
jobright_scraped_jobs_list = [] # Temporary list for JSON backup if needed

def run_jobright_scraper(max_position=None):
    """
    Fetches data from JobRight API with pagination, formats, and calls store_job_data.
    :param max_position: The highest position number to scrape up to. Uses config default if None.
    """
    global jobright_scraped_jobs_list
    jobright_scraped_jobs_list = [] # Reset backup list

    if not config.JOBRIGHT_COOKIE_STRING:
        logging.error("JobRight cookie string not configured. Skipping JobRight scraping.")
        return

    logging.info("--- Starting JobRight API Scraper ---")

    headers = config.JOBRIGHT_HEADERS.copy()
    # Add cookie string from config to headers
    headers['cookie'] = config.JOBRIGHT_COOKIE_STRING

    # Determine pagination limits
    start_position = 0
    increment = config.JOBRIGHT_POSITION_INCREMENT
    end_position = max_position if max_position is not None else config.JOBRIGHT_MAX_POSITION

    total_processed_count = 0
    total_inserted_count = 0

    # Loop through positions (pagination)
    for position in range(start_position, end_position + 1, increment):
        processed_in_page = 0
        inserted_in_page = 0
        page_url = f"{config.JOBRIGHT_API_BASE_URL}?refresh=false&sortCondition=0&position={position}"
        logging.info(f"Fetching JobRight data for position {position} from: {page_url}")

        try:
            response = requests.get(page_url, headers=headers, timeout=30)
            # Check specifically for 500 errors and log before raising
            if response.status_code == 500:
                logging.error(f"HTTP Error 500 (Internal Server Error) fetching JobRight data for position {position}. Skipping this position.")
                # Optionally log response body if needed for debugging 500s
                # logging.debug(f"Response body for 500 error: {response.text[:500]}")
                time.sleep(config.JOBRIGHT_REQUEST_DELAY_SECONDS) # Still apply delay even on error
                continue # Go to the next position

            response.raise_for_status() # Raise an exception for other bad status codes (4xx)
            data = response.json()

            if data.get("result") and data["result"].get("jobList"):
                job_list = data["result"]["jobList"]
                logging.info(f"  Received {len(job_list)} jobs from JobRight API for position {position}.")

                if not job_list:
                    logging.info(f"  No more jobs found at position {position}. Stopping JobRight pagination.")
                    break # Stop if an empty list is returned

                for item_index, item in enumerate(job_list):
                    processed_in_page += 1
                    job_result = item.get("jobResult")
                    if not job_result:
                        logging.warning(f"  Skipping item {item_index+1}, missing 'jobResult'.")
                        continue

                    # --- Refined Data Extraction with Debugging ---
                    job_id = job_result.get("jobId")
                    job_title = job_result.get("jobTitle")

                    # Safely get company name
                    company_result = item.get("companyResult") or {} # Ensure it's a dict, even if None/missing
                    company_name = company_result.get("companyName")

                    logging.debug(f"  Processing JobRight Job ID: {job_id}, Extracted Title: '{job_title}', Extracted Company: '{company_name}', ")

                    # Check for essential data *before* building the full dict
                    if not job_title or not company_name:
                        logging.warning(f"  Skipping JobRight job (ID: {job_id}) due to missing title ('{job_title}') or company ('{company_name}').")
                        continue # Skip this job if essential info is missing

                    # --- Map the rest of the data ---
                    apply_link = job_result.get("applyLink") or job_result.get("originalUrl")
                    application_type = "external" if apply_link else "unknown"

                    description_parts = [job_result.get("jobSummary", "")]
                    if job_result.get("coreResponsibilities"):
                         resp = job_result.get("coreResponsibilities")
                         if isinstance(resp, list): description_parts.extend(resp)
                         elif isinstance(resp, str): description_parts.append(resp)
                    description = "\n\n".join(filter(None, description_parts))

                    job_data = {
                        "source_platform": "jobright",
                        "source_job_id": job_id, # Use extracted variable
                        "source_url": job_result.get("originalUrl"),
                        "application_type": application_type,
                        "application_url": apply_link,
                        "job_title": job_title, # Use extracted variable
                        "company_name": company_name, # Use extracted variable
                        "company_linkedin_url": company_result.get("companyLinkedinURL"),
                        "company_website": company_result.get("companyURL"),
                        "location": job_result.get("jobLocation"),
                        "is_remote": job_result.get("isRemote"),
                        "work_model": job_result.get("workModel"),
                        "publish_time": job_result.get("publishTime"),
                        "publish_time_desc": job_result.get("publishTimeDesc"),
                        "employment_type": job_result.get("employmentType"),
                        "seniority_level": job_result.get("jobSeniority"),
                        "description": description,
                        "description_html": None,
                        "job_summary": job_result.get("jobSummary"),
                        "skills": job_result.get("jdCoreSkills"),
                        "qualifications": job_result.get("qualifications"),
                        "core_responsibilities": job_result.get("coreResponsibilities"),
                        "social_connections": job_result.get("socialConnections"),
                        "personal_social_connections": job_result.get("personalSocialConnections"),
                        # "_raw_data": job_result # Optional
                    }

                    # Add to temp list for JSON backup
                    jobright_scraped_jobs_list.append(job_data)

                    # Attempt to store in MongoDB
                    if store_job_data(job_data):
                         inserted_in_page += 1

                logging.info(f"  Finished processing page for position {position}. Processed: {processed_in_page}, Newly Inserted: {inserted_in_page}")
                total_processed_count += processed_in_page
                total_inserted_count += inserted_in_page

            else:
                logging.warning(f"  No 'result' or 'jobList' found in JobRight API response for position {position}.")

            # *** Add Configurable Delay between API calls ***
            logging.debug(f"Waiting for {config.JOBRIGHT_REQUEST_DELAY_SECONDS} seconds before next request...")
            time.sleep(config.JOBRIGHT_REQUEST_DELAY_SECONDS)

        except requests.exceptions.HTTPError as e:
            # Log specific HTTP errors (like 4xx)
            logging.error(f"HTTP Error fetching JobRight data for position {position}: {e.response.status_code} {e.response.reason}")
            if e.response.status_code in [401, 403]:
                 logging.error("Authorization error (401/403). JobRight cookie might be expired or invalid. Stopping JobRight scraping.")
                 break # Stop if auth fails
            # For other HTTP errors, maybe log and continue to next position?
            time.sleep(config.JOBRIGHT_REQUEST_DELAY_SECONDS) # Apply delay even on error before potentially continuing
            continue # Continue to the next position on other HTTP errors for now
        except requests.exceptions.RequestException as e:
            logging.error(f"Request Error fetching JobRight data for position {position}: {e}")
            break # Stop on general request errors (like connection timeout)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response from JobRight API for position {position}: {e}")
            logging.error(f"Response Text: {response.text[:500]}...")
            time.sleep(config.JOBRIGHT_REQUEST_DELAY_SECONDS) # Apply delay
            continue # Continue to next position
        except Exception as e:
            logging.error(f"An unexpected error occurred during JobRight scraping for position {position}: {e}", exc_info=True)
            break # Stop on unexpected errors

    logging.info(f"--- JobRight API Scraper Finished ---")
    logging.info(f"--- Total Jobs Processed (all pages attempted): {total_processed_count} ---")
    logging.info(f"--- Total New Jobs Inserted (all pages attempted): {total_inserted_count} ---")

    # Optional: Save JobRight backup JSON
    if jobright_scraped_jobs_list:
        try:
            with open(config.OUTPUT_FILENAME_JOBRIGHT, "w", encoding="utf-8") as f:
                serializable_list = []
                for job in jobright_scraped_jobs_list:
                    serializable_job = job.copy()
                    for key, value in serializable_job.items():
                        if isinstance(value, datetime.datetime):
                            serializable_job[key] = value.isoformat()
                    serializable_list.append(serializable_job)
                json.dump(serializable_list, f, ensure_ascii=False, indent=4)
            logging.info(f"--- Saved JobRight backup data to {config.OUTPUT_FILENAME_JOBRIGHT} ---")
        except Exception as e:
            logging.error(f"--- Error saving JobRight backup data to JSON: {e} ---")
