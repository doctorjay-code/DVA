param()

Write-Host "==================================================" -ForegroundColor Green
Write-Host "      닥터빌(DVA) 프로그램 환경 설치 시작" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""

Write-Host "[1/4] Python 설치 상태 확인 중..." -ForegroundColor Cyan

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

if ($hasPython) {
    Write-Host "-> Python 설치 상태가 양호합니다. ($pythonCmd)" -ForegroundColor Green
} else {
    Write-Host "-> Python이 감지되지 않았습니다. 신규 설치 단계를 진행합니다." -ForegroundColor Yellow
}

if (-not $hasPython) {
    Write-Host "[2/4] 최신 Python 설치 파일 구성 중..." -ForegroundColor Cyan
    
    $latestVersion = "3.14.6"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $releaseInfo = Invoke-RestMethod -Uri "https://endoflife.date/api/python.json" -UseBasicParsing -TimeoutSec 5
        if ($releaseInfo -and $releaseInfo[0].latest) {
            $latestVersion = $releaseInfo[0].latest
        }
    } catch { }

    $pythonUrl = "https://www.python.org/ftp/python/$latestVersion/python-$latestVersion-amd64.exe"
    $installerPath = "$env:TEMP\python_installer.exe"

    try {
        Write-Host "-> Python 설치 파일 다운로드 시작..." -ForegroundColor Yellow
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $oldProgress = $ProgressPreference
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
        $ProgressPreference = $oldProgress
        
        Write-Host "-> 다운로드 완료. Python 백그라운드 설치를 시작합니다..." -ForegroundColor Yellow
        Write-Host "-> 설치 완료까지 약 30초~1분 정도 소요되니 잠시 기다려 주세요..." -ForegroundColor Cyan
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

Write-Host ""
Write-Host "[3/4] 필수 라이브러리 패키지 설치 중..." -ForegroundColor Cyan
Write-Host "-> pip 및 requirements.txt에 등록된 패키지들을 설치하는 중입니다. (약 30초~1분 소요)" -ForegroundColor Yellow

& $pythonCmd -m pip install --upgrade pip --quiet --disable-pip-version-check
& $pythonCmd -m pip install -r "$PSScriptRoot\requirements.txt"

if ($LASTEXITCODE -eq 0) {
    Write-Host "-> 필수 라이브러리 설치가 완료되었습니다!" -ForegroundColor Green
}
else {
    Write-Host "-> 라이브러리 설치 중 오류가 발생했습니다. 인터넷 연결 상태를 확인하고 다시 시도해 주세요." -ForegroundColor Red
    Read-Host "종료하려면 Enter를 누르세요..."
    exit 1
}

Write-Host ""
Write-Host "[4/4] 계정 정보 설정 프로그램 실행 중..." -ForegroundColor Cyan
Write-Host "-> 계정 정보 입력용 설정 창이 열립니다. 정보를 정확히 입력해 주세요." -ForegroundColor Yellow
& $pythonCmd "$PSScriptRoot\account_setup.py"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "     설치가 모두 완료되었습니다. 창을 닫아주세요!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Read-Host "완료하려면 Enter를 누르세요..."

exit 0
