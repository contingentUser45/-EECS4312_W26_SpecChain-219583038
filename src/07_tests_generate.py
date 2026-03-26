"""generates tests from specs + logs prompts with append/diff"""
import json, os, sys, re, time
from groq import Groq

root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec_path=os.path.join(root,"spec","spec_auto.md")
output_path=os.path.join(root,"tests","tests_auto.json")
prompt_path=os.path.join(root,"prompts","prompt_auto.json")
model_id="meta-llama/llama-4-scout-17b-16e-instruct"

env=os.path.join(root,".env")
if os.path.exists(env):
    lines=[l.strip() for l in open(env) if l.strip()]
    if len(lines)>=2:
        os.environ["groq_api_key"]=lines[1]

sys_prompt=(
    "generate a validation test scenario.\n"
    "ensure:\n"
    "- steps are clear and workable\n"
    "- expected result directly validates the requirement\n"
    "- output is valid json\n"
)

commands=(
    "requirement:\n{req}\n\n"
    "generate one test scenario in this using this format:\n\n"
    '{{'
    '"test_id": "T_auto_x",'
    '"requirement_id": "fr_auto_x",'
    '"scenario": "short description of validation",'
    '"steps": ["step 1", "step 2", "step 3"],'
    '"expected_result": "specific measurable outcome"'
    '}}'
)


def extract_requirements(md_text):
    blocks=md_text.split("# Requirement ID:")
    reqs=[]
    for b in blocks[1:]:
        rid_match=re.search(r"(fr_auto_\d+)",b,re.IGNORECASE)
        desc_match=re.search(r"description:\s*\[(.*?)\]",b,re.IGNORECASE)
        if rid_match:
            reqs.append({
                "requirement_id":rid_match.group(1),
                "description":(desc_match.group(1) if desc_match else "").strip()
            })
    return reqs


def is_valid_test(test):
    required=["test_id","requirement_id","scenario","steps","expected_result"]
    for f in required:
        if f not in test:
            return False
    if not isinstance(test["steps"],list) or len(test["steps"])<2:
        return False
    return True


def fallback_test(req,idx):
    return {
        "test_id":f"T_auto_{idx}",
        "requirement_id":req["requirement_id"],
        "scenario":f"validate {req['description']}",
        "steps":[
            "initialize system",
            f"execute function related to: {req['description']}",
            "capture system response"
        ],
        "expected_result":f"system satisfies requirement: {req['description']}"
    }


def generate_test(client,req,idx):
    prompt=commands.format(req=json.dumps(req,indent=2))
    try:
        res=client.chat.completions.create(
            model=model_id,
            messages=[
                {"role":"system","content":sys_prompt},
                {"role":"user","content":prompt}
            ],
            temperature=0.2,
            response_format={"type":"json_object"}
        )
        raw_output=res.choices[0].message.content
        data=json.loads(raw_output)
        if not is_valid_test(data):
            raise ValueError("invalid structure")
    except Exception as e:
        print(f"something went wrong for {req['requirement_id']} ({e}) using backup")
        raw_output=f"error: {str(e)}"
        data=fallback_test(req,idx)
    data["test_id"]=f"T_auto_{idx}"
    data["requirement_id"]=req["requirement_id"]
    return data,prompt,raw_output


def validate_coverage(requirements,tests):
    req_ids={r["requirement_id"] for r in requirements}
    tested_ids={t["requirement_id"] for t in tests}
    missing=req_ids-tested_ids
    if missing:
        raise ValueError(f"missing tests for: {missing}")


def save_tests(path,data):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    wrapped = {
        "tests": data
    }
    with open(path,"w",encoding="utf-8") as f:
        json.dump(wrapped,f,indent=2,ensure_ascii=False)

def save_prompt_logs(path,data):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path,encoding="utf-8") as f:
                existing=json.load(f)
            if not isinstance(existing,list):
                existing=[]
        except:
            print("failed to load existing prompt logs, stopping edits")
            return
    else:
        existing=[]

    def key(x):
        return (x.get("requirement_id"),x.get("user_prompt"),x.get("model"))

    existing_keys={key(x) for x in existing}
    new_unique=[x for x in data if key(x) not in existing_keys]
    existing.extend(new_unique)

    with open(path,"w",encoding="utf-8") as f:
        json.dump(existing,f,indent=2,ensure_ascii=False)

    print(f"appended {len(new_unique)} new test prompt logs")


def run():
    key=os.environ.get("groq_api_key")
    if not key:
        sys.exit("missing api key, ensure .env exists")

    if not os.path.exists(spec_path):
        sys.exit("missing spec_auto.md")

    client=Groq(api_key=key)

    with open(spec_path,encoding="utf-8") as f:
        md_text=f.read()

    requirements=extract_requirements(md_text)
    print(f"found {len(requirements)} requirements")

    if not requirements:
        sys.exit("no requirements found")

    tests=[]
    prompt_logs=[]
    start_time=time.time()

    for i,req in enumerate(requirements,1):
        test,prompt,response=generate_test(client,req,i)
        tests.append(test)

        prompt_logs.append({
            "test_id":f"T_auto_{i}",
            "requirement_id":req["requirement_id"],
            "system_prompt":sys_prompt,
            "user_prompt":prompt,
            "response":response,
            "model":model_id
        })

        elapsed=time.time()-start_time
        avg=elapsed/i
        eta=avg*(len(requirements)-i)
        print(f"T_auto_{i} generating | eta: {eta:.1f}s")

    validate_coverage(requirements,tests)

    total_time=time.time()-start_time
    save_tests(output_path,tests)
    save_prompt_logs(prompt_path,prompt_logs)

    print(f"\nsaved -> {output_path}")
    print(f"total time: {total_time:.2f}s")


if __name__=="__main__":
    run()