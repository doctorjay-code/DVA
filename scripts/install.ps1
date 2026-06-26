param()

# Python이 실제로 작동하는지(윈도우 스토어 가짜 파일이 아닌지) 확인합니다
$hasPython = $false
$pythonCmd = "python"

if (Get-Command $pythonCmd -ErrorAction SilentlyContinue) {
    try {
        $out = (& $pythonCmd --version 2>&1) -join " "
        if ($LASTEXITCODE -eq 0 -and $out -notmatch "was not found" -and $out -match "Python") {
            $hasPython = $true
        }
    } catch { }
}

if (-not $hasPython) {
    $pythonCmd = "py"
    if (Get-Command $pythonCmd -ErrorAction SilentlyContinue) {
        try {
            $out = (& $pythonCmd --version 2>&1) -join " "
            if ($LASTEXITCODE -eq 0 -and $out -match "Python") {
                $hasPython = $true
            }
        } catch { }
    }
}

if (-not $hasPython) {
    Write-Host "Python not found. Installing..." -ForegroundColor Yellow
    
    $pythonUrl = "https://www.python.org/ftp/python/3.13.1/python-3.13.1-amd64.exe"
    $installerPath = "$env:TEMP\python_installer.exe"

    try {
        Write-Host "Downloading Python..." -ForegroundColor Cyan
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $oldProgress = $ProgressPreference
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
        $ProgressPreference = $oldProgress
        
        Write-Host "Installing Python..." -ForegroundColor Cyan
        $process = Start-Process -FilePath $installerPath `
            -ArgumentList "/passive InstallAllUsers=1 PrependPath=1" `
            -Wait -PassThru
        
        if ($process.ExitCode -ne 0) {
            Write-Host "Installation failed with exit code: $($process.ExitCode)" -ForegroundColor Red
            Read-Host "Press Enter"
            exit 1
        }
        
        Start-Sleep -Seconds 5
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        
        Write-Host "Python installed! Reloading environment..." -ForegroundColor Green
        
        # Refresh PATH for the current session
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $pythonCmd = "python"
    }
    catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Read-Host "Press Enter"
        exit 1
    }
}

Write-Host "Using Python command: $pythonCmd" -ForegroundColor Cyan

Write-Host ""
Write-Host "Installing packages..." -ForegroundColor Cyan
& $pythonCmd -m pip install --upgrade pip --quiet --disable-pip-version-check
& $pythonCmd -m pip install -r "$PSScriptRoot\requirements.txt"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Packages installed successfully!" -ForegroundColor Green
}
else {
    Write-Host "Package installation failed!" -ForegroundColor Red
    Read-Host "Press Enter"
    exit 1
}

# 2. 계정 정보 설정 (인코딩 문제 방지를 위해 파이썬으로 위임)
& $pythonCmd "$PSScriptRoot\account_setup.py"

exit 0
