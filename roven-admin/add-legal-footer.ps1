# ============================================================================
# ROVEN - add-legal-footer.ps1  (one-time)
# Adds to every main-site page that has a footer-legal block:
#   1. the "not an employment agency" disclaimer line
#   2. an Accessibility link in the footer Legal list (where that list exists)
# Idempotent - skips anything already patched. Redeploys when done.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File C:\Users\kurvh\roven-admin\add-legal-footer.ps1
# ============================================================================

$site = "C:\Users\kurvh\roven-site"

$disclaimer = @'
      <p style="font-size:11px;line-height:1.6;color:rgba(255,255,255,.4);max-width:640px;margin:0 0 14px">Roven is a hiring marketplace. Roven is not an employment agency, staffing firm, or recruiter, and is not a party to any employment relationship formed through the platform.</p>
'@

$privacyLi = '<li><a href="privacy.html">Privacy policy</a></li>'
$accessLi  = '<li><a href="privacy.html">Privacy policy</a></li>' + "`n" + '          <li><a href="accessibility.html">Accessibility</a></li>'
$anchor    = '    <div class="footer-legal">'
$patched = 0

Get-ChildItem "$site\*.html" -File | ForEach-Object {
    $c = Get-Content $_.FullName -Raw
    $changed = $false

    if (($c -like "*$privacyLi*") -and ($c -notlike "*accessibility.html*")) {
        $c = $c.Replace($privacyLi, $accessLi)
        $changed = $true
    }

    if (($c -like "*footer-legal*") -and ($c -notlike "*not an employment agency*")) {
        $idx = $c.IndexOf($anchor)
        if ($idx -ge 0) {
            $c = $c.Substring(0, $idx) + $disclaimer + $c.Substring($idx)
            $changed = $true
        }
    }

    if ($changed) {
        Set-Content -Path $_.FullName -Value $c -NoNewline
        Write-Host ("patched {0}" -f $_.Name) -ForegroundColor Green
        $patched++
    } else {
        Write-Host ("skip    {0}" -f $_.Name) -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "$patched page(s) patched. Deploying..." -ForegroundColor Cyan
Set-Location $site
wrangler pages deploy . --project-name=rovenhr
