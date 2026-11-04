import json
from pathlib import Path

import httpx


API_URL = "http://localhost:8000/api"
DATASET = Path("docs/evaluation_dataset.json")


def in_range(value: float, expected: list[float]) -> bool:
    return expected[0] <= value <= expected[1]


def main() -> None:
    cases = json.loads(DATASET.read_text())
    precision_hits = 0
    reciprocal_sum = 0.0
    timestamp_hits = 0
    unsupported_rejections = 0
    unsupported_total = 0
    with httpx.Client(timeout=30) as client:
        for case in cases:
            response = client.post(f"{API_URL}/ask", json={"question": case["question"], "video_ids": []})
            response.raise_for_status()
            payload = response.json()
            if case.get("unsupported"):
                unsupported_total += 1
                unsupported_rejections += int(payload["grounded"] is False)
                continue
            sources = payload["sources"]
            for index, source in enumerate(sources, start=1):
                if source["video_title"] == case["expected_video"]:
                    precision_hits += 1 if index == 1 else 0
                    reciprocal_sum += 1 / index
                    timestamp_hits += int(in_range(source["start_time"], case["expected_timestamp_range"]))
                    break
    supported_total = max(1, len([c for c in cases if not c.get("unsupported")]))
    print(
        json.dumps(
            {
                "precision_at_1": precision_hits / supported_total,
                "mrr": reciprocal_sum / supported_total,
                "timestamp_accuracy": timestamp_hits / supported_total,
                "unsupported_rejection_rate": unsupported_rejections / max(1, unsupported_total),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

