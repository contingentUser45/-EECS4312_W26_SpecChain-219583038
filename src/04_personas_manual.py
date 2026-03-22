import json
import os
import sys

REQUIRED_KEYS = {"id", "name", "description", "derived_from_group", "goals", "pain_points"}
LIST_FIELDS   = ("goals", "pain_points", "context", "constraints", "evidence_reviews")

def get_paths():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return (
        os.path.join(root, "personas", "personas_manual.json"),
        os.path.join(root, "data", "review_groups_manual.json"),
    )

def load_json(path, label):
    if not os.path.exists(path):
        print(f"[!!] {label} not found.")
        sys.exit(1)
    content = open(path, encoding="utf-8").read().strip()
    if not content or content in ("[]", "{}"):
        print(f"[!!] {label} is empty — populate it first.")
        sys.exit(1)
    return json.loads(content)

def generate_template(groups_path, persona_path):
    data   = load_json(groups_path, "review_groups_manual.json")
    groups = data.get("groups", data) if isinstance(data, dict) else data

    if not isinstance(groups, list) or not groups:
        print("[!!] review_groups_manual.json has no groups.")
        sys.exit(1)

    personas = [
        {
            "id":                 f"P{i}",
            "name":               "TODO: Descriptive persona name",
            "description":        "TODO: Who this person is and their situation",
            "derived_from_group": g.get("group_id", f"G{i}") if isinstance(g, dict) else str(g),
            "goals":              ["TODO: What does this user want?"],
            "pain_points":        ["TODO: What frustrates this user?"],
            "context":            ["TODO: When/how do they use the app?"],
            "constraints":        ["TODO: What limitations matter to them?"],
            "evidence_reviews":   ["TODO: e.g. rev_12"],
        }
        for i, g in enumerate(groups, start=1)
    ]

    os.makedirs(os.path.dirname(persona_path), exist_ok=True)
    json.dump({"personas": personas}, open(persona_path, "w", encoding="utf-8"), indent=2)
    print(f"[OK] Template created — {len(personas)} persona(s) scaffolded.")
    print("     Fill in all TODO fields before running this script again.")

def validate(persona_path):
    personas = load_json(persona_path, "personas_manual.json").get("personas", [])
    if not isinstance(personas, list) or not personas:
        print('[!!] Expected {"personas": [...]} with at least one entry.')
        sys.exit(1)

    errors = [
        f"  [{p.get('id','?')}] {msg}"
        for p in personas
        for msg in (
            [f"missing keys: {REQUIRED_KEYS - set(p)}"] if REQUIRED_KEYS - set(p) else []
        ) + (
            ["has unfilled TODO fields"] if "TODO" in json.dumps(p) else []
        ) + [
            f"'{f}' must be a non-empty list"
            for f in LIST_FIELDS
            if f in p and (not isinstance(p[f], list) or not p[f])
        ]
    ]

    if errors:
        print("[!!] Validation failed:\n" + "\n".join(errors))
        sys.exit(1)
    print(f"[OK] Valid — {len(personas)} persona(s) found.")

def main():
    persona_path, groups_path = get_paths()
    content = open(persona_path, encoding="utf-8").read().strip() if os.path.exists(persona_path) else ""

    if not content or content in ("[]", "{}", '{"personas": []}'):
        print("[--] File missing or empty — generating starter template...")
        generate_template(groups_path, persona_path)
    else:
        print("[--] File found — validating...")
        validate(persona_path)

if __name__ == "__main__":
    main()