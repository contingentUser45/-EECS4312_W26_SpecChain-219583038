"""imports or reads your raw dataset; if you scraped, include scraper here"""
from google_play_scraper import reviews, Sort
import os
import json

APP_ID = "com.calm.android"
LANG = "en"
COUNTRY = "ca"
COUNT = 2000  # within required range (1000–5000)


def collect_reviews():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    data_dir = os.path.join(repo_root, "data")
    os.makedirs(data_dir, exist_ok=True)

    out_path = os.path.join(data_dir, "reviews_raw.jsonl")
    meta_path = os.path.join(data_dir, "dataset_metadata.json")

    print(f"Collecting {COUNT} reviews for Calm ({APP_ID})...\n")

    try:
        result, _ = reviews(
            APP_ID,
            lang=LANG,
            country=COUNTRY,
            sort=Sort.NEWEST,
            count=COUNT
        )
    except Exception as e:
        print(f"Something went wrong: {e}")
        return

    print(f"Total reviews fetched: {len(result)}")

    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for i, r in enumerate(result):
            record = {
                "review_id": f"R{i+1:04d}",
                "userName": r.get("userName", ""),
                "score": r.get("score", 0),
                "content": r.get("content", ""),
                "thumbsUpCount": r.get("thumbsUpCount", 0),
                "reviewCreatedVersion": r.get("reviewCreatedVersion", ""),
                "at": str(r.get("at", ""))
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"Saved {written} reviews → {out_path}")

    metadata = {
        "app_name": "Calm",
        "app_id": APP_ID,
        "platform": "Google Play Store",
        "language": LANG,
        "country": COUNTRY,
        "collection_method": "google_play_scraper reviews(), Sort.NEWEST, count=2000",
        "raw_review_count": written,
        "collection_note": "Collected a fixed sample within the required 1,000–5,000 range.",
        "cleaning_steps": [
            "remove duplicates",
            "remove empty reviews",
            "remove very short reviews",
            "remove punctuation",
            "remove special characters and emojis",
            "convert numbers to text",
            "remove extra whitespace",
            "lowercase",
            "remove stop words",
            "lemmatization"
        ]
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Metadata saved → {meta_path}")


if __name__ == "__main__":
    collect_reviews()