@echo off
chcp 65001 > nul
title StorageMap Dev Launcher
color 0B

echo ==================================================
echo       StorageMap Dual Dev Server Launcher
echo ==================================================
echo.

cd /d "%~dp0"

echo [1/3] Starting Backend (Node.js) on Port 3001...
start "StorageMap Backend" cmd /k "title StorageMap Backend & npm run dev"

echo [2/3] Starting Frontend (Vite) on Port 5173...
start "StorageMap Frontend" cmd /k "title StorageMap Frontend & cd client & npm run dev"

echo [3/3] Waiting for servers and opening browser...
ping 127.0.0.1 -n 5 > nul
start http://localhost:5173

echo.
echo All Servers are running in separate windows!
echo Close those windows when you are done.
echo ==================================================
echo Auto-closing launcher in 3 seconds...
ping 127.0.0.1 -n 4 > nul
