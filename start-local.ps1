param(
    [switch]$CreateAdmin,
    [switch]$ResetPassword
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskVenvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $taskVenvPython)) {
    $taskPythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $taskPython = if ($taskPythonCommand) {
        $taskPythonCommand.Source
    } else {
        Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    }
    if (-not (Test-Path -LiteralPath $taskPython)) {
        throw 'Instala Python 3.12 o superior y vuelve a ejecutar este archivo.'
    }

    & $taskPython -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudo crear el entorno virtual.'
    }
    & $taskVenvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudieron instalar las dependencias. Ejecuta .venv\Scripts\python.exe -m pip install -r requirements.txt y vuelve a intentar.'
    }
}

if (-not $env:APP_SECRET) {
    $taskSecretDirectory = Join-Path $env:LOCALAPPDATA 'TamaraAdmin'
    New-Item -ItemType Directory -Force -Path $taskSecretDirectory | Out-Null
    $taskSecretFile = Join-Path $taskSecretDirectory 'server-key.dpapi'
    if (-not (Test-Path -LiteralPath $taskSecretFile)) {
        $taskSecret = & $taskVenvPython -c 'import secrets; print(secrets.token_urlsafe(48))'
        $taskEncrypted = ConvertTo-SecureString -String $taskSecret -AsPlainText -Force | ConvertFrom-SecureString
        [System.IO.File]::WriteAllText($taskSecretFile, $taskEncrypted)
        $taskSecret = $null
    }
    $taskSecure = Get-Content -LiteralPath $taskSecretFile -Raw | ConvertTo-SecureString
    $taskCredential = [System.Net.NetworkCredential]::new('', $taskSecure)
    $env:APP_SECRET = $taskCredential.Password
}

if (-not $env:APP_ORIGIN) {
    $env:APP_ORIGIN = 'http://127.0.0.1:8765'
}

if ($CreateAdmin) {
    & $taskVenvPython manage.py create-admin
} elseif ($ResetPassword) {
    & $taskVenvPython manage.py reset-password
} else {
    # Windows PowerShell 5.1 treats redirected native stderr as error records.
    # Waitress warnings must be logged without terminating the running server.
    $taskPreviousErrorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $taskVenvPython manage.py serve
        $taskServeExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $taskPreviousErrorPreference
    }
    if ($taskServeExitCode -ne 0) {
        throw "El servidor termino con codigo $taskServeExitCode. Revisa tamara-inicio.log."
    }
}

if ($LASTEXITCODE -ne 0) {
    throw 'La operación no terminó correctamente. Revisa el mensaje anterior.'
}