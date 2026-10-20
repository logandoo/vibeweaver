@echo off
REM install.bat — install vibeweaver-mini + its checker gate into OpenCode (Windows)

setlocal

set SCRIPT_DIR=%~dp0
set SKILLS_DIR=%USERPROFILE%\.config\opencode\skills\vibeweaver-mini
set PLUGINS_DIR=%USERPROFILE%\.config\opencode\plugins

set FILES=SKILL.md scripts\vw_check.py scripts\check.sh scripts\setup_project.bat

for %%F in (%FILES%) do (
    if not exist "%SCRIPT_DIR%%%F" (
        echo [ERROR] %%F not found at: %SCRIPT_DIR%%%F
        exit /b 1
    )
)
if not exist "%SCRIPT_DIR%vibeweaver-mini-gate.js" (
    echo [ERROR] vibeweaver-mini-gate.js not found at: %SCRIPT_DIR%
    exit /b 1
)

if not exist "%SKILLS_DIR%\scripts" mkdir "%SKILLS_DIR%\scripts"
if not exist "%PLUGINS_DIR%" mkdir "%PLUGINS_DIR%"

for %%F in (%FILES%) do (
    copy /y "%SCRIPT_DIR%%%F" "%SKILLS_DIR%\%%F" >nul
    if errorlevel 1 (
        echo [ERROR] failed to copy %%F
        exit /b 1
    )
    echo [OK] Installed: %%F
)
copy /y "%SCRIPT_DIR%vibeweaver-mini-gate.js" "%PLUGINS_DIR%\vibeweaver-mini-gate.js" >nul
if errorlevel 1 (
    echo [ERROR] failed to copy vibeweaver-mini-gate.js
    exit /b 1
)
echo [OK] Installed plugin: vibeweaver-mini-gate.js

echo.
echo [OK] vibeweaver-mini installed to: %SKILLS_DIR%\
echo      Plugin installed to: %PLUGINS_DIR%\
echo      In your project, run: setup_project.bat
echo      Restart OpenCode to activate.

endlocal
