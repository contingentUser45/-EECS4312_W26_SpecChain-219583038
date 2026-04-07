"""generates structured specs from personas"""
import json, os, sys, time
from groq import Groq

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
personas_path = os.path.join(root, "personas", "personas_auto.json")
groups_path = os.path.join(root, "data", "review_groups_auto.json")
output_path = os.path.join(root, "spec", "spec_auto.md")
prompt_path = os.path.join(root, "prompts", "prompt_auto.json")

model_id = "meta-llama/llama-4-scout-17b-16e-instruct"
env = os.path.join(root, ".env")

print("Checking for GROQ_API_KEY...")

key = os.environ.get("GROQ_API_KEY")

if not key and os.path.exists(env):
    print("   Checking .env file...")
    lines = [l.strip() for l in open(env, encoding="utf-8") if l.strip()]
    if len(lines) >= 2:
        for line in lines:
            if line.startswith("GROQ_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"\'')
                break
        if not key:
            key = lines[1]

if not key:
    print("\nGROQ_API_KEY not found.")
    print("   Use: export GROQ_API_KEY=\"your_key_here\"")
    key_input = input("Enter your Groq API key: ").strip()
    if key_input:
        key = key_input
    else:
        sys.exit("No API key provided.")
else:
    print("   API key found.")

os.environ["GROQ_API_KEY"] = key

sys_prompt = (
    "Generate unique functional requirements for Calm, a meditation and sleep app on Google Play, strictly following the required template.\n"
    "Use ONLY precise, measurable, and testable language.\n"
    "DO NOT use ANY vague or ambiguous terms such as: fast, quick, rapid, efficient, optimized, user friendly, easy, simple, intuitive, seamless, smooth, effortless, robust, scalable, reliable, stable, secure, safe, clear, clearly, understandable, obvious, transparent, relevant, accurate, appropriate, effective, useful, meaningful, high quality, good, better, best, improved, enhanced, minimal, sufficient, adequate, acceptable, reasonable, responsive, performant, low latency, real-time, accessible, available, consistent, flexible, adaptable, quickly, easily, properly, correctly, smoothly, significant, substantial, large, small, minor, frequent, often, rare, occasionally, short, long, near, far, as needed, where possible, if applicable, as appropriate, and/or, etc, various, multiple, several, optimized, streamlined, dynamic, powerful. or the requirement is kaput\n"
    "Every requirement must include a measurable condition (e.g., time, percentage, limit, or specific behavior).\n"
    "Bad example: 'system should be fast'\n"
    "Good example: 'system shall respond within 2 seconds for 95% of requests'\n"
    "Use the persona's pain points and goals.\n"
    "Return ONLY valid JSON."
)

commands = (
    "Persona:\n{persona}\n\n"
    "Group Theme: {theme}\n"
    "Group ID: {gid}\n\n"
    "Generate a requirement using EXACT structure:\n\n"
    '{{'
    '"requirement_id": "FR_auto_X",'
    '"description": "...",'
    '"source_persona": "...",'
    '"traceability": "...",'
    '"acceptance_criteria": "Given..., When..., Then..."'
    '}}'
)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_requirement(client, persona, group, idx):
    persona_text = json.dumps(persona, indent=2)
    theme = group.get("group_theme", "user needs")
    gid = group.get("group_id", f"A{idx}")

    user_prompt = commands.format(persona=persona_text, theme=theme, gid=gid)

    try:
        res = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content.strip()
        parsed = json.loads(content)

        if isinstance(parsed, list):
            if len(parsed) == 0:
                raise ValueError("Empty list returned")
            data = parsed[0]
        elif isinstance(parsed, dict):
            data = parsed
        else:
            raise ValueError(f"Unexpected type: {type(parsed)}")

    except Exception:
        data = {
            "requirement_id": f"FR_auto_{idx}",
            "description": "The system shall operate without failure under normal usage conditions.",
            "source_persona": persona.get("name", f"User{idx}"),
            "traceability": f"Derived from review group {gid}",
            "acceptance_criteria": "Given normal usage conditions, When the user interacts with the feature, Then the system responds within 3 seconds for at least 95% of interactions."
        }

    data["requirement_id"] = f"FR_auto_{idx}"
    data["traceability"] = f"Derived from review group {gid}"

    data.setdefault("description", "The system shall ...")
    data.setdefault("source_persona", persona.get("name", f"User{idx}"))
    data.setdefault("acceptance_criteria", "Given ..., When ..., Then ...")

    return data, user_prompt


def format_md(req):
    return f"""# Requirement ID: {req["requirement_id"]}
- Description: [{req["description"]}]
- Source Persona: [{req["source_persona"]}]
- Traceability: [{req["traceability"]}]
- Acceptance Criteria: [{req["acceptance_criteria"]}]
"""


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except:
            print("Failed to load existing JSON")
            return
    else:
        existing = []

    def key(x):
        return (x.get("requirement_id"), x.get("user_prompt"))

    existing_keys = {key(x) for x in existing}
    new_unique = [x for x in data if key(x) not in existing_keys]
    existing.extend(new_unique)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"Appended {len(new_unique)} new prompt logs")


def run():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        sys.exit("missing api key")

    client = Groq(api_key=key)
    personas = load_json(personas_path)
    groups = load_json(groups_path)
    group_map = {g["group_id"]: g for g in groups}

    specs = []
    prompt_logs = []
    total = len(personas) * 2
    start_time = time.time()
    req_counter = 1

    for i, persona in enumerate(personas, 1):
        iter_start = time.time()
        gid = persona.get("review_group_id") or f"AG{i}"
        group = group_map.get(gid, {})

        for _ in range(2):
            req, user_prompt = generate_requirement(client, persona, group, req_counter)
            specs.append(format_md(req))
            prompt_logs.append({
                "requirement_id": req["requirement_id"],
                "system_prompt": sys_prompt,
                "user_prompt": user_prompt,
                "model": model_id
            })
            req_counter += 1

        elapsed = time.time() - start_time
        avg = elapsed / req_counter
        eta = avg * (total - req_counter)
        print(f"Generated 2 requirements for persona {i} | ETA: {eta:.1f}s")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(specs))

    save(prompt_path, prompt_logs)

    total_time = time.time() - start_time
    print(f"\nTotal time: {total_time:.2f}s")


if __name__ == "__main__":
    run()