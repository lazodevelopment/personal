# upload_templates.ps1 - JC-LAZO-WWT-0907-002
# JC-LAZO-WWSEO-0919-006: every wedding-websites/*/index.html (the 13 template
# demos plus the style and intent landing pages) and the hub itself, one object
# each. Helper folders (_*) and scripts never go up.
# Preferred path is now: python wedding-websites\sync_dist.py, then
# python deploy\upload_r2.py --prefix wedding-websites (same objects, boto3).
# This script remains for wrangler-only sessions. Run from C:\Users\kurvh\lazo-directory\worker:
#   powershell -ExecutionPolicy Bypass -File ..\wedding-websites\upload_templates.ps1
$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot
Write-Host "uploading wedding-websites/index.html"
npx wrangler r2 object put "lazo-site/wedding-websites/index.html" --file (Join-Path $src 'index.html') --content-type "text/html; charset=utf-8" --remote
foreach ($d in Get-ChildItem -Path $src -Directory | Where-Object { $_.Name -notlike '_*' -and (Test-Path (Join-Path $_.FullName 'index.html')) }) {
  $t = $d.Name
  Write-Host "uploading wedding-websites/$t/index.html"
  npx wrangler r2 object put "lazo-site/wedding-websites/$t/index.html" --file (Join-Path $d.FullName 'index.html') --content-type "text/html; charset=utf-8" --remote
}
Write-Host "done - purge Cloudflare cache for /wedding-websites/* (or Purge Everything)"
