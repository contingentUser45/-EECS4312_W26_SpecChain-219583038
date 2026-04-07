"""generates tests from specs + logs prompts with append/diff"""
import json, os, sys, re, time, random
from groq import Groq, RateLimitError, APIError

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec_path = os.path.join(root, "spec", "spec_auto.md")
output_path = os.path.join(root, "tests", "tests_auto.json")
prompt_path = os.path.join(root, "prompts", "prompt_auto.json")

model_id = "meta-llama/llama-4-scout-17b-16e-instruct"
env = os.path.join(root, ".env")

MAX_RETRIES = 5
BASE_DELAY = 1.5

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
    "You are working on Calm, a meditation and sleep mobile app.\n"
    "generate 2 validation test scenarios.\n"
    "ensure:\n"
    "- steps are clear and workable\n"
    "- expected result directly validates the requirement\n"
    "- output is valid json\n"
    "Return a JSON object with a 'test_scenarios' key containing an array of exactly 2 test objects.\n"
)

commands = (
    "requirement:\n{req}\n\n"
    "generate two test scenarios using this format:\n\n"
    '{{'
    '"test_scenarios": [' 
    '{{'
    '"test_id": "T_auto_xa",'
    '"requirement_id": "fr_auto_x",'
    '"scenario": "short description of validation",'
    '"steps": ["step 1", "step 2", "step 3"],'
    '"expected_result": "specific measurable outcome"'
    '}},'
    '{{'
    '"test_id": "T_auto_xb",'
    '"requirement_id": "fr_auto_x",'
    '"scenario": "short description of validation",'
    '"steps": ["step 1", "step 2", "step 3"],'
    '"expected_result": "specific measurable outcome"'
    '}}'
    ']'
    '}}'
)


def extract_requirements(md_text):
    blocks = md_text.split("# Requirement ID:")
    reqs = []
    for b in blocks[1:]:
        rid_match = re.search(r"(fr_auto_\d+)", b, re.IGNORECASE)
        desc_match = re.search(r"description:\s*\[(.*?)\]", b, re.IGNORECASE)
        if rid_match:
            reqs.append({
                "requirement_id": rid_match.group(1),
                "description": (desc_match.group(1) if desc_match else "").strip()
            })
    return reqs


def is_valid_test(test):
    required = ["test_id", "requirement_id", "scenario", "steps", "expected_result"]
    for f in required:
        if f not in test:
            return False
    if not isinstance(test["steps"], list) or len(test["steps"]) < 2:
        return False
    return True


def fallback_test(req, idx, suffix="a"):
    return {
        "test_id": f"T_auto_{idx}{suffix}",
        "requirement_id": req["requirement_id"],
        "scenario": f"validate {req['description']}",
        "steps": [
            "initialize system",
            f"execute function related to: {req['description']}",
            "capture system response"
        ],
        "expected_result": f"system satisfies requirement: {req['description']}"
    }


def generate_test(client, req, idx):
    prompt = commands.format(req=json.dumps(req, indent=2))
    raw_content = "error"

    for attempt in range(MAX_RETRIES):
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            raw_content = res.choices[0].message.content
            parsed = json.loads(raw_content)

            if isinstance(parsed, list):
                test_list = parsed
            elif isinstance(parsed, dict):
                if "test_scenarios" in parsed and isinstance(parsed["test_scenarios"], list):
                    test_list = parsed["test_scenarios"]
                elif "tests" in parsed and isinstance(parsed["tests"], list):
                    test_list = parsed["tests"]
                else:
                    test_list = [parsed]
            else:
                raise ValueError("invalid structure")

            results = []
            suffixes = ["a", "b"]

            for j in range(2):
                if j < len(test_list):
                    data = test_list[j]
                    if not isinstance(data, dict):
                        data = fallback_test(req, idx, suffixes[j])
                else:
                    data = fallback_test(req, idx, suffixes[j])

                data["test_id"] = f"T_auto_{idx}{suffixes[j]}"
                data["requirement_id"] = req["requirement_id"]

                if not is_valid_test(data):
                    data = fallback_test(req, idx, suffixes[j])
                    data["test_id"] = f"T_auto_{idx}{suffixes[j]}"
                    data["requirement_id"] = req["requirement_id"]

                results.append(data)

            return results, prompt, raw_content

        except (RateLimitError, APIError):
            if attempt == MAX_RETRIES - 1:
                print(f"[FAIL] Max retries hit for {req['requirement_id']}")
                break

            delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
            print(f"[Retry {attempt+1}] Rate limited. Sleeping {delay:.2f}s")
            time.sleep(delay)

        except Exception:
            print(f"something went wrong for {req['requirement_id']}, using backup")
            break

    t1 = fallback_test(req, idx, "a")
    t2 = fallback_test(req, idx, "b")
    return [t1, t2], prompt, raw_content


def save_tests(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wrapped = {"tests": data}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wrapped, f, indent=2, ensure_ascii=False)


def save_prompt_logs(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except:
            print("failed to load existing prompt logs")
            existing = []
    else:
        existing = []

    def key(x):
        return (x.get("requirement_id"), x.get("user_prompt"), x.get("model"))

    existing_keys = {key(x) for x in existing}
    new_unique = [x for x in data if key(x) not in existing_keys]
    existing.extend(new_unique)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"appended {len(new_unique)} new test prompt logs")


def run():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        sys.exit("missing api key")

    if not os.path.exists(spec_path):
        sys.exit("missing spec_auto.md")

    client = Groq(api_key=key)

    with open(spec_path, encoding="utf-8") as f:
        md_text = f.read()

    requirements = extract_requirements(md_text)
    print(f"found {len(requirements)} requirements")

    if not requirements:
        sys.exit("no requirements found")

    tests = []
    prompt_logs = []
    start_time = time.time()

    for i, req in enumerate(requirements, 1):
        test_pair, prompt, response = generate_test(client, req, i)
        tests.extend(test_pair)

        prompt_logs.append({
            "test_id": f"T_auto_{i}a/b",
            "requirement_id": req["requirement_id"],
            "system_prompt": sys_prompt,
            "user_prompt": prompt,
            "response": response,
            "model": model_id
        })

        time.sleep(0.5)  # throttle to avoid burst rate limits

        elapsed = time.time() - start_time
        avg = elapsed / i
        eta = avg * (len(requirements) - i)
        print(f"T_auto_{i}a + T_auto_{i}b generated | ETA: {eta:.1f}s")

    print(f"\nTotal tests generated: {len(tests)} (expected {len(requirements) * 2})")

    save_tests(output_path, tests)
    save_prompt_logs(prompt_path, prompt_logs)

    total_time = time.time() - start_time
    print(f"\nsaved -> {output_path}")
    print(f"total time: {total_time:.2f}s")


if __name__ == "__main__":
    run()