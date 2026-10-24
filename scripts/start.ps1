param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$projectPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.13 -m venv .venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv .venv
    } else {
        throw 'Instale Python 3.13 e habilite o comando py ou python. Depois execute novamente.'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o ambiente virtual.' }
    & $projectPython -m pip install -c constraints.txt -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível instalar as dependências.' }
}
& $projectPython -m tigrifes.build_site --output site
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível gerar o site estático.' }
Write-Host "TigrIFES estático em http://127.0.0.1:$Port (Ctrl+C para encerrar)."
& $projectPython -m http.server $Port --directory site --bind 127.0.0.1
exit $LASTEXITCODE
