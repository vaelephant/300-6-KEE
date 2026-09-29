import hashlib, math, re
TOKEN=re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")
DIM=256

def embed(text:str)->list[float]:
    v=[0.0]*DIM
    for t in TOKEN.findall(text.lower()):
        h=int(hashlib.blake2b(t.encode(),digest_size=8).hexdigest(),16)
        v[h%DIM]+=1.0 if (h>>8)&1 else -1.0
    n=math.sqrt(sum(x*x for x in v)) or 1.0
    return [x/n for x in v]

def cosine(a,b): return sum(x*y for x,y in zip(a,b))
