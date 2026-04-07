"""automated persona generation pipeline"""
import json, os, sys, time, random
from groq import Groq, RateLimitError, APIError

num_clusters = 10
batch_size = 50
model_id = "meta-llama/llama-4-scout-17b-16e-instruct"

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = os.path.join(root, ".env")

print("Checking for GROQ_API_KEY...")
key = os.environ.get("GROQ_API_KEY")

if not key and os.path.exists(env):
    print(" Checking .env file...")
    with open(env, encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) < 2:
        sys.exit("Missing API key on line 2 of .env")

    key = lines[1].strip().strip('"').strip("'")

if not key:
    print("\nGROQ_API_KEY not found.")
    key_input = input("Enter your Groq API key: ").strip()
    if key_input:
        key = key_input
    else:
        sys.exit("No API key provided.")

if not key.startswith("gsk_"):
    sys.exit("Invalid Groq API key format")

print(" API key found.")

sys_prompt = "return only valid json."

commands = (
    "create a persona for group {group_id} ({review_count} reviews).\n\n"
    "{samples}\n\n"
    "return json with: persona_id, name, age_range, occupation, context, "
    "goals, pain_points, tech_comfort, quote, group_theme."
)

control_commands = (
    f"you must return only valid json.\n\n"
    f"group reviews into exactly {num_clusters} groups.\n"
    "each review must appear in exactly one group.\n\n"
    '{ "groups": [ { "group_id": "g1", "theme": "...", "review_ids": ["..."] } ] }'
)


def load_reviews():
    path = os.path.join(root, "data", "reviews_clean.jsonl")
    if not os.path.exists(path):
        sys.exit("missing reviews_clean.jsonl")
    out = []
    for l in open(path, encoding="utf-8"):
        if not l.strip():
            continue
        r = json.loads(l)
        txt = r.get("content", "")
        out.append({"review_id": str(r.get("review_id")), "original": txt, "cleaned": txt})
    return out


def rate_limited_call(client, messages, temperature=0.0, max_retries=8):
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            return json.loads(res.choices[0].message.content)
        except RateLimitError as e:
            retry_after = None
            if hasattr(e, 'response') and e.response is not None:
                retry_after = e.response.headers.get("retry-after")
            if retry_after:
                wait = int(retry_after) + random.uniform(0.5, 2.0)
                print(f"Rate limit hit. Waiting {wait:.1f}s (retry-after)...")
            else:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limit hit (attempt {attempt+1}/{max_retries}). Waiting {wait:.1f}s...")
            time.sleep(wait)
            continue
        except (APIError, json.JSONDecodeError) as e:
            print(f"API/JSON error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt + random.uniform(0, 1))
            continue
        except Exception as e:
            print(f"Unexpected error (attempt {attempt+1}): {e}")
            time.sleep(3)
            continue
    print("Max retries exceeded. Using fallback.")
    return None


def call_group(client, batch):
    txt = "\n".join(f'[{r["review_id"]}] {r["cleaned"][:200]}' for r in batch)
    messages = [
        {"role": "system", "content": control_commands},
        {"role": "user", "content": txt}
    ]
    result = rate_limited_call(client, messages, temperature=0)
    if result is None:
        return {"groups": []}
    return result


def semantic_group(client, reviews):
    by_id = {r["review_id"]: r for r in reviews}
    buckets = {}
    total = (len(reviews) + batch_size - 1) // batch_size
    start = time.time()

    for i, s in enumerate(range(0, len(reviews), batch_size), 1):
        batch = reviews[s:s + batch_size]
        res = call_group(client, batch)
        groups_out = res.get("groups", []) if isinstance(res, dict) else []

        for idx, g in enumerate(groups_out):
            if not isinstance(g, dict):
                continue
            gid = g.get("group_id", f"g{idx+1}")
            buckets.setdefault(gid, {"theme": g.get("theme", gid), "reviews": []})
            for rid in g.get("review_ids", []):
                r = by_id.get(str(rid))
                if r and r not in buckets[gid]["reviews"]:
                    buckets[gid]["reviews"].append(r)

        avg = (time.time() - start) / i
        eta = avg * (total - i)
        print(f"Grouping batch {i}/{total} | ETA: {eta:.1f}s")

    groups = []
    for i, (gid, b) in enumerate(sorted(buckets.items()), 1):
        cluster = b["reviews"]
        groups.append({
            "group_id": f"A{i}",
            "group_theme": b["theme"],
            "review_ids": [r["review_id"] for r in cluster],
            "review_count": len(cluster),
            "representative_quotes": [r["original"][:120] for r in cluster[:8]],
        })
    return groups


def enforce_min(groups, min_size=10):
    groups = groups[:5]
    while True:
        groups.sort(key=lambda g: g["review_count"])
        small, big = groups[0], groups[-1]
        if small["review_count"] >= min_size or big["review_count"] <= min_size:
            break
        rid = big["review_ids"].pop()
        small["review_ids"].append(rid)
        small["review_count"] += 1
        big["review_count"] -= 1
    return groups


def make_persona(client, g, i):
    samples = "\n".join(f"- {q}" for q in g["representative_quotes"])
    prompt = commands.format(
        group_id=g["group_id"],
        review_count=g["review_count"],
        samples=samples
    )
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": prompt}
    ]
    result = rate_limited_call(client, messages, temperature=0.3)
    if result is None:
        return {"persona_id": f"ap{i}", "name": f"user{i}"}
    return result


def save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def run():
    client = Groq(api_key=key)

    reviews = load_reviews()
    print(f"Loaded {len(reviews)} reviews.")

    print("=== Starting semantic grouping ===")
    groups = semantic_group(client, reviews)
    groups = enforce_min(groups, 10)

    by_id = {r["review_id"]: r for r in reviews}
    for g in groups:
        g["representative_quotes"] = [by_id[r]["original"][:120] for r in g["review_ids"][:8]]

    print("=== Starting persona generation ===")
    personas = []
    prompt_logs = []
    start = time.time()

    for i, g in enumerate(groups, 1):
        samples = "\n".join(f"- {q}" for q in g["representative_quotes"])
        user_prompt = commands.format(
            group_id=g["group_id"],
            review_count=g["review_count"],
            samples=samples
        )

        p = make_persona(client, g, i)

        prompt_logs.append({
            "group_id": g["group_id"],
            "system_prompt": sys_prompt,
            "user_prompt": user_prompt,
            "model": model_id
        })

        personas.append(p)

        avg = (time.time() - start) / i
        eta = avg * (len(groups) - i)
        print(f"Persona {i}/{len(groups)} | ETA: {eta:.1f}s")

        if i < len(groups):
            time.sleep(1.2)

    save(os.path.join(root, "data/review_groups_auto.json"), groups)
    save(os.path.join(root, "personas/personas_auto.json"), personas)
    save(os.path.join(root, "prompts/prompt_auto.json"), prompt_logs)

    print("Pipeline completed successfully!")


if __name__ == "__main__":
    run()