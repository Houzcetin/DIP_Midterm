@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0" || exit /b 1

if /i "%~1"=="/build" (
    call "%~dp0build.bat" /nopause
    if errorlevel 1 exit /b 1
) else if not "%~1"=="" (
    echo Usage: package.bat [/build] 1>&2
    exit /b 1
)

if not exist "dist\DIP_Midterm.exe" (
    echo Error: dist\DIP_Midterm.exe is missing. Run package.bat /build. 1>&2
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    echo Error: .venv\Scripts\python.exe is missing. Run setup.bat first. 1>&2
    exit /b 1
)
".venv\Scripts\python.exe" tools\make_readme.py
if errorlevel 1 (
    echo Error: README.pdf generation failed. 1>&2
    exit /b 1
)
if not exist "README.pdf" (
    echo Error: README.pdf is missing. 1>&2
    exit /b 1
)

powershell.exe -NoProfile -NonInteractive -Command ^
    "$ErrorActionPreference = 'Stop';" ^
    "$root = (Get-Location).Path;" ^
    "$stagingRoot = Join-Path $root 'build\package';" ^
    "$stage = Join-Path $stagingRoot ([Guid]::NewGuid().ToString('N'));" ^
    "$archive = Join-Path $root 'DIP_Midterm_OguzCetin.zip';" ^
    "try {" ^
    "    $null = New-Item -ItemType Directory -Path (Join-Path $stage 'dist') -Force;" ^
    "    Copy-Item -LiteralPath 'dist\DIP_Midterm.exe' -Destination (Join-Path $stage 'dist');" ^
    "    Copy-Item -LiteralPath 'README.pdf' -Destination $stage;" ^
    "    robocopy.exe 'src' (Join-Path $stage 'src') /E /XD __pycache__ /XJ /NFL /NDL /NJH /NJS /NP;" ^
    "    if ($LASTEXITCODE -ge 8) { throw ('Source staging failed (Robocopy exit code ' + $LASTEXITCODE + ').') };" ^
    "    $entries = 'dist', 'src', 'README.pdf' | ForEach-Object { Join-Path $stage $_ };" ^
    "    $stagedArchive = Join-Path $stage 'submission.zip';" ^
    "    Compress-Archive -LiteralPath $entries -DestinationPath $stagedArchive -CompressionLevel Optimal;" ^
    "    Move-Item -LiteralPath $stagedArchive -Destination $archive -Force;" ^
    "    Write-Output ('Created ' + $archive);" ^
    "} finally {" ^
    "    if (Test-Path -LiteralPath $stage) {" ^
    "        $resolved = (Resolve-Path -LiteralPath $stage).ProviderPath;" ^
    "        if (-not $resolved.StartsWith($stagingRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {" ^
    "            throw ('Unexpected staging path ' + $resolved);" ^
    "        };" ^
    "        Remove-Item -LiteralPath $resolved -Recurse -Force;" ^
    "    };" ^
    "}; exit 0"
exit /b %errorlevel%
