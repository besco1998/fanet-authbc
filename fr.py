import re
from pathlib import Path

p = Path("/home/besco1998/projects/fanet-authbc/paper/main.tex")
t = p.read_text()

old = "the co-design sustains $1.9$--$3.2\\times$"
new = "the co-design sustains $1.9\\times$--$3.2\\times$"
assert t.count(old) == 1, f"got {t.count(old)}"
p.write_text(t.replace(old, new))

t2 = p.read_text()
i, j = t2.index("\\begin{abstract}"), t2.index("\\end{abstract}")
ab = t2[i:j]
print("quoted ratios:", re.findall(r"\$?(\d\.\d)\\times\$?", ab))
stripped = re.sub(r"\\[a-zA-Z]+\*?(\[[^]]*\])?({[^}]*})?", " ", ab)
print("words:", len(stripped.split()))
