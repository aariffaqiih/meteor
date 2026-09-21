"""Reproducible local profile; --network measures metadata GET transport, not inference."""
import argparse
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser()
parser.add_argument("--baseline", action="store_true")
parser.add_argument("--network", action="store_true")
args = parser.parse_args()
source = ROOT / "audit/baseline/app.py" if args.baseline else ROOT / "app.py"
spec = importlib.util.spec_from_file_location("measured_app", source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.app.template_folder = str(source.parent if args.baseline else ROOT / "templates")


def measure(function, repeats=200):
    function()  # Warm template/bytecode caches.
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        function()
        samples.append((time.perf_counter() - start) * 1000)
    return {"n": repeats, "median_ms": round(statistics.median(samples), 4),
            "p95_ms": round(sorted(samples)[int(.95 * (len(samples) - 1))], 4)}


history = [{"role": role, "content": "a" * 600}
           for _ in range(10) for role in ("user", "assistant")]
raw = json.dumps(history)
client = module.app.test_client()
result = {
    "source": "baseline" if args.baseline else "hardened",
    "local": {
        "GET_empty_page": measure(lambda: client.get("/")),
        "read_history_12000_chars_20_messages": measure(lambda: module.read_history(raw)),
        "trim_history_12000_plus_4000": measure(lambda: module.trim_history(history, 4000)),
        "identity_filter_8000_chars": measure(lambda: module.protect_identity("a" * 8000)),
    },
}
with module.app.test_request_context("/"):
    module.app.preprocess_request()
    result["local"]["render_12000_chars_20_messages"] = measure(
        lambda: module.render_template("index.html", history=history, error=None, message="", edit_index=None))

if args.network:
    import requests
    from dotenv import dotenv_values
    config = dotenv_values(ROOT / ".env")
    result["network"] = {}
    for provider, prefix, url in (
        ("openrouter", "sk-or-", "https://openrouter.ai/api/v1/key"),
        ("groq", "gsk_", "https://api.groq.com/openai/v1/models"),
    ):
        key = next(value for name, value in config.items() if name.startswith("API_KEY_") and value.startswith(prefix))
        samples = {"fresh": [], "pooled": []}
        statuses = {"fresh": [], "pooled": []}
        with requests.Session() as session:
            for order in (("fresh", "pooled"), ("pooled", "fresh"), ("fresh", "pooled")):
                for mode in order:
                    start = time.perf_counter()
                    try:
                        transport = session if mode == "pooled" else requests
                        response = transport.get(url, headers={"Authorization": "Bearer " + key},
                                                 timeout=(5, 20), allow_redirects=False)
                        statuses[mode].append(response.status_code)
                        response.close()
                    except requests.RequestException:
                        statuses[mode].append("network_error")
                    samples[mode].append(round((time.perf_counter() - start) * 1000, 2))
        result["network"][provider] = {"samples_ms": samples, "statuses": statuses,
                                         "median_ms": {k: round(statistics.median(v), 2) for k, v in samples.items()}}

print(json.dumps(result, indent=2))
