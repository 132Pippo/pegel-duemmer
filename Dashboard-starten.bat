@echo off
rem Doppelklick startet das Pegel-Dashboard (Daten aktualisieren, Server starten, Browser oeffnen)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
