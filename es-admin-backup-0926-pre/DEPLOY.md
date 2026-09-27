# Elizabeth Scott admin dashboard — deploy (PowerShell, wrangler as the wedding-brands Cloudflare account)

Expand-Archive "$env:USERPROFILE\Downloads\es-admin.zip" -DestinationPath "C:\Users\kurvh" -Force
cd C:\Users\kurvh\es-admin
npx wrangler pages project create elizabethscott-admin --production-branch=main
npx wrangler pages deploy . --project-name=elizabethscott-admin
# then Cloudflare → Workers & Pages → elizabethscott-admin → Custom domains → admin.elizabethscottweddings.com

# Site: visitor tracking (optional but needed for the Visitors page)
Copy-Item "$env:USERPROFILE\Downloads\es-site\assets\js\esw-track.js" "C:\Users\kurvh\es-site\assets\js\esw-track.js" -Force
New-Item -ItemType Directory -Force "C:\Users\kurvh\es-site\functions\api" | Out-Null
Copy-Item "$env:USERPROFILE\Downloads\es-site\functions_api_geo.js" "C:\Users\kurvh\es-site\functions\api\geo.js" -Force
# add   <script src="/assets/js/esw-track.js" defer></script>   after the site.js tag in the page shell (and _src\build.py if ES uses a generator), then deploy the site as usual.
