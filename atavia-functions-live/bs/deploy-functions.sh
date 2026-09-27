#!/usr/bin/env bash
# Run in Cloud Shell from ~/bs after replacing main.py.  Deploys the 3 new
# functions and re-deploys charge_balances (new 7 AM schedule + digest).
set -e
cd ~/bs
cp main.py main.py.v13.bak 2>/dev/null || true
R=us-central1
common="--gen2 --region=$R --runtime=python312 --source=. --allow-unauthenticated"

gcloud functions deploy admin_action $common --entry-point=admin_action --trigger-http \
  --set-secrets=ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest

gcloud functions deploy ical_feed $common --entry-point=ical_feed --trigger-http \
  --set-secrets=GRATUITY_SECRET=GRATUITY_SECRET:latest

gcloud functions deploy inquiry_webhook $common --entry-point=inquiry_webhook --trigger-http \
  --set-secrets=RESEND_API_KEY=RESEND_API_KEY:latest

# daily job: now 07:00 America/Phoenix, ends with the digest email.
# Same command you used on Sep 5 — omitting the trigger flag keeps the existing scheduler trigger.
gcloud functions deploy charge_balances --gen2 --region=$R --runtime=python312 --source=. --entry-point=charge_balances \
  --set-secrets=ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest
# The schedule itself lives in Cloud Scheduler; move it to 7 AM Phoenix:
JOB=$(gcloud scheduler jobs list --location=$R --format='value(name)' | grep -i charge_balances | head -1)
[ -n "$JOB" ] && gcloud scheduler jobs update pubsub "$JOB" --location=$R --schedule="0 7 * * *" --time-zone="America/Phoenix" || echo ">> couldn't find the scheduler job; set it to 07:00 America/Phoenix in Cloud Scheduler by hand"

echo "Done. URLs:"
gcloud functions describe admin_action --region=$R --gen2 --format='value(serviceConfig.uri)'
gcloud functions describe ical_feed --region=$R --gen2 --format='value(serviceConfig.uri)'
gcloud functions describe inquiry_webhook --region=$R --gen2 --format='value(serviceConfig.uri)'
