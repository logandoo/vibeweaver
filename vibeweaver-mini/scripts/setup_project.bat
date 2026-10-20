@echo off
REM setup_project.bat — put the mini checker where the gate can find it.
REM Usage: setup_project.bat [project-root]   (default: current directory)

setlocal
set HERE=%~dp0
if "%~1"=="" (set ROOT=%CD%) else (set ROOT=%~1)

if not exist "%ROOT%" (
    echo not a directory: %ROOT%
    exit /b 1
)

if exist "%ROOT%\vw_check.py" (
    echo [OK] kept existing vw_check.py
) else (
    copy /y "%HERE%vw_check.py" "%ROOT%\vw_check.py" >nul
    echo [OK] copied vw_check.py
)

if not exist "%ROOT%\script" mkdir "%ROOT%\script"
if exist "%ROOT%\script\check.sh" (
    echo [OK] kept existing script\check.sh
) else (
    copy /y "%HERE%check.sh" "%ROOT%\script\check.sh" >nul
    echo [OK] copied script\check.sh
)

echo [OK] mini project ready: %ROOT%
echo      Run: bash script/check.sh (or python3 vw_check.py) until ALL CHECKS PASS

endlocal
