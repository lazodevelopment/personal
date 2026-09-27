<#
  set_secret.ps1 - JC-LAZO-SECRET-0916-001

  Put a secret into .env without it ever appearing in the terminal scrollback,
  in a chat window, or in PowerShell's command history.

  Usage (from anywhere):
      powershell -ExecutionPolicy Bypass -File C:\Users\kurvh\lazo-directory\deploy\set_secret.ps1 CF_API_TOKEN

  The value is read with -AsSecureString, so what you paste is masked as you
  paste it. The line is replaced if the key already exists, appended if not.
  Everything else in .env is left exactly as it was, and the file is written
  UTF-8 with NO byte-order mark and LF endings - a BOM would attach itself to
  the first variable name and python-dotenv would read it as a different key.
#>
param(
  [Parameter(Mandatory = $true)][string]$Name,
  [string]$EnvPath = 'C:\Users\kurvh\lazo-directory\.env'
)

if ($Name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
  Write-Host "Not a valid variable name: $Name" -ForegroundColor Red; exit 1
}
if (-not (Test-Path $EnvPath)) {
  Write-Host "No .env at $EnvPath" -ForegroundColor Red; exit 1
}

$secure = Read-Host "Paste the value for $Name (input is hidden)" -AsSecureString
$bstr   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try   { $value = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }

$value = $value.Trim()
if ([string]::IsNullOrWhiteSpace($value)) {
  Write-Host "Nothing pasted - .env unchanged." -ForegroundColor Yellow; exit 1
}
if ($value -match '[\r\n]') {
  Write-Host "That value contains a line break - .env unchanged." -ForegroundColor Red; exit 1
}

# back up once per day, so a mistake is always recoverable
$bak = "$EnvPath.bak-" + (Get-Date -Format 'yyyyMMdd')
if (-not (Test-Path $bak)) { Copy-Item $EnvPath $bak }

$lines   = [IO.File]::ReadAllText($EnvPath) -split "`r?`n"
$existed = $false
$out = foreach ($l in $lines) {
  if ($l -match "^\s*$([regex]::Escape($Name))\s*=") { $existed = $true; "$Name=$value" }
  else { $l }
}
if (-not $existed) { $out = @($out | Where-Object { $_ -ne '' }) + "$Name=$value" }

$text = ($out -join "`n").TrimEnd("`n") + "`n"
[IO.File]::WriteAllText($EnvPath, $text, (New-Object Text.UTF8Encoding $false))

$verb = if ($existed) { 'replaced' } else { 'added' }
Write-Host "$Name $verb in .env ($($value.Length) characters). Value not shown." -ForegroundColor Green
Write-Host "Backup: $bak"
