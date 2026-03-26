"""computes metrics: coverage/traceability/ambiguity/testability"""
import json,os,re

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def path(*x):return os.path.join(ROOT,*x)

mode_input=input("Select mode (auto / hybrid / manual / all): ").strip().lower()
valid_modes=["auto","hybrid","manual"]

if mode_input=="all":modes=valid_modes
elif mode_input in valid_modes:modes=[mode_input]
else:
    print("Invalid input, defaulting to hybrid")
    modes=["hybrid"]

dataset=path("data","reviews_clean.jsonl")

AMBIGUOUS_WORDS=[
"fast","quick","rapid","efficient","optimized",
"user friendly","easy","simple","intuitive","seamless","smooth","effortless",
"robust","scalable","reliable","stable","secure","safe",
"clear","clearly","understandable","obvious","transparent",
"relevant","accurate","appropriate","effective","useful","meaningful",
"high quality","good","better","best","improved","enhanced",
"minimal","sufficient","adequate","acceptable","reasonable",
"responsive","performant","low latency","real-time",
"accessible","available","consistent","flexible","adaptable",
"quickly","easily","properly","correctly","smoothly",
"significant","substantial","large","small","minor",
"frequent","often","rare","occasionally",
"short","long","near","far",
"as needed","where possible","if applicable","as appropriate",
"and/or","etc","various","multiple","several",
"optimized","streamlined","dynamic","powerful"
]

def load_json(p):
    try:
        with open(p,encoding="utf-8") as f:return json.load(f)
    except:return []

def load_jsonl(p):
    try:
        with open(p,encoding="utf-8") as f:return [json.loads(l) for l in f if l.strip()]
    except:return []

def parse_requirements(md):
    res=[]
    matches=list(re.finditer(r"#\s*Requirement ID[:]*\s*(FR[\w\-]+)",md,re.IGNORECASE))
    for i,m in enumerate(matches):
        rid=m.group(1).strip().upper()
        start,end=m.end(),matches[i+1].start() if i+1<len(matches) else len(md)
        block=md[start:end]
        pm=re.search(r"Source Persona:\s*([^\n]+)",block,re.IGNORECASE)
        persona=pm.group(1).strip() if pm else ""
        dm=re.search(r"Description:\s*([^\n]+)",block,re.IGNORECASE)
        desc=dm.group(1).strip().lower() if dm else ""
        res.append({"id":rid,"persona":persona,"description":desc})
    return res

def is_ambiguous(t):
    t=t.lower()
    score=0
    for w in AMBIGUOUS_WORDS:
        if re.search(rf"\b{re.escape(w)}\b",t):score+=1
    if any(re.search(p,t) for p in[
        r"\d+\s*(seconds?|ms|milliseconds?|minutes?)",
        r"\d+\s*(items?|results?|steps?|taps?)",
        r"\d+\s*%",
        r"within\s+\d+",
        r"at least\s+\d+",
        r"no more than\s+\d+"
    ]):score=max(0,score-1)
    return score>0

def normalize_req_id(x):
    if x is None:return None
    x=str(x).strip().upper()
    m=re.match(r"(FR_[A-Z]+)_(\d+)",x)
    if m:return f"{m.group(1)}_{int(m.group(2))}"
    m=re.search(r"(\d+)",x)
    if m:return f"FR_{int(m.group(1))}"
    return x

def normalize_persona_id(p,name_map=None):
    if p is None:return None
    val=str(p).strip().upper()
    val=re.sub(r"[\[\]\*\-—]", " ", val).strip()
    m=re.search(r"P\s*(\d+)",val)
    if m:return f"P{int(m.group(1))}"
    m=re.search(r"(\d+)",val)
    if m:return f"P{int(m.group(1))}"
    if name_map:
        clean=re.sub(r"[^A-Z ]","",val).strip()
        if clean in name_map:return name_map[clean]
    return None

def normalize_id(x):
    if x is None:return None
    x=str(x).strip().upper()
    if re.match(r"^R\d+$",x):return x
    if re.match(r"^\d+$",x):return f"R{int(x):04d}"
    return x

def extract_dataset_ids(d):
    ids=set()
    for x in d:
        if isinstance(x,dict):
            for k in["review_id","id","reviewId"]:
                if k in x:
                    nid=normalize_id(x[k])
                    if nid:ids.add(nid)
    return ids

def extract_group_ids(g):
    ids=set()
    if isinstance(g,dict):g=g.get("groups",[])
    for x in g:
        if isinstance(x,dict) and "review_ids" in x:
            for rid in x["review_ids"]:
                nid=normalize_id(rid)
                if nid:ids.add(nid)
    return ids

