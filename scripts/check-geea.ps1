# Diagnóstico da ligação dos contentores ao GEEA. Corre-se na raiz do repositório:
#
#   powershell -ExecutionPolicy Bypass -File scripts\check-geea.ps1
#
# Não muda nada: só lê o .env, o compose e o que os contentores vêem.

$ErrorActionPreference = 'Continue'
$falhas = 0
function Ok($texto)     { Write-Host "  [OK]     $texto" -ForegroundColor Green }
function Falha($texto)  { Write-Host "  [FALHA]  $texto" -ForegroundColor Red; $script:falhas++ }
function Nota($texto)   { Write-Host "           $texto" }

Set-Location (Join-Path $PSScriptRoot '..')
Write-Host ''
Write-Host 'Ligação ao GEEA'
Write-Host ''

# 1. O .env existe com esse nome exacto, e não .env.txt.
if (-not (Test-Path -LiteralPath '.env')) {
    Falha 'não há ficheiro .env nesta pasta'
    Get-ChildItem -Force -Filter '.env*' | ForEach-Object { Nota "encontrado: $($_.Name)" }
    exit 1
}
Ok 'o .env existe'

$env_ = @{}
Get-Content -LiteralPath '.env' | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object {
    $nome, $valor = $_ -split '=', 2
    $env_[$nome.Trim()] = $valor.Trim().Trim('"')
}

# 2. O nome e o IP do GEEA, juntos.
$geeaHost = $env_['GEEA_HOSTNAME']; $geeaIp = $env_['GEEA_IP']
if ($geeaHost -and $geeaIp) { Ok "GEEA_HOSTNAME=$geeaHost e GEEA_IP=$geeaIp no .env" }
elseif ($geeaHost -or $geeaIp) { Falha 'só uma de GEEA_HOSTNAME e GEEA_IP está preenchida: são as duas, ou nenhuma' }
else { Nota 'GEEA_HOSTNAME e GEEA_IP não estão no .env: o nome do GEEA tem de resolver sozinho dentro do Docker' }

$url = $env_['AUTH_JWKS_URL']
if (-not $url) { Falha 'AUTH_JWKS_URL não está no .env'; exit 1 }
Nota "o GEEA configurado: $url"

# 3. O compose lê-os.
if ($geeaHost -and $geeaIp) {
    $config = docker compose config 2>$null | Out-String
    if ($config -match [regex]::Escape("$geeaHost=$geeaIp")) { Ok 'o docker compose lê o nome e o IP' }
    else { Falha 'o docker compose não mostra o extra_hosts do GEEA: o docker-compose.yml é antigo?' }
}

# 4. O contentor foi recriado com eles.
$hosts = docker exec mozaops-auth-service cat /etc/hosts 2>$null | Out-String
if (-not $hosts) { Falha 'o contentor mozaops-auth-service não está a correr (docker compose up -d)'; exit 1 }
if ($geeaHost -and $geeaIp) {
    if ($hosts -match "$([regex]::Escape($geeaIp))\s+$([regex]::Escape($geeaHost))") { Ok "o contentor sabe que $geeaHost é $geeaIp" }
    else { Falha 'o contentor não tem a entrada do GEEA: falta recriá-lo (docker compose up -d)' }
}

# 5. Proxy dentro do contentor.
$variaveis = docker exec mozaops-auth-service printenv 2>$null
$proxy = $variaveis | Select-String -Pattern '^(HTTP|HTTPS)_PROXY=' -CaseSensitive:$false
if ($proxy) {
    $proxy | ForEach-Object { Nota "proxy no contentor: $($_.Line)" }
    $semProxy = ($variaveis | Select-String -Pattern '^NO_PROXY=' -CaseSensitive).Line
    if ($geeaHost -and $semProxy -notmatch [regex]::Escape($geeaHost)) { Falha 'o GEEA não está no NO_PROXY do contentor' }
    else { Ok "o GEEA passa ao lado do proxy ($semProxy)" }
}
else { Ok 'o contentor não tem proxy configurado' }

# 6. O contentor chega ao GEEA.
$teste = "import sys, urllib.request as u`ntry:`n    print(u.urlopen(sys.argv[1], timeout=10).status)`nexcept Exception as e:`n    print(type(e).__name__, e)"
$resposta = docker exec mozaops-auth-service python -c $teste $url 2>&1 | Out-String
$resposta = $resposta.Trim()
if ($resposta -eq '200') { Ok 'o contentor chega ao GEEA (200)' }
else {
    Falha "o contentor não chega ao GEEA: $resposta"
    Nota 'Se o Postman chega e o contentor não: confirmar os pontos acima, e no Docker Desktop,'
    Nota 'Settings > Resources > Proxies, pôr o host e o IP do GEEA nas excepções.'
}

Write-Host ''
if ($falhas -eq 0) { Write-Host 'Tudo certo: os contentores chegam ao GEEA.' -ForegroundColor Green }
else { Write-Host "$falhas problema(s) por resolver." -ForegroundColor Red }
Write-Host ''
