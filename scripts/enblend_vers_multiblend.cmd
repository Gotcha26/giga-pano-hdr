@echo off
rem Lanceur de enblend_vers_multiblend.ps1 : c'est ce fichier que l'on designe a Hugin comme "enblend".
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0enblend_vers_multiblend.ps1" %*
exit /b %ERRORLEVEL%
