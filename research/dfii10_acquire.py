"""Download DFII10 historical vintages from the public ALFRED form.

The receipt records the request and response even when a download fails.
"""
from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import zipfile

URL = "https://alfred.stlouisfed.org/series/downloaddata?seid=DFII10"
START, END = "2019-01-01", "2026-09-19"


class VintageOptions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.dates = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "select" and values.get("id") == "form_selected_vintage_dates":
            self.inside = True
        if tag == "option" and self.inside:
            value = values.get("value", "")
            try:
                date.fromisoformat(value)
            except ValueError:
                return
            if START <= value <= END:
                self.dates.append(value)

    def handle_endtag(self, tag):
        if tag == "select":
            self.inside = False


def retrieve(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    receipt = {"url": URL, "observation_start": START,
               "observation_end": END, "file_type": "3", "format": "csv",
               "attempts": []}
    headers = {"User-Agent": "coinquant-personal-research/1.0",
               "Accept": "text/html,application/zip,*/*"}
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    try:
        with opener.open(urllib.request.Request(URL, headers=headers), timeout=35) as response:
            html = response.read().decode("utf-8")
        vintage = VintageOptions()
        vintage.feed(html)
        dates = vintage.dates
        if not dates:
            raise ValueError("no qualifying vintage date in official form")
        receipt["vintages"] = {"count": len(dates), "first": dates[0],
                                "last": dates[-1], "sha256": sha256(" ".join(dates).encode()).hexdigest()}
        common = [("form[units]", "lin"),
                  ("form[obs_start_date]", START),
                  ("form[obs_end_date]", END),
                  ("form[entered_vintage_dates]", ""),
                  ("form[file_type]", "3"),
                  ("form[file_format]", "csv"),
                  ("form[download_data]", "Download data")]
        for label, selected, limit in (
            ("single", [next(d for d in dates if d >= "2020-01-02")], 60),
            ("all", dates, 210),
        ):
            params = common + [("form[selected_vintage_dates][]", d) for d in selected]
            body = urllib.parse.urlencode(params).encode()
            record = {"label": label, "selected_count": len(selected),
                      "request_sha256": sha256(body).hexdigest(),
                      "request_bytes": len(body)}
            receipt["attempts"].append(record)
            try:
                request = urllib.request.Request(URL, data=body, headers=headers, method="POST")
                with opener.open(request, timeout=limit) as response:
                    payload = response.read()
                    record["http_status"] = response.status
                    record["content_type"] = response.headers.get("Content-Type")
                    record["final_url"] = response.geturl()
                    record["response_bytes"] = len(payload)
                    record["response_sha256"] = sha256(payload).hexdigest()
                if not payload.startswith(b"PK\x03\x04"):
                    record["error"] = "non-ZIP response: " + payload[:180].decode("utf-8", "replace")
                    if label == "single":
                        (out / "DFII10_ALFRED_single_response.html").write_bytes(payload)
                    if label == "single":
                        break
                    continue
                path = out / f"DFII10_ALFRED_{label}.zip"
                path.write_bytes(payload)
                with zipfile.ZipFile(path) as archive:
                    record["members"] = archive.namelist()
                record["path"] = path.name
            except (OSError, ValueError, urllib.error.HTTPError) as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                if label == "single":
                    break
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    (out / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    import sys
    outcome = retrieve(sys.argv[1])
    print(json.dumps({key: outcome.get(key) for key in ("vintages", "attempts", "error")}))
