"""JARVIS wake: when the hub's alarm fires, open JARVIS on this PC in a kiosk window that is allowed to autoplay,
so the morning brief and then the radio come out of the PC speakers even if JARVIS wasn't open.

Runs every minute from Task Scheduler ("JARVIS wake", hidden). It asks the hub once a minute whether the alarm is due;
the hub answers yes exactly once per alarm. The kiosk uses its own Chrome profile (JarvisKiosk) so Chrome honours the
autoplay flag; the first time, unlock JARVIS in that window with the access key (the cookie then persists).
"""
import json, os, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()
CHROME = next((p for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")) if os.path.exists(p)), None)
PROFILE = os.path.expandvars(r"%LOCALAPPDATA%\JarvisKiosk")


def main():
    req = urllib.request.Request(HUB + "/api/alarm/due", headers={"x-hub-key": KEY, "User-Agent": "Mozilla/5.0 (JARVIS feeder)"})
    d = json.load(urllib.request.urlopen(req, timeout=20))
    if not d.get("due"):
        return
    if not CHROME:
        print("Chrome not found; cannot open the wake window"); return
    args = [CHROME, f"--user-data-dir={PROFILE}", "--kiosk", "--autoplay-policy=no-user-gesture-required", "--no-first-run", "--disable-session-crashed-bubble", HUB + "/#wake"]
    subprocess.Popen(args, close_fds=True)
    print("wake window opened")


if __name__ == "__main__":
    main()
