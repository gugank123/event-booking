# Migrate local MySQL (backend/.env) into Aiven MySQL.
# Usage: right-click > Run with PowerShell, or:
#   cd backend; .\migrate-to-aiven.ps1
# You will be prompted for the full Aiven Service URI (with real password).
# Get it from Aiven console > your service > Overview > Service URI
# (click the eye icon to reveal the password BEFORE copying).
# Also download ca.pem from the same Overview page into backend/ca.pem.

$ErrorActionPreference = "Stop"
$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BackendDir

$BinDir = "C:\Program Files\MySQL\MySQL Server 8.4\bin"
$DumpExe = Join-Path $BinDir "mysqldump.exe"
$MysqlExe = Join-Path $BinDir "mysql.exe"
if (-not (Test-Path $DumpExe)) { throw "mysqldump not found at $DumpExe" }
if (-not (Test-Path $MysqlExe)) { throw "mysql not found at $MysqlExe" }

$CaFile = Join-Path $BackendDir "ca.pem"
if (-not (Test-Path $CaFile)) {
    Write-Host "ERROR: ca.pem not found in $BackendDir" -ForegroundColor Red
    Write-Host "Download it from Aiven console > service Overview page and save as backend/ca.pem, then re-run."
    exit 1
}

# Load local DB credentials from backend/.env
$envMap = @{}
Get-Content (Join-Path $BackendDir ".env") | ForEach-Object {
    if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') { $envMap[$matches[1].Trim()] = $matches[2].Trim() }
}
$LocalHost = $envMap["MYSQL_HOST"]; if (-not $LocalHost) { $LocalHost = "127.0.0.1" }
$LocalPort = $envMap["MYSQL_PORT"]; if (-not $LocalPort) { $LocalPort = "3306" }
$LocalUser = $envMap["MYSQL_USER"]; if (-not $LocalUser) { $LocalUser = "eventflow" }
$LocalDb = $envMap["MYSQL_DATABASE"]; if (-not $LocalDb) { $LocalDb = "eventflow" }
$LocalPass = $envMap["MYSQL_PASSWORD"]
if (-not $LocalPass) { $LocalPass = Read-Host "Local MySQL password for $LocalUser" -AsSecureString | ForEach-Object { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) } }

Write-Host "Aiven Service URI (right-click > Paste). It must contain the REAL password, not CLICK_TO_REVEAL:"
$AivenUri = Read-Host "MYSQL_URL"
if ($AivenUri -match "CLICK_TO") {
    Write-Host "ERROR: URI still contains CLICK_TO_REVEAL_PASSWORD. Go back to Aiven, click the eye icon to reveal, then copy again." -ForegroundColor Red
    exit 1
}

# Parse URI with Python (handles URL-encoded passwords correctly)
$ParsedJson = $AivenUri | venv\Scripts\python.exe -c "import sys, json, urllib.parse; u=urllib.parse.urlparse(sys.stdin.read().strip()); print(json.dumps({'user':urllib.parse.unquote(u.username or ''),'pass':urllib.parse.unquote(u.password or ''),'host':u.hostname,'port':u.port or 21347,'db':(u.path or '/defaultdb').lstrip('/')})))"
$P = $ParsedJson | ConvertFrom-Json
Write-Host "Target: $($P.user)@$($P.host):$($P.port)/$($P.db)"

# 1) Dump local DB
$DumpFile = Join-Path $BackendDir "eventflow-dump.sql"
Write-Host "Dumping local $LocalDb -> $DumpFile ..."
$env:MYSQL_PWD = $LocalPass
& $DumpExe -h $LocalHost -P $LocalPort -u $LocalUser --single-transaction --routines --events $LocalDb > $DumpFile
$env:MYSQL_PWD = $null
Write-Host ("Dump done: {0:N1} KB" -f ((Get-Item $DumpFile).Length / 1KB))
if ((Get-Item $DumpFile).Length -lt 1024) {
    Write-Host "ERROR: dump is almost empty. Your local MySQL server is probably not running." -ForegroundColor Red
    Write-Host "Start it first: Start-Process 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe' -ArgumentList '--datadir=`"C:\ProgramData\MySQL\MySQL Server 8.4\Data`"'"
    exit 1
}

# 2) Restore into Aiven (SSL required) — fail loudly on any error
Write-Host "Restoring into Aiven (this overwrites tables in $($P.db)) ..."
$env:MYSQL_PWD = $P.pass
$RestoreErr = Join-Path $BackendDir "restore-error.log"
Get-Content $DumpFile -Raw | & $MysqlExe --ssl-mode=REQUIRED --ssl-ca="$CaFile" -h $P.host -P $P.port -u $P.user $P.db 2> $RestoreErr
$RestoreExit = $LASTEXITCODE
$env:MYSQL_PWD = $null
if ($RestoreExit -ne 0) {
    Write-Host "ERROR: restore failed (mysql exit code $RestoreExit)." -ForegroundColor Red
    Write-Host "--- mysql error output ---"
    Get-Content $RestoreErr
    Write-Host "--------------------------"
    exit 1
}
Remove-Item $RestoreErr -ErrorAction SilentlyContinue
Write-Host "Restore done." -ForegroundColor Green

# 2b) Confirm tables actually landed on Aiven before continuing
Write-Host 'Confirming table count on Aiven ...'
$env:MYSQL_PWD = $P.pass
$CountDb = $P.db
$CountSql = 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ''' + $CountDb + ''';'
$TableCountRaw = & $MysqlExe --ssl-mode=REQUIRED --ssl-ca="$CaFile" -h $P.host -P $P.port -u $P.user -N -e $CountSql
$env:MYSQL_PWD = $null
$TableCount = "$TableCountRaw".Trim()
Write-Host ('Tables in Aiven ' + $CountDb + ': ' + $TableCount)
if ([int]$TableCount -lt 5) {
    Write-Host 'ERROR: Aiven DB still looks empty. The restore did not take - paste the full log above.' -ForegroundColor Red
    exit 1
}

# 3) Verify Django can talk to Aiven
Write-Host "Verifying Django connection to Aiven ..."
$env:MYSQL_URL = $AivenUri
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py showmigrations --list | Select-Object -Last 8
$env:MYSQL_URL = $null

Write-Host ""
Write-Host "OK. Next: on Render set MYSQL_URL to the same URI and MYSQL_SSL_CA_CONTENT to the text of ca.pem." -ForegroundColor Green
