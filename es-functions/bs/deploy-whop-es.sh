#!/usr/bin/env bash
# Elizabeth Scott: deploy the Whop-capable build (ported from Atavia v11, 2026-10-05).
# Run in the danbrenmedia@gmail.com Cloud Shell from ~/es-deploy/functions after
# copying in: main.py, lib/whop.py, and running patch_es_emails_whop.py.
# ALWAYS --project=elizabeth-scott-738e5 here: that shell's default project is wrong.
#
# SAFE BY DEFAULT: PAYMENT_PROCESSOR stays "zoho" unless you pass whop as $1.
#   ./deploy-whop-es.sh          # deploy, new bookings stay on Zoho
#   ./deploy-whop-es.sh whop     # deploy AND flip new bookings to Whop
#
# One-time prerequisites (Secret Manager, elizabeth-scott-738e5):
#   printf '%s' 'apik_SAME_KEY_AS_ATAVIA'   | gcloud secrets create WHOP_API_KEY        --data-file=- --project=elizabeth-scott-738e5
#   printf '%s' 'ws_SECRET_OF_THE_ES_WEBHOOK' | gcloud secrets create WHOP_WEBHOOK_SECRET --data-file=- --project=elizabeth-scott-738e5
#   (grant the runtime service account Secret Manager Secret Accessor on both)
# The ES webhook is a SECOND webhook in the same Whop company, pointed at the
# whop_webhook URL printed at the end, events payment.succeeded + payment.failed.
set -e
cd ~/es-deploy/functions
cp main.py main.py.pre-whop.bak 2>/dev/null || true

PROC="${1:-zoho}"
P=elizabeth-scott-738e5
WHOP_ACCOUNT_ID="${WHOP_ACCOUNT_ID:-biz_FeVrtPXroSleTG}"   # same Whop company as Atavia (Danbren Media)

R=us-central1
common="--gen2 --region=$R --runtime=python312 --source=. --allow-unauthenticated --project=$P"
env="--update-env-vars=PAYMENT_PROCESSOR=$PROC,WHOP_ACCOUNT_ID=$WHOP_ACCOUNT_ID"
zoho="ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest"
whop="WHOP_API_KEY=WHOP_API_KEY:latest,WHOP_WEBHOOK_SECRET=WHOP_WEBHOOK_SECRET:latest"
pay="$zoho,$whop"

gcloud functions deploy whop_setup   $common $env --entry-point=whop_setup   --trigger-http --set-secrets=$whop
gcloud functions deploy whop_webhook $common $env --entry-point=whop_webhook --trigger-http \
  --set-secrets=$whop,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest

gcloud functions deploy book_submit $common $env --entry-point=book_submit --trigger-http --memory=512MB \
  --set-secrets=$pay,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest
gcloud functions deploy signwell_webhook $common $env --entry-point=signwell_webhook --trigger-http --memory=512MB \
  --set-secrets=$pay,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest
gcloud functions deploy gratuity $common $env --entry-point=gratuity --trigger-http \
  --set-secrets=$pay,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest
gcloud functions deploy admin_action $common $env --entry-point=admin_action --trigger-http \
  --set-secrets=$pay,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest
# daily job: omitting the trigger flag keeps the existing scheduler trigger. ES timeout is 60s; raise it while we're here.
gcloud functions deploy charge_balances --gen2 --region=$R --runtime=python312 --source=. --project=$P $env --entry-point=charge_balances --timeout=540s \
  --set-secrets=$pay,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest
gcloud functions deploy zoho_session $common $env --entry-point=zoho_session --trigger-http --set-secrets=$zoho
gcloud functions deploy zoho_webhook $common $env --entry-point=zoho_webhook --trigger-http --memory=512MB \
  --set-secrets=$pay,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest

echo "Done. PAYMENT_PROCESSOR=$PROC. Register this URL as a Whop webhook (payment.succeeded, payment.failed):"
gcloud functions describe whop_webhook --region=$R --gen2 --project=$P --format='value(serviceConfig.uri)'
echo "Remember: es-site /book page PROCESSOR const must match ($PROC)."
