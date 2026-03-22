"""checks required files/folders exist"""
import os

GREEN = "\033[92m"
RED = "\033[91m"
NORMAL = "\033[0m"

required_paths = [
    "../data/reviews_clean.jsonl",
    "../data/review_groups_manual.json",
    "../personas/personas_manual.json",
    "../personas/personas_auto.json",
    "../personas/personas_hybrid.json",
    "../spec/spec_manual.md",
    "../spec/spec_auto.md",
    "../spec/spec_hybrid.md",
    "../tests/tests_manual.json",
    "../tests/tests_auto.json",
    "../tests/tests_hybrid.json",
    "../metrics/metrics_manual.json",
    "../metrics/metrics_auto.json",
    "../metrics/metrics_hybrid.json",
    "../reflection/reflection.md",
    "../README.md"
]

print("Checking repository structure...\n")

filesvalidated = True
fails = 0

for path in required_paths:
    if os.path.exists(path):
        print(f"{GREEN}{path} found{NORMAL}")
    else:
        print(f"{RED}{path} MISSING{NORMAL}")
        filesvalidated = False
        fails = fails + 1


if filesvalidated:
    print(f"{GREEN}Files were successfully Validated{NORMAL}")
else:
    print(f"{RED}Validation Failed. {fails} files are missing from the repository{NORMAL}")