# Lanceur du projet pour Windows (PowerShell 5.1+). Utiliser de preference `scout.cmd` a la racine :
#
#   scout                  demarre l'interface web (installe le projet si besoin) et ouvre le navigateur
#   scout web -Port 8080   idem sur un autre port ; -NoBrowser pour ne pas ouvrir le navigateur
#   scout setup            cree l'environnement virtuel et installe le projet
#   scout test             lance les tests
#   scout check            porte qualite : format, lint, typage strict, tests
#   scout demo             classement de demonstration dans le terminal
#
# Messages volontairement sans accents : PowerShell 5.1 lit les scripts sans BOM en ANSI.

param(
    [Parameter(Position = 0)]
    [string]$Command = "web",
    [int]$Port = 8000,
    [string]$Address = "127.0.0.1",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
Set-Location $Root

function Say([string]$Message) { Write-Host "[fuzzy-scouting] $Message" -ForegroundColor Green }
function Fail([string]$Message) { Write-Host "[fuzzy-scouting] $Message" -ForegroundColor Red; exit 1 }

function Invoke-Step([string[]]$Arguments) {
    & $Py @Arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# Vrai si le projet est importable DEPUIS CE DOSSIER, avec ses dependances web et de test.
# (Un venv cree avant un deplacement du dossier pointe encore sur l'ancien chemin.)
function Test-Installed {
    if (-not (Test-Path $Py)) { return $false }
    $probe = "import sys, pathlib, fuzzyscout, fastapi, uvicorn, pytest; " +
        "sys.exit(0 if pathlib.Path(fuzzyscout.__file__).resolve().is_relative_to(pathlib.Path.cwd().resolve()) else 1)"
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $Py -c $probe 2>$null | Out-Null
    $ErrorActionPreference = $previous
    return ($LASTEXITCODE -eq 0)
}

function Install-Project {
    if (-not (Test-Path $Py)) {
        Say "Creation de l'environnement virtuel (.venv)..."
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($launcher) { & py -3 -m venv .venv } else { & python -m venv .venv }
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Py)) {
            Fail "Impossible de creer .venv : Python 3.11 ou plus recent est requis (https://www.python.org/downloads/)."
        }
    }
    Say "Installation du projet et de ses dependances..."
    Invoke-Step @("-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-e", ".[api,dev]")
    Say "Installation terminee."
}

function Confirm-Installed {
    if (-not (Test-Installed)) { Install-Project }
}

function Test-PortOpen {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect($Address, $Port); return $true } catch { return $false } finally { $client.Close() }
}

function Start-Web {
    $url = "http://${Address}:$Port"
    if (Test-PortOpen) {
        $health = $null
        try { $health = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 3 } catch { }
        if ($health -and $health.status -eq "ok") {
            Say "Le serveur tourne deja sur $url."
            if (-not $NoBrowser) { Start-Process $url }
            return
        }
        Fail "Le port $Port est occupe par un autre programme. Essayez : scout web -Port 8080"
    }
    if (-not $NoBrowser) {
        # Ouvre le navigateur des que le serveur repond (au plus 30 s d'attente).
        Start-Job -ArgumentList $url -ScriptBlock {
            param($url)
            for ($i = 0; $i -lt 60; $i++) {
                try { Invoke-RestMethod -Uri "$url/health" -TimeoutSec 2 | Out-Null; Start-Process $url; break }
                catch { Start-Sleep -Milliseconds 500 }
            }
        } | Out-Null
    }
    Say "Interface web : $url   (Ctrl+C pour arreter)"
    & $Py -m fuzzyscout.interfaces.cli serve --host $Address --port $Port
    exit $LASTEXITCODE
}

switch ($Command) {
    "help" {
        Get-Content $PSCommandPath | Where-Object { $_ -match "^#   " } | ForEach-Object { $_.Substring(2) }
    }
    "setup" { Install-Project }
    "web" { Confirm-Installed; Start-Web }
    "test" { Confirm-Installed; Invoke-Step @("-m", "pytest") }
    "check" {
        Confirm-Installed
        Invoke-Step @("-m", "ruff", "format", "--check", "src", "tests", "scripts")
        Invoke-Step @("-m", "ruff", "check", "src", "tests", "scripts")
        Invoke-Step @("-m", "mypy")
        Invoke-Step @("-m", "pytest")
        Say "Porte qualite verte."
    }
    "demo" {
        Confirm-Installed
        Invoke-Step @("-m", "fuzzyscout.interfaces.cli", "rank", "--position", "attaquant", "--top", "10", "--min-minutes", "900")
    }
    default { Fail "Commande inconnue : $Command (voir : scout help)" }
}
