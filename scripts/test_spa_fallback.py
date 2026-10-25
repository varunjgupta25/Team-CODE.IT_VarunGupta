import urllib.request
import subprocess
import time
import sys

def test_spa_deep_link():
    print("Starting Vite preview server on port 4176...")
    proc = subprocess.Popen(
        ["npx.cmd", "vite", "preview", "--port", "4176"],
        cwd="frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(3)
    try:
        url = "http://localhost:4176/customer/status/123"
        print(f"Requesting deep link: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "SPATestClient/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8")
            print(f"HTTP Status: {status}")
            has_root = '<div id="root">' in body
            has_vite = "index-" in body
            print(f"Contains <div id=\"root\">: {has_root}")
            print(f"Contains bundled SPA assets: {has_vite}")
            if status == 200 and has_root:
                print("SUCCESS: SPA fallback served index.html correctly on deep link!")
                return 0
            else:
                print("FAILED: SPA fallback failed.")
                return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    sys.exit(test_spa_deep_link())
