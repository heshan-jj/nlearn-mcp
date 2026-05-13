@echo off
cd /d "D:\Work\Code\GitHubRepos\nlearn mcp"

echo [%date% %time%] Running NLearn iCal generator... >> ical_cron.log 2>&1

python generate_ical.py --days 30 --output deadlines.ics >> ical_cron.log 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: generate_ical.py failed with code %errorlevel% >> ical_cron.log
    exit /b %errorlevel%
)

git add deadlines.ics >> ical_cron.log 2>&1
git diff --cached --quiet && (
    echo [%date% %time%] No changes to commit. >> ical_cron.log
) || (
    git commit -m "chore: update deadlines.ics [skip ci]" >> ical_cron.log 2>&1
    git push >> ical_cron.log 2>&1
    echo [%date% %time%] Pushed updated deadlines.ics >> ical_cron.log
)
