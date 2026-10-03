<#
JARVIS cloud feeder: moves the PC collectors (flights, traffic + sports + decisions, metrics, cameras,
balance charges / Search Console / iOS listings) onto a small always-on Google Cloud VM so the hub keeps
updating when the PC sleeps.

What it creates in the project you pass (-Project):
  - service account  jarvis-feeder@<project>.iam.gserviceaccount.com
  - VM               jarvis-feeder, e2-micro, Debian 12, 30 GB standard disk (inside Google's free tier
                     in us-central1 / us-east1 / us-west1; expect well under $5/month for network egress)
And it grants that service account read-only Firestore access (roles/datastore.viewer +
roles/serviceusage.serviceUsageConsumer) on the five business projects. No key files are copied;
the VM signs in as its own service account.

Stays on the PC: the social-posting check (the posting logs live there) and the approved-action
executor (jarvis_hands). The hub alerts you if approved actions sit unpicked for 10 minutes.

Run, from C:\Users\kurvh\jarvis-hub, after `gcloud auth login` as an owner of the project and of the
five Firebase projects:
    powershell -ExecutionPolicy Bypass -File cloud\setup_feeder.ps1 -Project <project-id> -DryRun
    powershell -ExecutionPolicy Bypass -File cloud\setup_feeder.ps1 -Project <project-id>
Undo:
    gcloud compute instances delete jarvis-feeder --zone us-central1-a --project <project-id>
#>
param(
  [Parameter(Mandatory = $true)][string]$Project,
  [string]$Zone = "us-central1-a",
  [switch]$DryRun,
  [switch]$OnlyInstall   # the VM already exists: just copy the files and (re)install
)
$ErrorActionPreference = "Stop"
$gc = "C:\Users\kurvh\google-cloud-sdk\bin\gcloud.cmd"
$here = Split-Path -Parent $PSScriptRoot
$sa = "jarvis-feeder@$Project.iam.gserviceaccount.com"
$firestoreProjects = @("atavia-c29cd", "elizabeth-scott-738e5", "lazo-513ec", "roven-7efea", "lease-reputation")

function G([string[]]$a, [switch]$OkToFail) {
  Write-Host ("> gcloud " + ($a -join " ")) -ForegroundColor Cyan
  if ($DryRun) { return }
  & $gc @a
  if ($LASTEXITCODE -ne 0 -and -not $OkToFail) { throw "gcloud failed: $($a -join ' ')" }
}

if (-not $OnlyInstall) {
G @("services", "enable", "compute.googleapis.com", "iam.googleapis.com", "searchconsole.googleapis.com", "--project", $Project)
G @("iam", "service-accounts", "create", "jarvis-feeder", "--display-name", "JARVIS feeder", "--project", $Project) -OkToFail
$needOwner = @()
foreach ($p in $firestoreProjects) {
  $ok = $true
  foreach ($role in @("roles/datastore.viewer", "roles/serviceusage.serviceUsageConsumer")) {
    G @("projects", "add-iam-policy-binding", $p, "--member", "serviceAccount:$sa", "--role", $role, "--condition", "None", "--quiet") -OkToFail
    if (-not $DryRun -and $LASTEXITCODE -ne 0) { $ok = $false }
  }
  if (-not $ok) { $needOwner += $p; Write-Host "  (no permission on $p from this account; grant it from that project's owner, see the end)" -ForegroundColor Yellow }
}
G @("compute", "instances", "create", "jarvis-feeder", "--project", $Project, "--zone", $Zone,
    "--machine-type", "e2-micro", "--image-family", "debian-12", "--image-project", "debian-cloud",
    "--boot-disk-size", "30GB", "--boot-disk-type", "pd-standard",
    "--service-account", $sa, "--scopes", "cloud-platform,https://www.googleapis.com/auth/webmasters.readonly") -OkToFail
if (-not $DryRun) { Write-Host "Waiting 60 s for the VM to boot..."; Start-Sleep -Seconds 60 }
} else { $needOwner = @() }

$files = @("collect_metrics.py", "collect_traffic.py", "collect_flights.py", "collect_cams.py", "collect_watch.py", ".hub-key", "cloud\install.sh", "cloud\crontab.txt") | ForEach-Object { Join-Path $here $_ }
$sshOpts = @("--project", $Project, "--zone", $Zone, "--strict-host-key-checking=no", "--quiet")
G (@("compute", "ssh", "jarvis-feeder") + $sshOpts + @("--command", "mkdir -p ~/jarvis"))
G (@("compute", "scp") + $files + @("jarvis-feeder:~/jarvis/") + $sshOpts)
G (@("compute", "ssh", "jarvis-feeder") + $sshOpts + @("--command", "bash ~/jarvis/install.sh"))

Write-Host ""
Write-Host "Check the hub's System strip and Watch panel over the next 15 minutes. When the feeds look right," -ForegroundColor Green
Write-Host "turn off the PC copies (the PC keeps the social check and the executor):" -ForegroundColor Green
Write-Host '  Disable-ScheduledTask -TaskName "JARVIS flights","JARVIS traffic","JARVIS metrics","JARVIS cameras"'
Write-Host '  then edit collect_watch.bat so the PC runs:  collect_watch.py --only social'
Write-Host "Search Console: add $sa as a Restricted user on each property (Settings > Users and permissions)."
if ($needOwner.Count) {
  Write-Host ""
  Write-Host "These projects need their owner to grant read access. Sign in as that owner (gcloud auth login) and run:" -ForegroundColor Yellow
  foreach ($p in $needOwner) {
    Write-Host "  gcloud projects add-iam-policy-binding $p --member serviceAccount:$sa --role roles/datastore.viewer --condition None"
    Write-Host "  gcloud projects add-iam-policy-binding $p --member serviceAccount:$sa --role roles/serviceusage.serviceUsageConsumer --condition None"
  }
  Write-Host "Until then the PC keeps feeding those businesses; the hub keeps the last good numbers for a project the server cannot read."
}
