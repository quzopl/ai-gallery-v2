"""Re-parse all libraries with the current detection engine (no server needed)."""
import sys, time
from pathlib import Path
from backend import db, detect, scanner

DB = Path(__file__).parent / ".work" / "gallery.db"
db.init_schema(DB)
w = db.start_writer(DB)
con = db.readonly(DB)
detect.REGISTRY.learned = [r[0] for r in con.execute("SELECT base FROM model_bases")]
detect.REGISTRY.on_learn = lambda b: db.add_model_base(w, base=b)
libs = con.execute("SELECT id, path FROM libraries").fetchall()
con.close()
for lib in libs:
    t = time.time()
    r = scanner.scan_library(library_id=lib["id"], library_root=Path(lib["path"]), writer=w,
                             db_path=DB, force="--force" in sys.argv,
                             on_progress=lambda a, b: print(f"\r{lib['path']} {a}/{b}", end="", flush=True))
    print(f"\n{r} in {time.time()-t:.0f}s")
db.stop_writer(w)
