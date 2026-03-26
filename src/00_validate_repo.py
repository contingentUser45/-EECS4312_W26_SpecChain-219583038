"""checks required files/folders exist"""
import os
import sys

GREEN = "\033[92m"
RED = "\033[91m"
NORMAL = "\033[0m"

required_paths = [
    # scripts
    "00_validate_repo.py",
    "01_collect_or_import.py",
    "02_clean.py",
    "03_manual_coding_template.py",
    "04_personas_manual.py",
    "05_personas_auto.py",
    "06_spec_generate.py",
    "07_tests_generate.py",
    "08_metrics.py",
    "run_all.py",

    # required data
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
    sys.exit(1)