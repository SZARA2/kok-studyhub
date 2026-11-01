@echo off
cd /d "%~dp0"
for %%f in ("%~dp0*.vbs") do wscript "%%f"
timeout /t 2 >nul
start "" http://localhost:8626/

