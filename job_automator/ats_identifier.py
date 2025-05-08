# job_automator/ats_identifier.py
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# More comprehensive patterns (order can matter)
ATS_PATTERNS = {
    "greenhouse": [r"boards\.greenhouse\.io", r"greenhouse\.io/embed"],
    "lever": [r"jobs\.lever\.co", r"lever\.co/apply"],
    "ashbyhq": [r"jobs\.ashbyhq\.com"],
    # Workday can be tricky due to custom subdomains
    "workday": [r"\.wd[0-9]+\.myworkdayjobs\.com", r"myworkdayjobs\.com", r"workday\.com/.*careers", r"workday\.com/.*jobs"],
    "bamboohr": [r"\.bamboohr\.com/careers", r"\.bamboohr\.com/jobs"],
    "icims": [r"icims\.com"],
    "smartrecruiters": [r"smartrecruiters\.com"],
    "taleo": [r"taleo\.net"],
    "jobvite": [r"jobs\.jobvite\.com"],
    "oraclecloud": [r"fa\.oraclecloud\.com", r"oraclecloud\.com/hcmUI/CandidateExperience"], # Oracle Fusion / Taleo Cloud
    "sap_successfactors": [r"successfactors\.com", r"sf\.careers"],
    # Add more based on observation
}

def identify_ats_platform(url: str) -> str | None:
    """
    Identifies the ATS platform based on URL patterns. Returns lowercase platform name or None.
    """
    if not url or not isinstance(url, str):
        return None

    try:
        # Optional: Normalize - remove www, use lowercase for matching
        parsed_url = urlparse(url.lower())
        host_plus_path = parsed_url.netloc.replace("www.","") + parsed_url.path

        for platform, patterns in ATS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, host_plus_path): # Search in combined host/path
                    logger.info(f"ATS identified as '{platform}' for URL: {url}")
                    return platform
    except Exception as e:
        logger.error(f"Error during ATS identification for URL {url}: {e}", exc_info=True)
        return None

    logger.warning(f"Could not identify ATS platform via patterns for URL: {url}")
    # Placeholder: Call AI identification if pattern matching fails
    # platform_ai = identify_ats_platform_ai(url, fetch_page_source(url)) # Need a way to get HTML
    # if platform_ai: return platform_ai
    return None

# Placeholder for AI-based identification (requires more infrastructure)
# def identify_ats_platform_ai(url: str, page_html: str) -> str | None:
#     # ... AI logic ...
#     pass

if __name__ == '__main__':
     test_urls = [
         "https://boards.greenhouse.io/openai/jobs/12345",
         "https://openai.wd1.myworkdayjobs.com/en-US/External/job/Location/Job-Title_JR-123",
         "https://jobs.lever.co/google/123abcde-456-etc",
         "https://cloudflare.jobs.ashbyhq.com/postings/123",
         "https://careers.google.com/jobs/results/1234/?company=Google", # Might be custom or need AI
         "https://eexi.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/job/1001",
         "https://performancemanager5.successfactors.eu/sf/jobreq?jobId=123&company=companyP",
         "https://meta.careers/jobs/12345/", # Custom, maybe Workday/SF backend?
         "https://example.bamboohr.com/careers/123",
         "https://us.smartrecruiters.com/Company/Job",
         None,""
     ]
     logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
     for test_url in test_urls:
         platform = identify_ats_platform(test_url)
         print(f"URL: {test_url} -> ATS: {platform}")