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
        subprocess.run([sys.executable, path], check=True)
        print(f"{name} executed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"{name} failed, check the code for bugs that can cause this issue")
        return False

def main():
    steps = [
        "00_validate_repo.py",
        "01_collect_or_import.py",
        "02_clean.py",
        "05_personas_auto.py",
        "06_spec_generate.py",
        "07_tests_generate.py",
        "08_metrics.py"
    ]
    for s in steps:
        if not run_step(s):
            return
    print(f"\nAll steps executed successfully")

if __name__ == "__main__":
    main()