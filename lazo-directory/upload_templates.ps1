# upload_templates.ps1 - JC-LAZO-WWT-0907-002
# JC-LAZO-WWT-0915-003: thirteen templates now.
# Puts the wedding-website templates into the lazo-site R2 bucket, one object each.
# Run from C:\Users\kurvh\lazo-directory\worker (where wrangler is logged in):
#   powershell -ExecutionPolicy Bypass -File ..\wedding-websites\upload_templates.ps1
$ErrorActionPreference = 'Stop'
$src = Join-Path $PSScriptRoot 'wedding-websites'
if (-not (Test-Path $src)) { $src = $PSScriptRoot }
foreach ($t in @('atelier','dune','fete','flora','noir','sage','tide','verona','shore','summit','ranch','starlit','frost')) {
  $f = Join-Path $src "$t\index.html"
  if (-not (Test-Path $f)) { throw "missing $f" }
  Write-Host "uploading wedding-websites/$t/index.html"
  npx wrangler r2 object put "lazo-site/wedding-websites/$t/index.html" --file $f --content-type "text/html; charset=utf-8" --remote
}
Write-Host "done - purge Cloudflare cache for /wedding-websites/* (or Purge Everything)"
