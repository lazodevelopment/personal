"""Release C:/Users/kurvh/lazo-directory/firestore.rules to lazo-513ec (Firebase Rules REST API, ADC)."""
import google.auth, google.auth.transport.requests, requests, difflib, sys
P = "lazo-513ec"
cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
cred.refresh(google.auth.transport.requests.Request())
H = {"Authorization": "Bearer " + cred.token, "x-goog-user-project": P}
B = "https://firebaserules.googleapis.com/v1/projects/" + P
rel = requests.get(B + "/releases/cloud.firestore", headers=H).json()
live = requests.get("https://firebaserules.googleapis.com/v1/" + rel["rulesetName"], headers=H).json()["source"]["files"][0]["content"]
src = open(r"C:\Users\kurvh\lazo-directory\firestore.rules", encoding="utf-8").read()
d = [l for l in difflib.unified_diff(live.replace("\r", "").splitlines(), src.replace("\r", "").splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
print("\n".join(d))
if any(l.startswith("-") and "Build ID" not in l and "heardAbout" not in l and "'legalEntityName']);" not in l for l in d):
    sys.exit("unexpected removals vs live - stopping")
rs = requests.post(B + "/rulesets", headers=H, json={"source": {"files": [{"name": "firestore.rules", "content": src}]}})
print("ruleset", rs.status_code, rs.text[:300] if rs.status_code != 200 else rs.json()["name"])
rs.raise_for_status()
up = requests.patch(B + "/releases/cloud.firestore", headers=H,
                    json={"release": {"name": "projects/%s/releases/cloud.firestore" % P, "rulesetName": rs.json()["name"]}})
print("release", up.status_code, up.text[:300])
