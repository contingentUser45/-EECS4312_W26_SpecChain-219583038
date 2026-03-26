"""runs the full pipeline end-to-end"""
import os, subprocess, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(root, "src")

def run_step(name):
    path = os.path.join(src, name)
    if not os.path.exists(path):
        print(f"missing {name}")
        return False
    try:
        if name == "08_metrics.py":
            subprocess.run(
                [sys.executable, path],
                input="all\n",
                text=True,
                check=True
            )
        else:
            subprocess.run([sys.executable, path], check=True)

        print(f"{name} executed successfully")
        return True

    except subprocess.CalledProcessError:
        print(f"{name} failed, check the code for bugs that can cause this issue")
        return False

def main():
    steps = [
        "00_validate_repo.py", # Run repo check before collection
        "01_collect_or_import.py", # Collect or import required data
        "02_clean.py", # clean data
        "05_personas_auto.py", # Generates Personas
        "06_spec_generate.py", # Generates Specs
        "07_tests_generate.py", # Generates Test
        "08_metrics.py" # Generates all details for the metrics from all pipelines
    ]

    for s in steps:
        if not run_step(s):
            return

    print("\nAll steps executed successfully")

if __name__ == "__main__":
    main()