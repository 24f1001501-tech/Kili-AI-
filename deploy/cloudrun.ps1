# Deploy the Kili AI backend to Google Cloud Run. Run this yourself; sign-in happens in your browser.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$repo = Split-Path $here -Parent   # deploy straight from the repo (Dockerfile at its root)
$region = "asia-south1"   # Mumbai
$service = "kili-ai"

function Find-GCloud {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"),
        "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command gcloud -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$gcloud = Find-GCloud
if (-not $gcloud) {
    Write-Host "Installing the Google Cloud CLI..." -ForegroundColor Cyan
    winget install --id Google.CloudSDK -e --accept-package-agreements --accept-source-agreements
    $gcloud = Find-GCloud
    if (-not $gcloud) { throw "Google Cloud CLI not found after install. Open a new terminal and run this script again." }
}
Write-Host "Using $gcloud"

# 1. Sign in (browser)
$account = & $gcloud auth list --filter=status:ACTIVE --format="value(account)"
if (-not $account) { & $gcloud auth login; $account = & $gcloud auth list --filter=status:ACTIVE --format="value(account)" }
Write-Host "Signed in as $account" -ForegroundColor Green

# 2. Project
$projFile = Join-Path $here "gcp_project.txt"
if (Test-Path $projFile) { $proj = (Get-Content $projFile -Raw).Trim() }
else {
    $proj = "kili-ai-" + (Get-Random -Minimum 100000 -Maximum 999999)
    & $gcloud projects create $proj --name="Kili AI"
    Set-Content $projFile $proj
}
& $gcloud config set project $proj | Out-Null
Write-Host "Project: $proj" -ForegroundColor Green

# 3. Billing (required by Cloud Run even within the free tier)
$enabled = & $gcloud billing projects describe $proj --format="value(billingEnabled)"
while ($enabled -ne "True") {
    $accounts = @(& $gcloud billing accounts list --filter="open=true" --format="value(name)")
    if ($accounts.Count -eq 0) {
        Write-Host "No billing account found. Create one (needs a card; the free tier covers a demo):" -ForegroundColor Yellow
        Write-Host "  https://console.cloud.google.com/billing/create"
        Read-Host "Press Enter when it's created"
        continue
    }
    $acct = $accounts[0]
    if ($accounts.Count -gt 1) {
        for ($i = 0; $i -lt $accounts.Count; $i++) { Write-Host "  [$i] $($accounts[$i])" }
        $acct = $accounts[[int](Read-Host "Which billing account number")]
    }
    & $gcloud billing projects link $proj --billing-account=$acct | Out-Null
    $enabled = & $gcloud billing projects describe $proj --format="value(billingEnabled)"
}
Write-Host "Billing linked." -ForegroundColor Green

# 4. Services and build settings
& $gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
& $gcloud config set builds/timeout 3600 | Out-Null

# 5. Sarvam key from the local .env (not printed)
$envFile = Join-Path $repo "backend\.env"
$keyLine = Get-Content $envFile | Where-Object { $_ -like "SARVAM_API_KEY=*" } | Select-Object -First 1
$sarvam = $keyLine.Substring("SARVAM_API_KEY=".Length).Trim()

# 6. Build in Google's cloud and deploy (10-20 minutes the first time)
Write-Host "Building and deploying (10-20 minutes the first time)..." -ForegroundColor Cyan
& $gcloud run deploy $service --source $repo --region $region --allow-unauthenticated `
    --port 7860 --memory 4Gi --cpu 2 --min-instances 0 --max-instances 1 --concurrency 20 --timeout 120 `
    --set-env-vars "ALLOW_PROFILE_LIST=0,SARVAM_API_KEY=$sarvam" --quiet

$url = & $gcloud run services describe $service --region $region --format="value(status.url)"
Set-Content (Join-Path $here "cloudrun_url.txt") $url
Write-Host "`nBackend live at: $url" -ForegroundColor Green
Write-Host "Done. Tell Claude it finished."
