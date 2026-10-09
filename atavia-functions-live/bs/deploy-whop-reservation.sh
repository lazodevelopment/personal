#!/usr/bin/env bash
# Atavia -> Whop, Elizabeth Scott setup (2026-10-08): retainer / PIF total charged at
# reservation through Whop's embedded checkout, booking + contract created server-side
# (whop_webhook backstop), prepaid contract wording. Flips NEW bookings to Whop.
# Existing Zoho bookings keep processor=zoho (their balances still charge through Zoho).
#
# Cloud Shell (info@ataviaweddings.com), after uploading atavia-whop-reservation.zip:
#   cd ~ && unzip -o atavia-whop-reservation.zip -d ~/atv-new && bash ~/atv-new/deploy-whop-reservation.sh
set -e
P=atavia-c29cd
R=us-central1
SRC=~/atv-new
cd ~/bs
gcloud config set project $P >/dev/null

# --- preflight: Whop secrets must exist in this project ------------------------
for s in WHOP_API_KEY WHOP_WEBHOOK_SECRET; do
  if ! gcloud secrets describe $s --project=$P >/dev/null 2>&1; then
    echo ">> Secret $s is missing in $P. Create it, then re-run:"
    echo "   printf '%s' 'VALUE' | gcloud secrets create $s --project=$P --data-file=-"
    exit 1
  fi
done

# --- back up, show what changes, install -----------------------------------------
STAMP=$(date +%Y%m%d-%H%M)
mkdir -p ~/bs-backups/$STAMP
cp -r main.py lib contract ~/bs-backups/$STAMP/ 2>/dev/null || cp -r main.py lib ~/bs-backups/$STAMP/
CG=contract/atavia_contract_generator.py; [ -f contract/atavia_contract_generator.py ] || CG=atavia_contract_generator.py
echo "== diff stat vs what is in ~/bs now (contract generator at $CG)"
{ diff main.py $SRC/main.py | grep -c '^[<>]'; } || true
cp $SRC/main.py main.py
cp $SRC/lib/whop.py lib/whop.py
cp $SRC/lib/emails.py lib/emails.py
cp $SRC/contract/atavia_contract_generator.py $CG
python3 -m py_compile main.py lib/whop.py lib/emails.py $CG && echo "== compiled OK"

WHOP_ACCOUNT_ID=biz_FeVrtPXroSleTG
common="--gen2 --region=$R --runtime=python312 --source=. --allow-unauthenticated"
env="--update-env-vars=PAYMENT_PROCESSOR=whop,WHOP_ACCOUNT_ID=$WHOP_ACCOUNT_ID"
zoho="ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest"
whop="WHOP_API_KEY=WHOP_API_KEY:latest,WHOP_WEBHOOK_SECRET=WHOP_WEBHOOK_SECRET:latest"
pay="$zoho,$whop"
mail="RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest"
sw="SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest"

# booking path first
gcloud functions deploy whop_setup   $common $env --entry-point=whop_setup   --trigger-http --set-secrets=$whop
gcloud functions deploy book_submit  $common $env --entry-point=book_submit  --trigger-http --memory=512MB --set-secrets=$pay,$sw,RESEND_API_KEY=RESEND_API_KEY:latest
gcloud functions deploy whop_webhook $common $env --entry-point=whop_webhook --trigger-http --memory=512MB --set-secrets=$pay,$mail,$sw
gcloud functions deploy signwell_webhook $common $env --entry-point=signwell_webhook --trigger-http --memory=512MB --set-secrets=$pay,$sw,$mail
# everything that charges, links, refunds or reads cards (Whop-aware now)
gcloud functions deploy admin_action $common $env --entry-point=admin_action --trigger-http --set-secrets=$pay,$sw,$mail
gcloud functions deploy gratuity     $common $env --entry-point=gratuity     --trigger-http --set-secrets=$pay,$mail
gcloud functions deploy zoho_webhook $common $env --entry-point=zoho_webhook --trigger-http --memory=512MB --set-secrets=$pay,$mail
# daily job: omitting the trigger flag keeps the existing scheduler trigger
gcloud functions deploy charge_balances --gen2 --region=$R --runtime=python312 --source=. $env --entry-point=charge_balances \
  --set-secrets=$pay,$mail,$sw

echo
echo "== Done. PAYMENT_PROCESSOR=whop. Smoke check (should return a checkout_id, mode=payment, amount=500):"
curl -s -X POST "$(gcloud functions describe whop_setup --region=$R --gen2 --format='value(serviceConfig.uri)')" \
  -H 'Content-Type: application/json' -H 'Origin: https://ataviaweddings.com' \
  -d '{"client_names":"Deploy Check","email":"deploycheck@example.com","package_id":"reverie","payment_option":"standard","event_date":"2027-09-10"}'
echo
echo "Whop webhook URL (must be registered in Whop for payment.succeeded + payment.failed):"
gcloud functions describe whop_webhook --region=$R --gen2 --format='value(serviceConfig.uri)'
