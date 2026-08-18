@echo off
REM install.bat — Install vibeweaver skill into OpenCode (Windows)

setlocal

set SKILL_NAME=vibeweaver
set SCRIPT_DIR=%~dp0
set SKILLS_DIR=%USERPROFILE%\.config\opencode\skills\%SKILL_NAME%

REM Files to install (flat companions + canonical assertion script)
set FILES=SKILL.md CODING_PRINCIPLES.md ENGINEERING_STD.md REFERENCE.md APPENDIX.md MEMORY_TEMPLATES.md MEMORY_RULES.md TESTING_PROTOCOLS.md scripts\assert_artifacts.py

REM Check source files exist
for %%F in (%FILES%) do (
    if not exist "%SCRIPT_DIR%%%F" (
        echo [ERROR] %%F not found at: %SCRIPT_DIR%%%F
        exit /b 1
    )
)

REM Create target directories
if not exist "%SKILLS_DIR%" (
    mkdir "%SKILLS_DIR%"
)
if not exist "%SKILLS_DIR%\scripts" (
    mkdir "%SKILLS_DIR%\scripts"
)

REM Copy all skill files
for %%F in (%FILES%) do (
    copy /y "%SCRIPT_DIR%%%F" "%SKILLS_DIR%\%%F" >nul
    echo [OK] Installed: %%F
)

echo.
echo [OK] vibeweaver skill installed to: %SKILLS_DIR%\
echo      Files installed: 9
echo      Restart OpenCode to activate.

endlocal
