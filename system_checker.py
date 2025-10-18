"""
System Dependencies Checker
Checks all required system dependencies before setup
"""
import sys
import shutil
import subprocess
from pathlib import Path

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class SystemChecker:
    def __init__(self):
        self.results = {
            'python': False,
            'mongodb': False,
            'pdflatex': False,
            'pip': False
        }
        self.warnings = []

    def print_header(self):
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}  SYSTEM REQUIREMENTS CHECK{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}\n")

    def print_success(self, msg):
        print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

    def print_error(self, msg):
        print(f"{Colors.RED}✗ {msg}{Colors.END}")

    def print_warning(self, msg):
        print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

    def check_python_version(self):
        """Check Python version is 3.8+"""
        print(f"{Colors.BOLD}Checking Python...{Colors.END}")
        version = sys.version_info

        if version.major == 3 and version.minor >= 8:
            self.print_success(f"Python {version.major}.{version.minor}.{version.micro} found")
            self.results['python'] = True
            return True
        else:
            self.print_error(f"Python 3.8+ required, found {version.major}.{version.minor}.{version.micro}")
            print(f"{Colors.YELLOW}  Install: https://www.python.org/downloads/{Colors.END}")
            return False

    def check_pip(self):
        """Check pip is available"""
        print(f"\n{Colors.BOLD}Checking pip...{Colors.END}")
        pip_path = shutil.which('pip') or shutil.which('pip3')

        if pip_path:
            try:
                result = subprocess.run(['pip', '--version'], capture_output=True, text=True)
                self.print_success(f"pip found: {result.stdout.strip()}")
                self.results['pip'] = True
                return True
            except:
                pass

        self.print_error("pip not found")
        print(f"{Colors.YELLOW}  Install: python -m ensurepip --upgrade{Colors.END}")
        return False

    def check_mongodb(self):
        """Check if MongoDB is installed and running"""
        print(f"\n{Colors.BOLD}Checking MongoDB...{Colors.END}")

        # Check if mongod is installed
        mongod_path = shutil.which('mongod')
        mongosh_path = shutil.which('mongosh') or shutil.which('mongo')

        if not mongod_path:
            self.print_error("MongoDB not installed")
            print(f"{Colors.YELLOW}  macOS: brew install mongodb-community{Colors.END}")
            print(f"{Colors.YELLOW}  Linux: sudo apt-get install mongodb-org{Colors.END}")
            print(f"{Colors.YELLOW}  Windows: https://www.mongodb.com/try/download/community{Colors.END}")
            return False

        self.print_success(f"MongoDB installed at {mongod_path}")

        # Check if MongoDB is running
        if mongosh_path:
            try:
                result = subprocess.run(
                    [mongosh_path, '--eval', 'db.version()', '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.print_success(f"MongoDB is running (version: {result.stdout.strip()})")
                    self.results['mongodb'] = True
                    return True
                else:
                    self.print_warning("MongoDB installed but not running")
                    print(f"{Colors.YELLOW}  Start: brew services start mongodb-community (macOS){Colors.END}")
                    print(f"{Colors.YELLOW}  Start: sudo systemctl start mongod (Linux){Colors.END}")
                    self.warnings.append('mongodb_not_running')
                    return False
            except subprocess.TimeoutExpired:
                self.print_warning("MongoDB not responding (timeout)")
                self.warnings.append('mongodb_timeout')
                return False
            except Exception as e:
                self.print_warning(f"Could not connect to MongoDB: {e}")
                self.warnings.append('mongodb_connection_failed')
                return False
        else:
            self.print_warning("mongosh not found - cannot verify MongoDB is running")
            self.warnings.append('mongosh_not_found')
            return False

    def check_pdflatex(self):
        """Check if pdflatex is installed"""
        print(f"\n{Colors.BOLD}Checking LaTeX (pdflatex)...{Colors.END}")

        pdflatex_path = shutil.which('pdflatex')

        if pdflatex_path:
            try:
                result = subprocess.run(
                    ['pdflatex', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
                self.print_success(f"pdflatex found: {version_line}")
                self.results['pdflatex'] = True
                return True
            except:
                pass

        self.print_error("pdflatex not found")
        print(f"{Colors.YELLOW}  macOS: Install MacTeX from https://www.tug.org/mactex/{Colors.END}")
        print(f"{Colors.YELLOW}  Linux: sudo apt-get install texlive-full{Colors.END}")
        print(f"{Colors.YELLOW}  Windows: Install MiKTeX from https://miktex.org/{Colors.END}")
        return False

    def check_git(self):
        """Check if git is installed (optional but recommended)"""
        print(f"\n{Colors.BOLD}Checking Git (optional)...{Colors.END}")

        git_path = shutil.which('git')

        if git_path:
            try:
                result = subprocess.run(['git', '--version'], capture_output=True, text=True)
                self.print_success(f"Git found: {result.stdout.strip()}")
                return True
            except:
                pass

        self.print_warning("Git not found (optional, but recommended)")
        print(f"{Colors.YELLOW}  Install: https://git-scm.com/downloads{Colors.END}")
        return False

    def check_all(self, verbose=True):
        """Run all checks"""
        if verbose:
            self.print_header()

        checks = [
            ('python', self.check_python_version),
            ('pip', self.check_pip),
            ('mongodb', self.check_mongodb),
            ('pdflatex', self.check_pdflatex),
        ]

        all_passed = True
        for name, check_func in checks:
            passed = check_func()
            if not passed and name in ['python', 'pip']:  # Critical dependencies
                all_passed = False

        # Optional checks
        self.check_git()

        if verbose:
            self.print_summary()

        return all_passed

    def print_summary(self):
        """Print summary of checks"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}  SUMMARY{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}\n")

        critical = ['python', 'pip']
        required = ['mongodb', 'pdflatex']

        # Critical dependencies
        critical_pass = all(self.results.get(dep, False) for dep in critical)
        if critical_pass:
            self.print_success("All critical dependencies met (Python, pip)")
        else:
            self.print_error("Missing critical dependencies!")
            print(f"{Colors.RED}  Cannot proceed without Python 3.8+ and pip{Colors.END}\n")
            return False

        # Required dependencies
        required_pass = all(self.results.get(dep, False) for dep in required)
        if required_pass:
            self.print_success("All required dependencies met (MongoDB, LaTeX)")
        else:
            missing = [dep for dep in required if not self.results.get(dep, False)]
            self.print_warning(f"Missing dependencies: {', '.join(missing)}")

            if 'mongodb_not_running' in self.warnings:
                print(f"\n{Colors.YELLOW}MongoDB is installed but not running.{Colors.END}")
                print(f"{Colors.CYAN}Start it with:{Colors.END}")
                print(f"  macOS: brew services start mongodb-community")
                print(f"  Linux: sudo systemctl start mongod")

            if not self.results.get('pdflatex'):
                print(f"\n{Colors.YELLOW}LaTeX is required for PDF generation.{Colors.END}")
                print(f"{Colors.CYAN}You can proceed with setup, but install LaTeX before generating resumes.{Colors.END}")

        print()
        return critical_pass

def main():
    """Run standalone system check"""
    checker = SystemChecker()
    all_passed = checker.check_all(verbose=True)

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ System is ready for Job Agent setup!{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Please install missing dependencies before proceeding.{Colors.END}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
