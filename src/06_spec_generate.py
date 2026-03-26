"""generates structured specs from personas"""
import json,os,sys,time
from groq import Groq

root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
personas_path=os.path.join(root,"personas","personas_auto.json")
groups_path=os.path.join(root,"data","review_groups_auto.json")
output_path=os.path.join(root,"spec","spec_auto.md")
prompt_path=os.path.join(root,"prompts","prompt_auto.json")
model_id="meta-llama/llama-4-scout-17b-16e-instruct"

env=os.path.join(root,".env")
if os.path.exists(env):
    lines=[l.strip() for l in open(env) if l.strip()]
    if len(lines)>=2:os.environ["GROQ_API_KEY"]=lines[1]

sys_prompt=("Generate a functional requirement strictly following the required template.\n"
"Use ONLY precise, measurable, and testable language.\n"
"DO NOT use ANY vague or ambiguous terms such as: fast, quick, efficient, user-friendly, robust, scalable, reliable, easy, intuitive. or the requirement is kaput\n"
"Every requirement must include a measurable condition (e.g., time, percentage, limit, or specific behavior).\n"
"Bad example: 'system should be fast'\n"
"Good example: 'system shall respond within 2 seconds for 95% of requests'\n"
"Use the persona's pain points and goals.\n"
"Return ONLY valid JSON.")

commands=("Persona:\n{persona}\n\n"
"Group Theme: {theme}\n"
"Group ID: {gid}\n\n"
"Generate a requirement using EXACT structure:\n\n"
'{{'
'"requirement_id": "FR_auto_X",'
'"description": "...",'
'"source_persona": "...",'
'"traceability": "...",'
'"acceptance_criteria": "Given..., When..., Then..."'
'}}')

def load_json(path):
    with open(path,encoding="utf-8") as f:return json.load(f)

def generate_requirement(client,persona,group,idx):
    persona_text=json.dumps(persona,indent=2)
    theme=group.get("group_theme","user needs")
    gid=group.get("group_id",f"A{idx}")
    user_prompt=commands.format(persona=persona_text,theme=theme,gid=gid)
    try:
        res=client.chat.completions.create(
            model=model_id,
            messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_prompt}],
            temperature=0.3,
            response_format={"type":"json_object"}
        )
        data=json.loads(res.choices[0].message.content)
    except:
        data={
            "requirement_id":f"FR_auto_{idx}",
            "description":"The system shall operate reliably.",
            "source_persona":persona.get("name",f"User{idx}"),
            "traceability":f"Derived from review group {gid}",
            "acceptance_criteria":"Given normal usage, When the system is used, Then it must function without failure."
        }
    data["requirement_id"]=f"FR_auto_{idx}"
    data["traceability"]=f"Derived from review group {gid}"
    return data,user_prompt

def format_md(req):
    return f"""# Requirement ID: {req["requirement_id"]}
- Description: [{req["description"]}]
- Source Persona: [{req["source_persona"]}]
- Traceability: [{req["traceability"]}]
- Acceptance Criteria:[{req["acceptance_criteria"]}]
"""

def save(path,data):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path,encoding="utf-8") as f:existing=json.load(f)
            if not isinstance(existing,list):existing=[]
        except:
            print("Failed to load existing JSON, stopping edits");return
    else:existing=[]
    def key(x):return(x.get("requirement_id"),x.get("user_prompt"))
    existing_keys={key(x) for x in existing}
    new_unique=[x for x in data if key(x) not in existing_keys]
    existing.extend(new_unique)
    with open(path,"w",encoding="utf-8") as f:json.dump(existing,f,indent=2,ensure_ascii=False)
    print(f"Appended {len(new_unique)} new prompt logs")

def run():
    key=os.environ.get("GROQ_API_KEY")
    if not key:sys.exit("Missing API key")
    client=Groq(api_key=key)
    personas=load_json(personas_path)
    groups=load_json(groups_path)
    group_map={g["group_id"]:g for g in groups}
    specs=[]
    prompt_logs=[]
    total=len(personas)*2
    start_time=time.time()
    req_counter=1
    for i,persona in enumerate(personas,1):
        iter_start=time.time()
        gid=persona.get("review_group_id") or f"AG{i}"
        group=group_map.get(gid,{})
        for _ in range(2):
            req,user_prompt=generate_requirement(client,persona,group,req_counter)
            specs.append(format_md(req))
            prompt_logs.append({
                "requirement_id":req["requirement_id"],
                "system_prompt":sys_prompt,
                "user_prompt":user_prompt,
                "model":model_id
            })
            req_counter+=1
        elapsed=time.time()-start_time
        avg=elapsed/req_counter
        eta=avg*(total-req_counter)
        print(f"Generated 2 requirements for persona {i} in {time.time()-iter_start:.2f}s | ETA: {eta:.1f}s")
    total_time=time.time()-start_time
    os.makedirs(os.path.dirname(output_path),exist_ok=True)
    with open(output_path,"w",encoding="utf-8") as f:f.write("\n".join(specs))
    save(prompt_path,prompt_logs)
    print(f"\nTotal time: {total_time:.2f}s")

if __name__=="__main__":run()