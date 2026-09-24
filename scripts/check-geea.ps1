# Diagnóstico da ligação dos contentores ao GEEA e ao Keycloak. Corre-se na raiz do repositório:
#
#   powershell -ExecutionPolicy Bypass -File scripts\check-geea.ps1
#
# Não muda nada: só lê o .env, o compose e o que os contentores vêem.
#
# São dois servidores: o GEEA, que faz o login (GEEA_SSOLOGIN_URL), e o Keycloak,
# que emite os tokens (AUTH_ISSUER, AUTH_JWKS_URL, GEEA_TOKEN_URL).

$ErrorActionPreference = 'Continue'
$falhas = 0
function Ok($texto)     { Write-Host "  [OK]     $texto" -ForegroundColor Green }
function Falha($texto)  { Write-Host "  [FALHA]  $texto" -ForegroundColor Red; $script:falhas++ }
function Nota($texto)   { Write-Host "           $texto" }

Set-Location (Join-Path $PSScriptRoot '..')
Write-Host ''
Write-Host 'Ligação ao GEEA e ao Keycloak'
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
# O nome antigo do par do Keycloak, que o compose também aceita.
if (-not $env_['KEYCLOAK_HOSTNAME']) { $env_['KEYCLOAK_HOSTNAME'] = $env_['GEEA_ISSUER_HOSTNAME'] }
if (-not $env_['KEYCLOAK_IP']) { $env_['KEYCLOAK_IP'] = $env_['GEEA_ISSUER_IP'] }

$login = $env_['GEEA_SSOLOGIN_URL']; $chaves = $env_['AUTH_JWKS_URL']; $issuer = $env_['AUTH_ISSUER']
if (-not $login -or -not $chaves -or -not $issuer) { Falha 'faltam GEEA_SSOLOGIN_URL, AUTH_JWKS_URL ou AUTH_ISSUER no .env'; exit 1 }
Nota "GEEA (login):       $login"
Nota "Keycloak (tokens):  $issuer"
if (-not $chaves.StartsWith($issuer)) { Falha 'o AUTH_JWKS_URL não começa pelo AUTH_ISSUER: os dois são do mesmo servidor' }

# 2. Os pares nome e IP, cada um completo ou vazio.
$pares = @(
    @{ Nome = 'GEEA_HOSTNAME'; Ip = 'GEEA_IP'; Para = 'GEEA (login)' },
    @{ Nome = 'KEYCLOAK_HOSTNAME'; Ip = 'KEYCLOAK_IP'; Para = 'Keycloak (tokens)' }
)
$mapeados = @()
foreach ($par in $pares) {
    $h = $env_[$par.Nome]; $i = $env_[$par.Ip]
    if ($h -and $i) { Ok "$($par.Nome)=$h e $($par.Ip)=$i ($($par.Para))"; $mapeados += @{ Host = $h; Ip = $i } }
    elseif ($h -or $i) { Falha "só uma de $($par.Nome) e $($par.Ip) está preenchida: são as duas, ou nenhuma" }
    else { Nota "$($par.Nome) e $($par.Ip) vazios: o nome do $($par.Para) tem de resolver sozinho no Docker" }
}

# 3. O compose lê-os, e 4. o contentor foi recriado com eles.
$config = docker compose config 2>$null | Out-String
$hosts = docker exec mozaops-auth-service cat /etc/hosts 2>$null | Out-String
if (-not $hosts) { Falha 'o contentor mozaops-auth-service não está a correr (docker compose up -d)'; exit 1 }
foreach ($m in $mapeados) {
    if ($config -notmatch [regex]::Escape("$($m.Host)=$($m.Ip)")) { Falha "o docker compose não mostra $($m.Host)=$($m.Ip): o docker-compose.yml é antigo?" }
    elseif ($hosts -match "$([regex]::Escape($m.Ip))\s+$([regex]::Escape($m.Host))") { Ok "o contentor sabe que $($m.Host) é $($m.Ip)" }
    else { Falha "o contentor não sabe onde está $($m.Host): falta recriá-lo (docker compose up -d)" }
}

# 5. Proxy dentro do contentor.
$variaveis = docker exec mozaops-auth-service printenv 2>$null
$proxy = $variaveis | Select-String -Pattern '^(HTTP|HTTPS)_PROXY=' -CaseSensitive:$false
if ($proxy) {
    $proxy | ForEach-Object { Nota "proxy no contentor: $($_.Line)" }
    $semProxy = ($variaveis | Select-String -Pattern '^NO_PROXY=' -CaseSensitive).Line
    foreach ($m in $mapeados) {
        if ($semProxy -notmatch [regex]::Escape($m.Host)) { Falha "$($m.Host) não está no NO_PROXY do contentor" }
    }
}
else { Ok 'o contentor não tem proxy configurado' }

# 6. O contentor chega aos dois servidores.
$teste = "import sys, urllib.request as u, urllib.error as e`nmetodo = sys.argv[2]`ncorpo = b'' if metodo == 'POST' else None`ntry:`n    print(u.urlopen(u.Request(sys.argv[1], data=corpo, method=metodo), timeout=10).status)`nexcept e.HTTPError as x:`n    print(x.code)`nexcept Exception as x:`n    print(type(x).__name__, x)"
function Pedido($url, $metodo = 'GET') { (docker exec mozaops-auth-service python -c $teste $url $metodo 2>&1 | Out-String).Trim() }

# O login é POST, como o MozaOps o faz; sem parâmetros o GEEA responde um erro, mas responde.
$resposta = Pedido ($login -split '\?')[0] 'POST'
if ($resposta -match '^\d{3}$') { Ok "o contentor chega ao GEEA (responde $resposta)" }
else { Falha "o contentor não chega ao GEEA: $resposta" }

$resposta = Pedido $chaves
if ($resposta -eq '200') { Ok 'o contentor chega ao Keycloak, às chaves dos tokens (200)' }
elseif ($resposta -match '^\d{3}$') { Falha "o Keycloak responde ${resposta} nas chaves: o AUTH_JWKS_URL está errado (tem de ser o iss dos tokens + /protocol/openid-connect/certs)" }
else { Falha "o contentor não chega ao Keycloak: $resposta" }

if ($falhas -gt 0) {
    Nota ''
    Nota 'Se o Postman chega e o contentor não: confirmar os pontos acima, e no Docker Desktop,'
    Nota 'Settings > Resources > Proxies, pôr os hosts e os IPs do GEEA e do Keycloak nas excepções.'
}

Write-Host ''
if ($falhas -eq 0) { Write-Host 'Tudo certo: os contentores chegam ao GEEA e ao Keycloak.' -ForegroundColor Green }
else { Write-Host "$falhas problema(s) por resolver." -ForegroundColor Red }
Write-Host ''
