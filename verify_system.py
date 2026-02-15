#!/usr/bin/env python3
"""
Automated verification script for AI HR Automation system
"""

import sys
import subprocess
import time
import requests
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print section header"""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def run_command(command, description):
    """Run shell command and return success status"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print_success(description)
            return True, result.stdout
        else:
            print_error(f"{description} - FAILED")
            print(f"Error: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print_error(f"{description} - TIMEOUT")
        return False, "Command timed out"
    except Exception as e:
        print_error(f"{description} - ERROR: {e}")
        return False, str(e)

def check_service(name, url):
    """Check if service is accessible"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print_success(f"{name} is accessible")
            return True
        else:
            print_warning(f"{name} returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"{name} is not accessible")
        return False
    except Exception as e:
        print_error(f"{name} check failed: {e}")
        return False

def main():
    """Main verification function"""
    print_header("AI HR AUTOMATION SYSTEM VERIFICATION")

    results = []

    # 1. Check Docker services
    print_header("1. DOCKER SERVICES")
    success, output = run_command(
        "docker-compose ps",
        "Check Docker Compose services"
    )
    results.append(("Docker Services", success))

    if success:
        services = ["hr-minio", "hr-mongodb", "hr-postgres", "ai-hr-automation-api", "hr-frontend"]
        for service in services:
            if service in output:
                print_success(f"{service} is running")
            else:
                print_warning(f"{service} may not be running")
    else:
        print_error("Could not check Docker services")

    # 2. Check PostgreSQL
    print_header("2. POSTGRESQL DATABASE")
    success, output = run_command(
        "docker exec hr-postgres psql -U hr_user -d hr_users -c 'SELECT COUNT(*) FROM users;'",
        "Check PostgreSQL database and user table"
    )
    results.append(("PostgreSQL", success))

    # 3. Check MongoDB
    print_header("3. MONGODB DATABASE")
    success, output = run_command(
        "docker exec hr-mongodb mongosh --quiet --eval 'db.serverStatus().ok'",
        "Check MongoDB connection"
    )
    results.append(("MongoDB", success))

    # 4. Check MinIO
    print_header("4. MINIO STORAGE")
    success = check_service("MinIO Console", "http://localhost:9001")
    results.append(("MinIO", success))

    # 5. Check Backend API
    print_header("5. BACKEND API")
    success = check_service("Backend Health Check", "http://localhost:8000/health")
    results.append(("Backend API", success))

    if success:
        # Test login
        try:
            response = requests.post(
                "http://localhost:8000/api/auth/token",
                data={
                    "username": "admin@hr-automation.com",
                    "password": "admin123"
                },
                timeout=5
            )
            if response.status_code == 200:
                print_success("Admin login successful")
                token = response.json().get("access_token")
                results.append(("Admin Login", True))

                # Test protected endpoint
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(
                    "http://localhost:8000/api/auth/me",
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    print_success("Protected endpoint accessible")
                    results.append(("Protected Endpoint", True))
                else:
                    print_error("Protected endpoint failed")
                    results.append(("Protected Endpoint", False))
            else:
                print_error("Admin login failed")
                results.append(("Admin Login", False))
        except Exception as e:
            print_error(f"Backend API test failed: {e}")
            results.append(("Backend API", False))
    else:
        print_error("Backend API not accessible, skipping API tests")

    # 6. Check Frontend
    print_header("6. FRONTEND APPLICATION")
    success = check_service("Frontend", "http://localhost:5173")
    results.append(("Frontend", success))

    # Summary
    print_header("VERIFICATION SUMMARY")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    for name, success in results:
        if success:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: FAILED")

    print(f"\n{BLUE}Total: {passed}/{total} checks passed{RESET}")

    if passed == total:
        print(f"\n{GREEN}{'=' * 80}{RESET}")
        print(f"{GREEN}✅ ALL CHECKS PASSED! System is ready to use.{RESET}")
        print(f"{GREEN}{'=' * 80}{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{'=' * 80}{RESET}")
        print(f"{RED}❌ SOME CHECKS FAILED. Please review the errors above.{RESET}")
        print(f"{RED}{'=' * 80}{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
