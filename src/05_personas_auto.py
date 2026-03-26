"""automated persona generation pipeline"""
import json, os, sys, time
from groq import Groq

num_clusters=10
batch_size=50
model_id="meta-llama/llama-4-scout-17b-16e-instruct"
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env=os.path.join(root,".env")
if os.path.exists(env):
    lines=[l.strip() for l in open(env) if l.strip()]
    if len(lines)>=2:
        os.environ["groq_api_key"]=lines[1]

sys_prompt="return only valid json."

commands=(
    "create a persona for group {group_id} ({review_count} reviews).\n\n"
    "{samples}\n\n"
    "return json with: persona_id, name, age_range, occupation, context, "
    "goals, pain_points, tech_comfort, quote, group_theme."
)

control_commands=(
    f"you must return only valid json.\n\n"
    f"group reviews into exactly {num_clusters} groups.\n"
    "each review must appear in exactly one group.\n\n"
    '{ "groups": [ { "group_id": "g1", "theme": "...", "review_ids": ["..."] } ] }'
)

def load_reviews():
    path=os.path.join(root,"data","reviews_clean.jsonl")
    if not os.path.exists(path): sys.exit("missing reviews_clean.jsonl")
    out=[]
    for l in open(path,encoding="utf-8"):
        if not l.strip(): continue
        r=json.loads(l)
        txt=r.get("content","")
        out.append({"review_id":str(r.get("review_id")),"original":txt,"cleaned":txt})
    return out

def call_group(client,batch,retries=3):
    txt="\n".join(f'[{r["review_id"]}] {r["cleaned"][:200]}' for r in batch)
    for _ in range(retries):
        try:
            res=client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role":"system","content":control_commands},
                    {"role":"user","content":txt}
                ],
                temperature=0,
                response_format={"type":"json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except:
            pass
    print("skipped batch - something went wrong (check your api key is valid)")
    return {"groups":[]}

def semantic_group(client,reviews):
    by_id={r["review_id"]:r for r in reviews}
    buckets={}
    total=(len(reviews)+batch_size-1)//batch_size
    start=time.time()
    for i,s in enumerate(range(0,len(reviews),batch_size),1):
        res=call_group(client,reviews[s:s+batch_size])
        avg=(time.time()-start)/i
        print(f"processing batch {i}/{total} eta: {avg*(total-i):.1f}s")
        groups_out = res.get("groups", []) if isinstance(res, dict) else res if isinstance(res, list) else []
        for idx,g in enumerate(groups_out):
            if not isinstance(g, dict):
                continue
            gid=g.get("group_id",f"g{idx+1}")
            buckets.setdefault(gid,{"theme":g.get("theme",gid),"reviews":[]})
            for rid in g.get("review_ids",[]):
                r=by_id.get(str(rid))
                if r and r not in buckets[gid]["reviews"]:
                    buckets[gid]["reviews"].append(r)
    groups=[]
    for i,(gid,b) in enumerate(sorted(buckets.items()),1):
        cluster=b["reviews"]
        groups.append({
            "group_id":f"A{i}",
            "group_theme":b["theme"],
            "review_ids":[r["review_id"] for r in cluster],
            "review_count":len(cluster),
            "representative_quotes":[r["original"][:120] for r in cluster[:8]],
        })
    return groups

def enforce_min(groups,min_size=10):
    groups=groups[:5]
    while True:
        groups.sort(key=lambda g:g["review_count"])
        small,big=groups[0],groups[-1]
        if small["review_count"]>=min_size or big["review_count"]<=min_size: break
        rid=big["review_ids"].pop()
        small["review_ids"].append(rid)
        small["review_count"]+=1
        big["review_count"]-=1
    return groups

def make_persona(client,g,i):
    samples="\n".join(f"- {q}" for q in g["representative_quotes"])
    prompt=commands.format(group_id=g["group_id"],review_count=g["review_count"],samples=samples)
    try:
        res=client.chat.completions.create(
            model=model_id,
            messages=[
                {"role":"system","content":sys_prompt},
                {"role":"user","content":prompt}
            ],
            temperature=0.3,
            response_format={"type":"json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except:
        return {"persona_id":f"ap{i}","name":f"user{i}"}

def save(p,d):
    os.makedirs(os.path.dirname(p),exist_ok=True)
    json.dump(d,open(p,"w",encoding="utf-8"),indent=2,ensure_ascii=False)

def run():
    key=os.environ.get("groq_api_key")
    if not key: sys.exit("missing api key")
    client=Groq(api_key=key)
    reviews=load_reviews()
    groups=semantic_group(client,reviews)
    groups=enforce_min(groups,10)
    by_id={r["review_id"]:r for r in reviews}
    for g in groups:
        g["representative_quotes"]=[by_id[r]["original"][:120] for r in g["review_ids"][:8]]
    personas=[]
    prompt_logs=[]
    start=time.time()
    for i,g in enumerate(groups,1):
        samples="\n".join(f"- {q}" for q in g["representative_quotes"])
        user_prompt=commands.format(group_id=g["group_id"],review_count=g["review_count"],samples=samples)
        p=make_persona(client,g,i)
        prompt_logs.append({
            "group_id":g["group_id"],
            "system_prompt":sys_prompt,
            "user_prompt":user_prompt,
            "model":model_id
        })
        avg=(time.time()-start)/i
        print(f"creating persona {i} eta: {avg*(len(groups)-i):.1f}s")
        personas.append(p)
    save(os.path.join(root,"data/review_groups_auto.json"),groups)
    save(os.path.join(root,"personas/personas_auto.json"),personas)
    save(os.path.join(root,"prompts/prompt_auto.json"),prompt_logs)

if __name__=="__main__":
    run()