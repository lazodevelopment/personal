# ============================================================================
# ROVEN - deploy-site.ps1  (v2, ASCII-clean)
# Moves freshly downloaded site files from Downloads into roven-site,
# then deploys to Cloudflare Pages.
#
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File C:\Users\kurvh\roven-admin\deploy-site.ps1
# ============================================================================

$site = "C:\Users\kurvh\roven-site"
$dl   = "$env:USERPROFILE\Downloads"

$known = @(
    "styles.css", "motion.js", "index.html", "employers.html", "about.html",
    "how-it-works.html", "contact.html", "terms.html", "privacy.html",
    "jobs.html", "favicon.ico", "favicon-32.png", "favicon-16.png",
    "apple-touch-icon.png", "og-image.png", "og-square.png",
    "logo.png", "logo-white.png", "icon.png", "check.png"
)

$moved = 0
foreach ($name in $known) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext  = [System.IO.Path]::GetExtension($name)
    $candidates = Get-ChildItem "$dl\$base*$ext" -ErrorAction SilentlyContinue |
                  Where-Object { $_.Name -match "^$([regex]::Escape($base))( \(\d+\))?$([regex]::Escape($ext))$" } |
                  Sort-Object LastWriteTime -Descending
    if ($candidates) {
        $newest = $candidates | Select-Object -First 1
        Move-Item -Force $newest.FullName "$site\$name"
        Write-Host ("moved  {0,-28} -> {1}" -f $newest.Name, $name) -ForegroundColor Green
        $moved++
        $candidates | Select-Object -Skip 1 | Remove-Item -Force
    }
}

if ($moved -eq 0) {
    Write-Host "Nothing to move - no known site files found in Downloads." -ForegroundColor Yellow
    Write-Host "Download the file(s) from the chat first, then rerun."
    exit 1
}

Write-Host ""
Write-Host "$moved file(s) placed. Deploying..." -ForegroundColor Cyan
Set-Location $site
wrangler pages deploy . --project-name=rovenhr
