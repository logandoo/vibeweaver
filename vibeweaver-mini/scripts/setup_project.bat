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
    findstr /C:"ALL CHECKS PASS" "%ROOT%\vw_check.py" >nul
    if errorlevel 1 (
        echo [ERROR] existing vw_check.py is not the mini checker; refusing to trust it.
        exit /b 1
    )
    findstr /C:"vw_test_hashes" "%ROOT%\vw_check.py" >nul
    if errorlevel 1 (
        echo [ERROR] existing vw_check.py is not the mini checker; refusing to trust it.
        exit /b 1
    )
    echo [OK] kept existing vw_check.py
) else (
    copy /y "%HERE%vw_check.py" "%ROOT%\vw_check.py" >nul
    if errorlevel 1 exit /b 1
    echo [OK] copied vw_check.py
)

if not exist "%ROOT%\script" mkdir "%ROOT%\script"
if exist "%ROOT%\script\check.sh" (
    findstr /C:"vw_check" "%ROOT%\script\check.sh" >nul
    if errorlevel 1 (
        echo [ERROR] existing script\check.sh is not the mini wrapper; refusing to trust it.
        exit /b 1
    )
    echo [OK] kept existing script\check.sh
) else (
    copy /y "%HERE%check.sh" "%ROOT%\script\check.sh" >nul
    if errorlevel 1 exit /b 1
    echo [OK] copied script\check.sh
)

echo [OK] mini project ready: %ROOT%
echo      Run: bash script/check.sh (or python3 vw_check.py) until ALL CHECKS PASS

endlocal
