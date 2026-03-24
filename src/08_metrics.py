"""computes metrics: coverage/traceability/ambiguity/testability"""
import json, os, re

root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p=lambda *x: os.path.join(root,*x)

groups=p("data","review_groups_auto.json")
personas=p("personas","personas_auto.json")
spec=p("spec","spec_auto.md")
tests=p("tests","tests_auto.json")
dataset=p("data","reviews_clean.jsonl")
out=p("metrics","metrics_auto.json")

amb=["fast","quick","efficient","user-friendly","robust","scalable","reliable","easy"]


def load(pth):
    try:
        return json.load(open(pth,encoding="utf-8"))
    except:
        return []


def load_jsonl(pth):
    try:
        return [json.loads(l) for l in open(pth,encoding="utf-8") if l.strip()]
    except:
        return []


def reqs(md):
    return [{
        "id":r.group(1),
        "p":(p_.group(1) if p_ else ""),
        "d":(d.group(1).lower() if d else "")
    } for b in md.split("# Requirement ID:")[1:]
      if (r:=re.search(r"(fr_auto_\d+)",b,re.IGNORECASE))
      for p_ in [re.search(r"source persona:\s*\[(.*?)\]",b,re.IGNORECASE)]
      for d in [re.search(r"description:\s*\[(.*?)\]",b,re.IGNORECASE)]]


def run():
    g,pers,t=load(groups),load(personas),load(tests)
    data=load_jsonl(dataset)

    qc=len(data)
    r=reqs(open(spec,encoding="utf-8").read()) if os.path.exists(spec) else []

    rc,pc,tc=len(r),len(pers),len(t)
    traced=sum(1 for x in r if x["p"])
    tested={x.get("requirement_id") for x in t}
    ambiguous=sum(1 for x in r if any(w in x["d"] for w in amb))

    out_data={
        "pipeline":"auto",
        "dataset_size":qc,
        "persona_count":pc,
        "requirements_count":rc,
        "tests_count":tc,
        "traceability_links":traced,
        "review_coverage":round(pc/qc,4) if qc else 0,
        "traceability_ratio":round(traced/rc,3) if rc else 0,
        "testability_rate":round(len({x["id"] for x in r}&tested)/rc,3) if rc else 0,
        "ambiguity_ratio":round(ambiguous/rc,3) if rc else 0
    }

    os.makedirs(os.path.dirname(out),exist_ok=True)
    json.dump(out_data,open(out,"w",encoding="utf-8"),indent=2)

    print("saved ->",out)


if __name__=="__main__":
    run()