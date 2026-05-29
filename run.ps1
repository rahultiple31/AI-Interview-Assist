$ErrorActionPreference = "Stop"

$version = [System.Environment]::OSVersion.Version
if ($version.Major -ne 10 -or $version.Build -lt 10240) {
    Write-Error "AI Interview Assist runs only on Windows 10 or Windows 11."
}

python .\main.py
