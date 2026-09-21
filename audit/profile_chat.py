"""Optional real chat timing. Sends two synthetic prompts; never prints bodies/keys."""
import argparse
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as meteor
from test_hardening import Form

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--live", action="store_true", help="Use the configured free API quota")
if not parser.parse_args().live:
    parser.error("Use --live explicitly to send the synthetic chat requests.")

client = meteor.app.test_client()
post, read = meteor.http.post, meteor.read_provider_json
results = []
for prompt in ("Balas hanya: Halo Meteor.", "Berapa 2 + 2? Jawab singkat."):
    attempts, body_times = [], []

    def timed_post(*args, **kwargs):
        start, status = time.perf_counter(), "network_error"
        try:
            response = post(*args, **kwargs)
            status = response.status_code
            return response
        finally:
            attempts.append({"status": status, "headers_ms": (time.perf_counter() - start) * 1000})

    def timed_read(*args, **kwargs):
        start = time.perf_counter()
        try:
            return read(*args, **kwargs)
        finally:
            body_times.append((time.perf_counter() - start) * 1000)

    form = Form(client.get("/").get_data(as_text=True))
    form.fields["message"] = prompt
    start = time.perf_counter()
    with patch.object(meteor.http, "post", side_effect=timed_post), patch.object(meteor, "read_provider_json", side_effect=timed_read):
        result = client.post("/", data=form.fields, content_type=form.encoding)
    elapsed = (time.perf_counter() - start) * 1000
    upstream = sum(row["headers_ms"] for row in attempts) + sum(body_times)
    results.append({"http_status": result.status_code, "total_ms": round(elapsed, 2),
                    "provider_io_and_decode_ms": round(upstream, 2), "other_ms": round(elapsed - upstream, 2),
                    "attempts": [{"status": row["status"], "headers_ms": round(row["headers_ms"], 2)} for row in attempts],
                    "body_decode_ms": [round(value, 2) for value in body_times]})
meteor.http.close()
print(json.dumps(results, indent=2))
