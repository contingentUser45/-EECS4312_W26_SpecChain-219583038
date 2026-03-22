"""creates/updates coding table template + instructions"""
import json
import sys
import os
GREEN = "\033[92m"
RED = "\033[91m"
NORMAL = "\033[0m"

OUTPUT_PATH = "../data/review_groups_manual.json"

def validate_template(data):
    if not isinstance(data, dict):
        print(f"{RED}What is this? this isn't a JSON{NORMAL}")
        return False

    if "groups" not in data or not isinstance(data["groups"], list):
        print(f"{RED}Array mismatch, 'groups' isn't here{NORMAL}")
        return False

    if len(data["groups"]) > 5:
        print(f"{RED}Group count is lower than 5, we need more thant 5 groups{NORMAL}")
        return False

    required_keys = {"group_id", "theme", "review_ids", "notes"}

    for g in data["groups"]:
        missing = required_keys - set(g.keys())
        if missing:
            print(f"{RED}Group {g.get('group_id','?')} is missing the following keys: {missing}{NORMAL}")
            return False
        if not isinstance(g["review_ids"], list):
            print(f"{RED}Group {g['group_id']} review_ids must be a list.{NORMAL}")
            return False
        if len(g["review_ids"]) < 10:
            print(f"{RED}Group {g['group_id']} has less than 10 reviews.{NORMAL}")
            return False

    print(f"{GREEN}ALL IS CLEAR YOU MAY PROCEED{NORMAL}")
    return True

def main():
    if os.path.exists(OUTPUT_PATH):
        print("File already exists. Running validation instead...\n")

        with open(OUTPUT_PATH, encoding="utf-8") as f:
            data = json.load(f)

        valid = validate_template(data)

        if not valid:
            print(f"{RED}WARNING! SYSTEM DETECTED INVALID TEMPLATE!{NORMAL}")
            sys.exit(1)

        return

    template = {
        "instructions": "Create 5 groups. Each must have at least 10 similar reviews.",
        "groups": [
            {"group_id": "G1", "theme": "", "review_ids": [], "notes": ""},
            {"group_id": "G2", "theme": "", "review_ids": [], "notes": ""},
            {"group_id": "G3", "theme": "", "review_ids": [], "notes": ""},
            {"group_id": "G4", "theme": "", "review_ids": [], "notes": ""},
            {"group_id": "G5", "theme": "", "review_ids": [], "notes": ""}
        ]
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(template, f, indent=2)
    print("Template created")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)
    print("Template created.")

if __name__ == "__main__":
    main()
