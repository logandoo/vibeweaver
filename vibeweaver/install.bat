@echo off
REM install.bat — Install vibeweaver skill into OpenCode (Windows)

setlocal

set SKILL_NAME=vibeweaver
set SCRIPT_DIR=%~dp0
set SKILLS_DIR=%USERPROFILE%\.config\opencode\skills\%SKILL_NAME%

REM Files to install (flat companions + canonical assertion script)
set FILES=SKILL.md COMPLETION_GATE.md CODING_PRINCIPLES.md ENGINEERING_STD.md REFERENCE.md APPENDIX.md MEMORY_TEMPLATES.md MEMORY_RULES.md TESTING_PROTOCOLS.md scripts\assert_artifacts.py scripts\vibeweaver-audit-core.js scripts\mm_probe.py

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

REM Install the plugin pair (physical gate + Tier-0/1/2 auditor)
if not exist "%USERPROFILE%\.config\opencode\plugins" (
    mkdir "%USERPROFILE%\.config\opencode\plugins"
)
for %%P in (vibeweaver-gate.js vibeweaver-audit.js) do (
    if exist "%SCRIPT_DIR%%%P" (
        copy /y "%SCRIPT_DIR%%%P" "%USERPROFILE%\.config\opencode\plugins\%%P" >nul
        echo [OK] Installed plugin: %%P
    )
)

echo.
echo [OK] vibeweaver skill installed to: %SKILLS_DIR%\
echo      Files installed: 12
echo      Plugins installed to: %USERPROFILE%\.config\opencode\plugins\
echo      Restart OpenCode to activate.

endlocal