def compute(mode):
    groups=path("data",f"review_groups_{mode}.json")
    personas=path("personas",f"personas_{mode}.json")
    spec=path("spec",f"spec_{mode}.md")
    tests=path("tests",f"tests_{mode}.json")
    out=path("metrics",f"metrics_{mode}.json")

    review_groups=load_json(groups)
    raw_personas=load_json(personas)
    tests_data=load_json(tests)
    dataset_data=load_jsonl(dataset)

    if isinstance(raw_personas,dict):personas_data=raw_personas.get("personas",[])
    elif isinstance(raw_personas,list):personas_data=raw_personas
    else:personas_data=[]

    if isinstance(tests_data,dict):tests_data=tests_data.get("tests",[])
    if not isinstance(tests_data,list):tests_data=[]

    name_map={}
    for p in personas_data:
        if isinstance(p,dict):
            raw=p.get("persona_id") or p.get("id") or p.get("persona") or p
            pid=normalize_persona_id(raw)
            name=(p.get("name") or p.get("description") or "").strip().upper()
            if pid and name:
                clean=re.sub(r"[^A-Z ]","",name).strip()
                name_map[clean]=pid

    if os.path.exists(spec):
        with open(spec,encoding="utf-8") as f:requirements=parse_requirements(f.read())
    else:requirements=[]

    qc,rc,pc,tc=len(dataset_data),len(requirements),len(personas_data),len(tests_data)

    valid_persona_ids=set()
    for p in personas_data:
        if isinstance(p,dict):
            raw=p.get("persona_id") or p.get("id") or p.get("persona") or p
        else:
            raw=p
        pid=normalize_persona_id(raw)
        if pid:valid_persona_ids.add(pid)

    tested_ids={normalize_req_id(t.get("requirement_id")) for t in tests_data if isinstance(t,dict) and t.get("requirement_id")}
    requirement_ids={normalize_req_id(r["id"]) for r in requirements}

    traced=sum(
        1 for r in requirements
        if normalize_persona_id(r["persona"],name_map) in valid_persona_ids
        and normalize_req_id(r["id"]) in tested_ids
    )

    ambiguous_count=sum(1 for r in requirements if is_ambiguous(r["description"]))

    dataset_ids=extract_dataset_ids(dataset_data)
    grouped_ids=extract_group_ids(review_groups)
    intersection=dataset_ids&grouped_ids

    print("\n--- SANITY CHECK ---")
    print("req_ids:",list(requirement_ids)[:5])
    print("test_ids:",list(tested_ids)[:5])
    print("personas:",list(valid_persona_ids))
    miss_t=[r["id"] for r in requirements if normalize_req_id(r["id"]) not in tested_ids]
    miss_p=[(r["id"],r["persona"],normalize_persona_id(r["persona"],name_map)) for r in requirements if normalize_persona_id(r["persona"],name_map) not in valid_persona_ids]
    print("missing test:",len(miss_t))
    print("missing persona:",len(miss_p))
    print("persona examples:",miss_p[:5])

    metrics={
        "pipeline":mode,
        "dataset_size":qc,
        "persona_count":pc,
        "requirements_count":rc,
        "tests_count":tc,
        "traceability_links":traced,
        "review_coverage":round(len(intersection)/len(grouped_ids),4) if grouped_ids else 0,
        "traceability_ratio":round(traced/rc,3) if rc else 0,
        "testability_rate":round(len(requirement_ids&tested_ids)/rc,3) if rc else 0,
        "ambiguity_ratio":round(ambiguous_count/rc,3) if rc else 0
    }

    os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,"w",encoding="utf-8") as f:json.dump(metrics,f,indent=2)
    print("saved ->",out)
    return metrics

def run():
    all_metrics=[]
    for m in modes:
        print(f"\nRunning mode: {m}")
        try:all_metrics.append(compute(m))
        except Exception as e:print(f"[WARN] Failed for {m}: {e}")

    if len(all_metrics)>1:
        summary_path=path("metrics","metrics_summary.json")

        best={
            "review_coverage":max(all_metrics,key=lambda x:x["review_coverage"])["pipeline"],
            "traceability_ratio":max(all_metrics,key=lambda x:x["traceability_ratio"])["pipeline"],
            "testability_rate":max(all_metrics,key=lambda x:x["testability_rate"])["pipeline"],
            "ambiguity_ratio":min(all_metrics,key=lambda x:x["ambiguity_ratio"])["pipeline"]
        }

        scores={m["pipeline"]:0 for m in all_metrics}
        for k,v in best.items():scores[v]+=1

        overall=max(scores,key=scores.get)

        summary={
            "metrics_summary":all_metrics,
            "best_by_metric":best,
            "scores":scores,
            "overall_winner":overall
        }

        os.makedirs(os.path.dirname(summary_path),exist_ok=True)
        with open(summary_path,"w",encoding="utf-8") as f:json.dump(summary,f,indent=2)

        print("\nSummary saved ->",summary_path)

if __name__=="__main__":run()