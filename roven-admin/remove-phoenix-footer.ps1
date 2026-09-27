# ============================================================================
# ROVEN - remove-phoenix-footer.ps1  (one-time)
# Removes the "PHOENIX, AZ" span from the footer of every main-site page
# (Roven is nationwide). Skips generated directories. Redeploys when done.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File C:\Users\kurvh\roven-admin\remove-phoenix-footer.ps1
# ============================================================================

$site = "C:\Users\kurvh\roven-site"
$patched = 0

Get-ChildItem "$site\*.html" -File | ForEach-Object {
    $c = Get-Content $_.FullName -Raw
    if ($c -notlike "*PHOENIX, AZ*") {
        Write-Host ("skip    {0}" -f $_.Name) -ForegroundColor DarkGray
        return
    }
    $c = $c -replace '\s*<span>PHOENIX, AZ</span>', ''
    Set-Content -Path $_.FullName -Value $c -NoNewline
    Write-Host ("patched {0}" -f $_.Name) -ForegroundColor Green
    $patched++
}

Write-Host ""
Write-Host "$patched page(s) patched. Deploying..." -ForegroundColor Cyan
Set-Location $site
wrangler pages deploy . --project-name=rovenhr
