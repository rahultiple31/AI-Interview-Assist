$ErrorActionPreference = "Stop"

$version = [System.Environment]::OSVersion.Version
if ($version.Major -ne 10 -or $version.Build -lt 10240) {
    Write-Error "Build supports Windows 10 and Windows 11 only."
}

python -m pip install -r requirements.txt
python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "AIInterviewAssist" `
    --add-data "ai_interview_assist;ai_interview_assist" `
    .\main.py

Write-Host "Build complete: dist\AIInterviewAssist\AIInterviewAssist.exe"
