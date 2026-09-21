@echo off
title Event Ticketing and Booking Platform
set "ROOT=%~dp0"
set "MYSQLD=C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
set "MYSQLDATA=C:\ProgramData\MySQL\MySQL Server 8.4\Data"

echo Checking MySQL...
netstat -an | findstr "LISTENING" | findstr ":3306" >nul
if errorlevel 1 (
    echo Starting MySQL...
    start "MySQL" /min "%MYSQLD%" --datadir="%MYSQLDATA%"
    :mysqlwait
    timeout /t 2 /nobreak >nul
    netstat -an | findstr "LISTENING" | findstr ":3306" >nul
    if errorlevel 1 goto mysqlwait
)
echo MySQL is running.

echo Starting Django backend...
if exist "%ROOT%backend\venv\Scripts\python.exe" (
    start "Django Backend" /d "%ROOT%backend" cmd /k venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
) else (
    start "Django Backend" /d "%ROOT%backend" cmd /k python manage.py runserver 127.0.0.1:8000
)

echo Starting React frontend...
start "React Frontend" /d "%ROOT%frontend" cmd /k npm run dev

echo Waiting for the app to respond...
where curl >nul 2>&1
if errorlevel 1 (
    echo curl not found, waiting 15 seconds instead...
    timeout /t 15 /nobreak >nul
) else (
    for /l %%i in (1,1,30) do (
        curl -s -o nul http://localhost:5173 >nul 2>&1
        if not errorlevel 1 goto openapp
        timeout /t 2 /nobreak >nul
    )
)

:openapp
echo Opening application...
start "" chrome http://localhost:5173

echo.
echo Event Ticketing and Booking Platform started.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo.
pause
