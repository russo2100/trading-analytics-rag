import sys

print("sys.executable:", sys.executable)
print("sys.version:", sys.version)

def check(modname: str):
    try:
        m = __import__(modname)
        path = getattr(m, "__file__", None)
        print(f"[OK] import {modname} -> {path}")
    except Exception as e:
        print(f"[FAIL] import {modname} -> {type(e).__name__}: {e}")

check("PIL")
check("PyPDF2")
check("docx")
check("faiss")
check("numpy")
