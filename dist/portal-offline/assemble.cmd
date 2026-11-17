@echo off
REM Copyright (c) Microsoft. All rights reserved.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0assemble.ps1" %*
exit /b %ERRORLEVEL%
