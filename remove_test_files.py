"""
YallaMotor Test Files Removal Script
=====================================
This script removes all test files and directories from the YallaMotor project.
Run this script from your project root or provide the project path.

Author: Principal Engineer
Date: November 15, 2025
"""

import os
import shutil
import sys

# Project base path
BASE_PATH = r"C:\Users\Ibtihaj\Desktop\yallamotor"

# List of files to delete (relative to base path)
FILES_TO_DELETE = [
    # Root level test files
    "test_api.py",
    "test_api_auth.py",
    "test_dashboard_api.py",
    
    # App-level test files
    "admin_panel/tests.py",
    "content/tests.py",
    "inquiries/tests.py",
    "listings/tests.py",
    "notifications/tests.py",
    "reviews/tests.py",
    "subscriptions/tests.py",
    "users/tests.py",
    "vehicles/tests.py",
    
    # Test templates
    "templates/business_partners/design_test.html",
    "templates/business_partners/responsive_test.html",
    "templates/business_partners/test_standard_template.html",
    "templates/business_partners/vendor_crud_test.html",
    "templates/business_partners/VENDOR_DASHBOARD_RESPONSIVE_TESTING.md",
    "templates/business_partners/vendor_responsive_test.html",
    "templates/business_partners/vendor_system_test.html",
]

# List of directories to delete (relative to base path)
DIRECTORIES_TO_DELETE = [
    "business_partners/tests",
    "core/tests",
    "users/tests",
    "yallamotor_project/tests",
]

def delete_file(filepath):
    """Delete a single file."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True, f"✓ Deleted file: {os.path.basename(filepath)}"
        else:
            return False, f"⚠ File not found: {os.path.basename(filepath)}"
    except Exception as e:
        return False, f"✗ Error deleting {os.path.basename(filepath)}: {str(e)}"

def delete_directory(dirpath):
    """Delete a directory and all its contents."""
    try:
        if os.path.exists(dirpath):
            shutil.rmtree(dirpath)
            return True, f"✓ Deleted directory: {os.path.basename(dirpath)}"
        else:
            return False, f"⚠ Directory not found: {os.path.basename(dirpath)}"
    except Exception as e:
        return False, f"✗ Error deleting {os.path.basename(dirpath)}: {str(e)}"

def main():
    """Main execution function."""
    print("="*70)
    print("YallaMotor Test Files Removal Script")
    print("="*70)
    print(f"\nProject Path: {BASE_PATH}\n")
    
    # Check if base path exists
    if not os.path.exists(BASE_PATH):
        print(f"✗ ERROR: Project path not found: {BASE_PATH}")
        print("Please update the BASE_PATH variable in this script.")
        return False
    
    # Statistics
    files_deleted = 0
    files_not_found = 0
    files_errors = 0
    dirs_deleted = 0
    dirs_not_found = 0
    dirs_errors = 0
    
    # Delete files
    print("DELETING TEST FILES")
    print("-" * 70)
    for file_rel_path in FILES_TO_DELETE:
        full_path = os.path.join(BASE_PATH, file_rel_path)
        success, message = delete_file(full_path)
        print(f"  {message}")
        if success:
            files_deleted += 1
        elif "not found" in message.lower():
            files_not_found += 1
        else:
            files_errors += 1
    
    # Delete directories
    print("\nDELETING TEST DIRECTORIES")
    print("-" * 70)
    for dir_rel_path in DIRECTORIES_TO_DELETE:
        full_path = os.path.join(BASE_PATH, dir_rel_path)
        success, message = delete_directory(full_path)
        print(f"  {message}")
        if success:
            dirs_deleted += 1
        elif "not found" in message.lower():
            dirs_not_found += 1
        else:
            dirs_errors += 1
    
    # Clean __pycache__ directories with test files
    print("\nCLEANING CACHED TEST FILES")
    print("-" * 70)
    pycache_cleaned = 0
    pycache_dirs = [
        "parts/__pycache__",
        "business_partners/__pycache__",
        "yallamotor_project/__pycache__",
    ]
    
    for pycache_dir in pycache_dirs:
        full_path = os.path.join(BASE_PATH, pycache_dir)
        if os.path.exists(full_path):
            # Find and delete test-related .pyc files
            for filename in os.listdir(full_path):
                if "test" in filename.lower() and filename.endswith(".pyc"):
                    file_path = os.path.join(full_path, filename)
                    try:
                        os.remove(file_path)
                        print(f"  ✓ Deleted: {pycache_dir}/{filename}")
                        pycache_cleaned += 1
                    except Exception as e:
                        print(f"  ✗ Error deleting {filename}: {str(e)}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Files deleted:     {files_deleted}")
    print(f"Files not found:   {files_not_found}")
    print(f"File errors:       {files_errors}")
    print(f"Dirs deleted:      {dirs_deleted}")
    print(f"Dirs not found:    {dirs_not_found}")
    print(f"Dir errors:        {dirs_errors}")
    print(f"Cache files cleaned: {pycache_cleaned}")
    print("="*70)
    
    total_deleted = files_deleted + dirs_deleted + pycache_cleaned
    print(f"\n✓ Total items removed: {total_deleted}")
    
    if files_errors > 0 or dirs_errors > 0:
        print(f"⚠ Total errors: {files_errors + dirs_errors}")
        return False
    
    print("\n✓ Test files cleanup completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        sys.exit(1)
