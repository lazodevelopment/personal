# JC-LAZO-WWI-0907-002 - uploads the wedding-websites index page. Run from lazo-directory\worker:
#   powershell -ExecutionPolicy Bypass -File ..\wedding-websites\upload_index.ps1
$f = Join-Path $PSScriptRoot 'index.html'
npx wrangler r2 object put "lazo-site/wedding-websites/index.html" --file $f --content-type "text/html; charset=utf-8" --remote
