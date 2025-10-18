# Job Agent - Complete Setup Guide

Welcome to Job Agent! This guide will walk you through setting up the automated job application system on your machine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Configuration](#configuration)
5. [Resume and Profile Setup](#resume-and-profile-setup)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed
- **MongoDB** installed and running locally
- **LaTeX distribution** (for PDF generation):
  - macOS: Install [MacTeX](https://www.tug.org/mactex/)
  - Linux: `sudo apt-get install texlive-full`
  - Windows: Install [MiKTeX](https://miktex.org/)
- **Google Gemini API Key** (free): Get it [here](https://aistudio.google.com/app/apikey)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/job_agent.git
cd job_agent

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the interactive setup wizard
python cli.py setup

# 5. Edit your resume data
# Edit base_resume.json with your experience and projects
# Edit info/achievements.txt with your achievements

# 6. Validate your configuration
python cli.py validate-config

# 7. Start using Job Agent!
./job-agent interactive
```

---

## Detailed Setup

### Step 1: Install System Dependencies

#### MongoDB Installation

**macOS (using Homebrew):**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Linux (Ubuntu/Debian):**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
```

**Windows:**
Download and install from [MongoDB Download Center](https://www.mongodb.com/try/download/community)

#### Verify MongoDB is Running

```bash
# Check if MongoDB is running
mongosh  # Should connect successfully

# Or check the service status
brew services list | grep mongodb  # macOS
sudo systemctl status mongod       # Linux
```

---

### Step 2: Python Environment Setup

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

---

### Step 3: Configuration

#### Option A: Interactive Setup Wizard (Recommended)

```bash
python cli.py setup
```

The wizard will guide you through:
- Creating your `.env` file
- Setting up API credentials
- Entering personal information
- Configuring professional profiles
- Creating resume template files

#### Option B: Manual Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit the file with your preferred editor
nano .env  # or vim, code, etc.
```

**Required fields in .env:**

```bash
# API Credentials
GEMINI_API_KEY=your_api_key_here

# Personal Information
YOUR_NAME=John Doe
FIRST_NAME=John
LAST_NAME=Doe
YOUR_EMAIL=john.doe@example.com
YOUR_PHONE=5551234567

# Address
STREET_ADDRESS=123 Main Street
CITY=New York
STATE=New York
ZIP_CODE=10001
LOCATION=New York, NY

# Professional Profiles
YOUR_LINKEDIN_PROFILE_URL=https://linkedin.com/in/johndoe
YOUR_GITHUB_URL=https://github.com/johndoe

# Work Authorization
WORK_AUTHORIZED=Yes
REQUIRE_SPONSORSHIP=No

# Professional Background
YEARS_EXPERIENCE=3
JOB_TITLE_CURRENT=Software Engineer
TECH_STACK=Python, JavaScript, React, Node.js
```

See `.env.example` for all available options.

---

### Step 4: Resume and Profile Setup

#### Create Your Base Resume

```bash
# Copy the example template
cp base_resume.json.example base_resume.json

# Edit with your actual experience
nano base_resume.json
```

**Structure of base_resume.json:**

```json
{
  "experience": [
    {
      "company": "Your Company",
      "title": "Your Job Title",
      "dates": "Jan 2022 -- Present",
      "technologies": "Python, React, AWS",
      "location": "City, State",
      "description": [
        "Bullet point describing your achievement or responsibility",
        "Another bullet point with quantified impact"
      ]
    }
  ],
  "projects": [
    {
      "title": "Project Name",
      "technologies": "Tech stack used",
      "dates": "Month Year -- Month Year",
      "description": [
        "What you built and the impact",
        "Technologies and methodologies used"
      ]
    }
  ],
  "skills": {
    "skills_list": ["Skill1", "Skill2", "Skill3"],
    "tools_list": ["Tool1", "Tool2", "Tool3"]
  }
}
```

#### Add Your Achievements

```bash
# Copy the example template
cp info/achievements.txt.example info/achievements.txt

# Edit with your actual achievements
nano info/achievements.txt
```

Add your:
- Professional achievements
- Awards and recognitions
- Certifications
- Notable contributions
- Quantified impacts

---

### Step 5: Validation

Verify your configuration is correct:

```bash
# Run the configuration validator
python cli.py validate-config

# Or run it standalone
python config_validator.py
```

This will check:
- ✓ All required fields are filled
- ✓ API keys are valid format
- ✓ Email and URLs are properly formatted
- ✓ Files exist in expected locations

---

## Configuration

### Environment Variables Reference

See `.env.example` for detailed documentation of all available configuration options.

**Categories:**

1. **API Credentials**: Gemini API, scraping cookies
2. **Personal Information**: Name, contact details, address
3. **Professional Profiles**: LinkedIn, GitHub, portfolio
4. **Work Authorization**: Work status, sponsorship needs
5. **Professional Background**: Experience, skills, achievements
6. **Optional Settings**: Database, paths, AI model selection

### Chrome User Data Directory (Browser Session Persistence)

For browser automation features, you can configure Chrome to use your existing browser profile, which allows:
- ✅ Persistent login sessions across automation runs
- ✅ Access to saved cookies and authentication
- ✅ Maintain form auto-fill data
- ✅ Use browser extensions

**Configuration in config.yaml:**

```yaml
advanced:
  chrome:
    user_data_dir: "/path/to/chrome/user/data"
```

**Default Chrome User Data Paths:**

- **macOS**: `/Users/USERNAME/Library/Application Support/Google/Chrome`
- **Windows**: `C:\Users\USERNAME\AppData\Local\Google\Chrome\User Data`
- **Linux**: `/home/USERNAME/.config/google-chrome`

**Example:**

```yaml
# macOS example
advanced:
  chrome:
    user_data_dir: "/Users/vipul/Library/Application Support/Google/Chrome"

# Windows example
advanced:
  chrome:
    user_data_dir: "C:\\Users\\vipul\\AppData\\Local\\Google\\Chrome\\User Data"
```

**Important Notes:**
- Close all Chrome windows before running automation with your profile
- You cannot run Chrome and automation simultaneously with the same profile
- For safety, consider using a separate Chrome profile for automation
- If left empty, a temporary profile will be created for each session

### LaTeX Resume Customization

The resume template is in `resume_tailor/tailor.py`. You can customize:

- **Fonts**: Uncomment font options in `RESUME_PREAMBLE`
- **Formatting**: Adjust margins, spacing, colors
- **Sections**: Modify section order and content
- **Header**: Update layout in `RESUME_HEADER`

To create custom LaTeX resume templates:

1. Edit the template sections in `tailor.py`
2. Or create a new template file and update the loader
3. Test compilation with `pdflatex` manually first

---

## Resume and Profile Setup

### Best Practices for base_resume.json

1. **Be Specific**: Use concrete examples and metrics
2. **Quantify Impact**: Include numbers, percentages, scale
3. **Action Verbs**: Start bullets with strong verbs (Led, Built, Improved)
4. **Relevant Technologies**: List tech stacks that match your target jobs
5. **Recent First**: Order experience and projects chronologically (newest first)

### Tips for achievements.txt

- Focus on measurable outcomes
- Include context (problem → solution → impact)
- Highlight leadership and collaboration
- Mention technologies and methodologies
- Keep it updated with latest accomplishments

---

## Troubleshooting

### Common Issues

#### "Configuration validation failed"

**Problem**: Required fields are missing or invalid

**Solution**:
```bash
# Run the validator to see specific errors
python cli.py validate-config

# Or use the setup wizard to reconfigure
python cli.py setup
```

#### "Failed to connect to database"

**Problem**: MongoDB is not running

**Solution**:
```bash
# Check if MongoDB is running
mongosh

# Start MongoDB
brew services start mongodb-community  # macOS
sudo systemctl start mongod             # Linux
```

#### "PDFLaTeX not found"

**Problem**: LaTeX is not installed or not in PATH

**Solution**:
- macOS: Install MacTeX from https://www.tug.org/mactex/
- Linux: `sudo apt-get install texlive-full`
- Or set `PDFLATEX_PATH` in `.env` to the full path

#### "Gemini API error / Rate limit"

**Problem**: API key invalid or rate limits exceeded

**Solutions**:
- Verify API key at https://aistudio.google.com/app/apikey
- Check quota limits in Google AI Studio
- Try switching to `gemini-2.5-flash-lite` (higher rate limits)

#### "No jobs found"

**Problem**: LinkedIn/JobRight cookies not configured

**Solution**:
1. Login to LinkedIn/JobRight
2. Open DevTools (F12) → Application → Cookies
3. Copy the cookie value (for LinkedIn: `li_at` cookie)
4. Add to `.env` file
5. Note: Scraping is optional - you can still use the system without it

### Getting Help

- **Documentation**: Check `README.md` and `CLAUDE.md`
- **Logs**: Check `logs/cli.log` for detailed error messages
- **Issues**: Report bugs on GitHub Issues
- **Configuration**: Run `python cli.py config-info` to see current settings

---

## Next Steps

Once setup is complete:

1. **Test the system**:
   ```bash
   python cli.py interactive
   ```

2. **Fetch some jobs** (optional):
   ```bash
   python cli.py fetch-jobs --source both --limit 10
   ```

3. **Generate documents for a job**:
   ```bash
   python cli.py generate-docs --interactive
   ```

4. **Apply to a job**:
   ```bash
   python cli.py apply --interactive
   ```

5. **Check status**:
   ```bash
   python cli.py status
   ```

---

## Security Best Practices

- ✅ **Never commit `.env` file** to version control
- ✅ **Use environment-specific passwords** (not your real passwords)
- ✅ **Rotate API keys** periodically
- ✅ **Review generated PDFs** before submitting
- ✅ **Keep MongoDB secure** (use authentication in production)
- ✅ **Back up your data** regularly

---

## Support and Contribution

- **Issues**: https://github.com/yourusername/job_agent/issues
- **Contributing**: See `CONTRIBUTING.md`
- **License**: MIT License (see `LICENSE`)

Happy job hunting! 🚀
