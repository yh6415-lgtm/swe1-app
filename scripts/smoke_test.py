"""Verify that the deployed polls index is reachable after a Travis deployment."""

import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

URL = "http://swe1-app-287872994760.us-east-1.elasticbeanstalk.com/polls/"


def main():
    for attempt in range(12):
        try:
            with urlopen(URL, timeout=30) as response:
                html = response.read().decode("utf-8")
                if response.status == 200 and "Latest polls" in html:
                    print(f"Deployment verified: {URL}")
                    return
        except (HTTPError, URLError, TimeoutError):
            pass
        if attempt < 11:
            time.sleep(10)
    raise SystemExit(f"Deployment smoke test failed: {URL}")


if __name__ == "__main__":
    main()
