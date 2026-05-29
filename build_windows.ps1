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

$finalProductPath = Join-Path $PSScriptRoot "final-product"
$portableAppPath = Join-Path $finalProductPath "AI-Interview-Assist"
$builtAppPath = Join-Path $PSScriptRoot "dist\AIInterviewAssist"

if (Test-Path $portableAppPath) {
    Remove-Item -LiteralPath $portableAppPath -Recurse -Force
}

New-Item -ItemType Directory -Path $finalProductPath -Force | Out-Null
Copy-Item -Path $builtAppPath -Destination $portableAppPath -Recurse -Force

Write-Host "Build complete: $portableAppPath\AIInterviewAssist.exe"
