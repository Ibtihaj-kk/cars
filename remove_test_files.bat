@echo off
REM YallaMotor Test Files Removal Batch Script
REM This script removes all test files from the project
REM Run this from the project root directory

echo ========================================
echo YallaMotor Test Files Removal
echo ========================================
echo.

cd /d "%~dp0"

echo Removing root-level test files...
if exist "test_api.py" del /f "test_api.py" && echo   - Deleted test_api.py
if exist "test_api_auth.py" del /f "test_api_auth.py" && echo   - Deleted test_api_auth.py
if exist "test_dashboard_api.py" del /f "test_dashboard_api.py" && echo   - Deleted test_dashboard_api.py

echo.
echo Removing app-level test files...
if exist "admin_panel\tests.py" del /f "admin_panel\tests.py" && echo   - Deleted admin_panel\tests.py
if exist "content\tests.py" del /f "content\tests.py" && echo   - Deleted content\tests.py
if exist "inquiries\tests.py" del /f "inquiries\tests.py" && echo   - Deleted inquiries\tests.py
if exist "listings\tests.py" del /f "listings\tests.py" && echo   - Deleted listings\tests.py
if exist "notifications\tests.py" del /f "notifications\tests.py" && echo   - Deleted notifications\tests.py
if exist "reviews\tests.py" del /f "reviews\tests.py" && echo   - Deleted reviews\tests.py
if exist "subscriptions\tests.py" del /f "subscriptions\tests.py" && echo   - Deleted subscriptions\tests.py
if exist "users\tests.py" del /f "users\tests.py" && echo   - Deleted users\tests.py
if exist "vehicles\tests.py" del /f "vehicles\tests.py" && echo   - Deleted vehicles\tests.py

echo.
echo Removing test templates...
if exist "templates\business_partners\design_test.html" del /f "templates\business_partners\design_test.html" && echo   - Deleted design_test.html
if exist "templates\business_partners\responsive_test.html" del /f "templates\business_partners\responsive_test.html" && echo   - Deleted responsive_test.html
if exist "templates\business_partners\test_standard_template.html" del /f "templates\business_partners\test_standard_template.html" && echo   - Deleted test_standard_template.html
if exist "templates\business_partners\vendor_crud_test.html" del /f "templates\business_partners\vendor_crud_test.html" && echo   - Deleted vendor_crud_test.html
if exist "templates\business_partners\VENDOR_DASHBOARD_RESPONSIVE_TESTING.md" del /f "templates\business_partners\VENDOR_DASHBOARD_RESPONSIVE_TESTING.md" && echo   - Deleted VENDOR_DASHBOARD_RESPONSIVE_TESTING.md
if exist "templates\business_partners\vendor_responsive_test.html" del /f "templates\business_partners\vendor_responsive_test.html" && echo   - Deleted vendor_responsive_test.html
if exist "templates\business_partners\vendor_system_test.html" del /f "templates\business_partners\vendor_system_test.html" && echo   - Deleted vendor_system_test.html

echo.
echo Removing test directories...
if exist "business_partners\tests" rd /s /q "business_partners\tests" && echo   - Deleted business_partners\tests\
if exist "core\tests" rd /s /q "core\tests" && echo   - Deleted core\tests\
if exist "users\tests" rd /s /q "users\tests" && echo   - Deleted users\tests\
if exist "yallamotor_project\tests" rd /s /q "yallamotor_project\tests" && echo   - Deleted yallamotor_project\tests\

echo.
echo Cleaning cached test files...
if exist "parts\__pycache__\test*.pyc" del /f /q "parts\__pycache__\test*.pyc" 2>nul && echo   - Cleaned parts\__pycache__\
if exist "business_partners\__pycache__\test*.pyc" del /f /q "business_partners\__pycache__\test*.pyc" 2>nul && echo   - Cleaned business_partners\__pycache__\
if exist "yallamotor_project\__pycache__\test*.pyc" del /f /q "yallamotor_project\__pycache__\test*.pyc" 2>nul && echo   - Cleaned yallamotor_project\__pycache__\

echo.
echo ========================================
echo Test files removal completed!
echo ========================================
echo.
pause
