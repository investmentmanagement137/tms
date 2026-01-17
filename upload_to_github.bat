@echo off
echo ========================================================
echo SETTING UP GITHUB REPOSITORY
echo ========================================================

:: 1. Initialize Git (Safe to run even if already initialized)
echo Initializing Git...
git init

:: 2. Configure User
echo Configuring User...
git config user.email "investmentmanagement137@gmail.com"
git config user.name "investmentmanagement137"

:: 3. Add Remote (Remove existing first to ensure correct URL)
echo Configuring Remote 'origin'...
git remote remove origin 2>nul
git remote add origin https://github.com/investmentmanagement137/tms.git

:: 4. .gitignore (Ensure we ignore temp files)
echo Creating/Updating .gitignore...
if not exist .gitignore (
    echo __pycache__ > .gitignore
    echo *.pyc >> .gitignore
    echo *.csv >> .gitignore
    echo *.log >> .gitignore
    echo .env >> .gitignore
    echo .idea >> .gitignore
    echo .vscode >> .gitignore
    echo venv >> .gitignore
)

:: 5. Add All Files
echo Adding files to staging...
git add .

:: 6. Commit
echo Committing files...
git commit -m "Initial commit of TMS Apify Actor"

:: 7. Push
echo Pushing to GitHub (main)...
git branch -M main
git push -u origin main

echo ========================================================
echo DONE!
echo ========================================================
pause
