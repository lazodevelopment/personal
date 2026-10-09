#!/usr/bin/env bash
# Deploy the Whop-capable build of the Atavia functions (v11, 2026-10-03).
# Run in Cloud Shell from ~/bs after replacing main.py, lib/whop.py, lib/emails.py.
#
# SAFE BY DEFAULT: PAYMENT_PROCESSOR stays "zoho" unless you pass whop as $1.
# Existing bookings keep their own `processor` field either way, so a flip
# only changes which processor NEW bookings land on.
#
#   ./deploy-whop.sh          # deploy, new bookings stay on Zoho
#   ./deploy-whop.sh whop     # deploy AND flip new bookings to Whop
#
# One-time prerequisites (Secret Manager, same project):
#   printf '%s' 'YOUR_WHOP_API_KEY'        | gcloud secrets create WHOP_API_KEY        --data-file=-
#   printf '%s' 'ws_YOUR_WEBHOOK_SECRET'   | gcloud secrets create WHOP_WEBHOOK_SECRET --data-file=-
#   (grant the functions' runtime service account Secret Manager Secret Accessor on both)
# And set WHOP_ACCOUNT_ID below to the biz_... id from whop.com/dashboard.
# Then register the webhook at whop.com/dashboard/developer > Webhooks:
#   URL = the whop_webhook URL printed at the end; events = payment.succeeded, payment.failed
set -e
cd ~/bs
cp main.py main.py.v11.bak 2>/dev/null || true

PROC="${1:-zoho}"
WHOP_ACCOUNT_ID="${WHOP_ACCOUNT_ID:-biz_FeVrtPXroSleTG}"   # Atavia Weddings (Danbren Media) on Whop
if [ -z "$WHOP_ACCOUNT_ID" ]; then
  echo ">> WHOP_ACCOUNT_ID is empty. export WHOP_ACCOUNT_ID=biz_xxx and re-run."; exit 1
fi

R=us-central1
common="--gen2 --region=$R --runtime=python312 --source=. --allow-unauthenticated"
env="--update-env-vars=PAYMENT_PROCESSOR=$PROC,WHOP_ACCOUNT_ID=$WHOP_ACCOUNT_ID"
zoho="ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest"
whop="WHOP_API_KEY=WHOP_API_KEY:latest,WHOP_WEBHOOK_SECRET=WHOP_WEBHOOK_SECRET:latest"
pay="$zoho,$whop"

# --- new ---------------------------------------------------------------------
gcloud functions deploy whop_setup   $common $env --entry-point=whop_setup   --trigger-http --set-secrets=$whop
gcloud functions deploy whop_webhook $common $env --entry-point=whop_webhook --trigger-http \
  --set-secrets=$whop,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest

# --- every function that charges, links, refunds or verifies a card ----------
gcloud functions deploy book_submit $common $env --entry-point=book_submit --trigger-http --memory=512MB \
  --set-secrets=$pay,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest
gcloud functions deploy signwell_webhook $common $env --entry-point=signwell_webhook --trigger-http --memory=512MB \
  --set-secrets=$pay,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest
gcloud functions deploy gratuity $common $env --entry-point=gratuity --trigger-http \
  --set-secrets=$pay,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest
gcloud functions deploy admin_action $common $env --entry-point=admin_action --trigger-http \
  --set-secrets=$pay,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest
# daily job: omitting the trigger flag keeps the existing scheduler trigger.
gcloud functions deploy charge_balances --gen2 --region=$R --runtime=python312 --source=. $env --entry-point=charge_balances \
  --set-secrets=$pay,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest
# zoho_session / zoho_webhook are unchanged in behaviour; redeploy so they pick up the shared helpers.
gcloud functions deploy zoho_session $common $env --entry-point=zoho_session --trigger-http --set-secrets=$zoho
gcloud functions deploy zoho_webhook $common $env --entry-point=zoho_webhook --trigger-http --memory=512MB \
  --set-secrets=$pay,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest

echo "Done. PAYMENT_PROCESSOR=$PROC. Register this URL as the Whop webhook (payment.succeeded, payment.failed):"
gcloud functions describe whop_webhook --region=$R --gen2 --format='value(serviceConfig.uri)'
echo "Remember: /book page PROCESSOR const must match ($PROC) and WHOP_ACCOUNT_ID must be filled in there too."
