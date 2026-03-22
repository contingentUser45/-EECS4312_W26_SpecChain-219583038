"""cleans raw data & make clean dataset"""
import json
import re
import os

YAPLIMITIER = {
    "the","and","is","in","it","of","to","a","for","on","this","that",
    "was","with","as","but","are","be","have","not","you","i","they",
    "my", "me", "we", "our", "your", "so", "if", "at", "by", "an", "or"
}

NUMCONV = {
    "0":"zero","1":"one","2":"two","3":"three","4":"four",
    "5":"five","6":"six","7":"seven","8":"eight","9":"nine"
}

def convert_numbers(text):
    def repl(match):
        return " ".join(NUMCONV.get(d, d) for d in match.group())
    return re.sub(r'\d+', repl, text)

def lemmatizatinator(word):
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("ing") and len(word) > 4:
        return word[:-3]
    if word.endswith("ed") and len(word) > 3:
        return word[:-2]
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word

def clean(text):
    text = text.lower()
    text = re.sub(r'http\S+', '', text)
    text = convert_numbers(text)
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    words = [w for w in words if w not in YAPLIMITIER]
    words = [lemmatizatinator(w) for w in words]
    return " ".join(words)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    in_path = os.path.join(repo_root, "data", "reviews_raw.jsonl")
    out_path = os.path.join(repo_root, "data", "reviews_clean.jsonl")
    seen = set()

    with open(in_path, "r", encoding="utf-8") as f, \
         open(out_path, "w", encoding="utf-8") as out:

        for line in f:
            r = json.loads(line)
            text = clean(r.get("content", ""))
            if not text or len(text.split()) < 3 or text in seen:
                continue
            seen.add(text)
            out.write(json.dumps({
                "review_id": r.get("review_id"),
                "content": text,
                "score": r.get("score", 0)
            }) + "\n")

    print("Operation successful")

if __name__ == "__main__":
    main()