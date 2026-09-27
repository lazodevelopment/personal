# ============================================================================
# ROVEN - add-social-footer.ps1  (one-time)
# Injects the @hireroven social icon row into every main-site page that has
# a footer-legal block and doesn't already have the icons. Skips generated
# directories (business/, jobs/, company/). Run AFTER deploy-site.ps1 has
# placed the three freshly-downloaded pages (employers/terms/privacy), then
# this patches the rest (index, about, how-it-works, contact, 404...) and
# redeploys.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File C:\Users\kurvh\roven-admin\add-social-footer.ps1
# ============================================================================

$site = "C:\Users\kurvh\roven-site"

$social = @'
    <div class="footer-social" style="display:flex;gap:14px;align-items:center;margin:26px 0 18px">
      <a href="https://facebook.com/hireroven" target="_blank" rel="noopener" aria-label="Roven on Facebook" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 21v-8h2.7l.4-3.2h-3.1V7.7c0-.9.3-1.6 1.6-1.6h1.7V3.2c-.3 0-1.3-.1-2.5-.1-2.5 0-4.2 1.5-4.2 4.3v2.4H7.4V13h2.7v8h3.4z"/></svg>
      </a>
      <a href="https://instagram.com/hireroven" target="_blank" rel="noopener" aria-label="Roven on Instagram" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.2c3.2 0 3.6 0 4.9.1 1.2.1 1.8.2 2.2.4.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.2.4.4 1 .4 2.2.1 1.3.1 1.7.1 4.9s0 3.6-.1 4.9c-.1 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.2-1 .4-2.2.4-1.3.1-1.7.1-4.9.1s-3.6 0-4.9-.1c-1.2-.1-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1-.4-2.2C2.2 15.6 2.2 15.2 2.2 12s0-3.6.1-4.9c.1-1.2.2-1.8.4-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.2 1-.4 2.2-.4C8.4 2.2 8.8 2.2 12 2.2zm0 1.8c-3.1 0-3.5 0-4.8.1-1.1.1-1.5.2-1.7.3-.4.2-.7.4-1 .7-.3.3-.5.6-.7 1-.1.2-.3.6-.3 1.7-.1 1.3-.1 1.7-.1 4.8s0 3.5.1 4.8c.1 1.1.2 1.5.3 1.7.2.4.4.7.7 1 .3.3.6.5 1 .7.2.1.6.3 1.7.3 1.3.1 1.7.1 4.8.1s3.5 0 4.8-.1c1.1-.1 1.5-.2 1.7-.3.4-.2.7-.4 1-.7.3-.3.5-.6.7-1 .1-.2.3-.6.3-1.7.1-1.3.1-1.7.1-4.8s0-3.5-.1-4.8c-.1-1.1-.2-1.5-.3-1.7-.2-.4-.4-.7-.7-1-.3-.3-.6-.5-1-.7-.2-.1-.6-.3-1.7-.3-1.3-.1-1.7-.1-4.8-.1zm0 3.1a4.9 4.9 0 1 1 0 9.8 4.9 4.9 0 0 1 0-9.8zm0 1.8a3.1 3.1 0 1 0 0 6.2 3.1 3.1 0 0 0 0-6.2zm5.1-3.1a1.1 1.1 0 1 1 0 2.3 1.1 1.1 0 0 1 0-2.3z"/></svg>
      </a>
      <a href="https://youtube.com/@hireroven" target="_blank" rel="noopener" aria-label="Roven on YouTube" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 7.2s-.2-1.4-.8-2c-.7-.8-1.6-.8-2-.9C16 4 12 4 12 4s-4 0-6.8.3c-.4 0-1.2.1-2 .9-.6.6-.8 2-.8 2S2.2 8.9 2.2 10.5v1.5c0 1.6.2 3.3.2 3.3s.2 1.4.8 2c.7.8 1.7.8 2.1.9 1.6.1 6.7.3 6.7.3s4 0 6.8-.3c.4 0 1.2-.1 2-.9.6-.6.8-2 .8-2s.2-1.6.2-3.3v-1.5c0-1.6-.2-3.3-.2-3.3zM9.9 14.9V8.6l5.4 3.2-5.4 3.1z"/></svg>
      </a>
      <a href="https://tiktok.com/@hireroven" target="_blank" rel="noopener" aria-label="Roven on TikTok" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M16.6 5.8a5.4 5.4 0 0 1-1.2-3.3h-3v12.2a2.9 2.9 0 1 1-2.1-2.8V8.7a6 6 0 1 0 5.2 5.9V9.2a8.4 8.4 0 0 0 4.9 1.6V7.7a5.4 5.4 0 0 1-3.8-1.9z"/></svg>
      </a>
    </div>
'@

$anchor = '    <div class="footer-legal">'
$patched = 0

Get-ChildItem "$site\*.html" -File | ForEach-Object {
    $c = Get-Content $_.FullName -Raw
    if ($c -like "*footer-social*") {
        Write-Host ("skip   {0} (already has icons)" -f $_.Name) -ForegroundColor DarkGray
        return
    }
    if ($c -notlike "*footer-legal*") {
        Write-Host ("skip   {0} (no footer-legal block)" -f $_.Name) -ForegroundColor DarkGray
        return
    }
    $idx = $c.IndexOf($anchor)
    if ($idx -lt 0) {
        Write-Host ("skip   {0} (anchor formatting differs - patch manually)" -f $_.Name) -ForegroundColor Yellow
        return
    }
    $c = $c.Substring(0, $idx) + $social + "`n" + $c.Substring($idx)
    Set-Content -Path $_.FullName -Value $c -NoNewline
    Write-Host ("patched {0}" -f $_.Name) -ForegroundColor Green
    $patched++
}

Write-Host ""
Write-Host "$patched page(s) patched. Deploying..." -ForegroundColor Cyan
Set-Location $site
wrangler pages deploy . --project-name=rovenhr
