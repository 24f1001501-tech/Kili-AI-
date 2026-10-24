@echo off
rem Double-click to start Kili AI (SayBetter) locally. Close the window to stop it.
title Kili AI
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
pause
