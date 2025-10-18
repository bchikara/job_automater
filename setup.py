"""
Setup script for Job Agent CLI
"""

from setuptools import setup, find_packages

setup(
    name='job-agent-cli',
    version='1.0.0',
    description='AI-Powered Job Application Automation CLI',
    author='Your Name',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pymongo',
        'python-dotenv',
        'linkedin-jobs-scraper',
        'selenium',
        'webdriver-manager',
        'google-generativeai',
        'PyPDF2',
        'reportlab',
        'beautifulsoup4',
        'langchain_google_genai',
        'click>=8.0.0',
        'rich>=13.0.0',
        'questionary>=2.0.0',
    ],
    entry_points={
        'console_scripts': [
            'job-agent=cli:cli',
        ],
    },
    python_requires='>=3.8',
)
