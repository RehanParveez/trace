import os
import shutil
import subprocess
import sys
import tempfile
import time
from app.modules.drawings_boq.takeoff.prep.analyze import analyze_page
from app.modules.drawings_boq.takeoff.prep.extract import extract_page, open_document
from app.modules.drawings_boq.takeoff.prep import details as D
from PIL import Image, ImageDraw

def line(title, value=""):
  print(f"{title:<26}{value}")

def main() -> int:
  if len(sys.argv) < 2:
    print(__doc__)
    return 2
  pdf = sys.argv[1]

  exe = shutil.which("tesseract")
  line("tesseract on PATH", exe or "NOT FOUND")
  if exe:
    try:
      ver = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
      line("tesseract version", ((ver.stdout or ver.stderr).splitlines() or ["?"])[0])
    except Exception as exc:  
      line("tesseract version", f"failed: {exc!r}")
  for name in ("PIL", "numpy", "pymupdf"):
    try:
      mod = __import__(name)
      line(name, getattr(mod, "__version__", getattr(mod, "VersionBind", "installed")))
    except ImportError:
      line(name, "NOT INSTALLED")

  line("ocr_available()", D.ocr_available())
  line("time limit now (s)", D.OCR_BUDGET_S)
  if not D.ocr_available():
    print("\nVERDICT: the reader cannot run here, so column sizes come from the plan squares.")
    return 1

  img = Image.new("L", (240, 70), 255)
  ImageDraw.Draw(img).text((20, 20), '9" 15"', fill=0)
  fd, path = tempfile.mkstemp(suffix=".png")
  os.close(fd)
  img.save(path)
  t = time.monotonic()
  try:
    r = subprocess.run(["tesseract", path, "-", "--psm", "7"], capture_output=True, text=True, timeout=60)
    line("raw call", f"return code {r.returncode}, {time.monotonic() - t:.2f} s, text {r.stdout.strip()!r}")
    if r.stderr.strip():
      line("raw call message", r.stderr.strip().splitlines()[0][:150])
  except Exception as exc:  
    line("raw call", f"FAILED: {exc!r}")
  finally:
    os.remove(path)

  with open(pdf, "rb") as fh:
    doc = open_document(fh.read())
  page_no = int(sys.argv[2]) if len(sys.argv) > 2 else len(doc)
  raw = extract_page(doc, page_no - 1, budget_s=120)
  res = analyze_page(raw, 1.0, budget_s=60)
  page = doc[page_no - 1]

  calls = [0, 0.0, 0]
  orig = D._tess

  def counted(image, psm):
    s = time.monotonic()
    out = orig(image, psm)
    calls[0] += 1
    calls[1] += time.monotonic() - s
    calls[2] += 0 if out else 1
    return out

  D._tess = counted
  D.OCR_BUDGET_S = 3600.0
  t = time.monotonic()
  facts = D.read_column_details(res.index.words, res.index, page, page.get_size(), raw.cropbox, raw.rotation)
  total = time.monotonic() - t
  print()
  for d in facts["details"]:
    line(f"detail {d['mark']}", f"{d['read']:<10} {d.get('w_in')} x {d.get('h_in')}")
  per = calls[1] / max(calls[0], 1)
  line("tesseract calls", calls[0])
  line("empty answers", calls[2])
  line("seconds per call", f"{per:.2f}")
  line("whole page took (s)", f"{total:.1f}")
  limit = float(os.environ.get("TRACE_OCR_BUDGET_S", "90"))
  print()
  if total <= limit * 0.6:
    print(f"VERDICT: enough. The page took {total:.0f} s against a limit of {limit:.0f} s.")
  else:
    need = int(total * 1.5) + 1
    print(f"VERDICT: too slow. The page took {total:.0f} s; set TRACE_OCR_BUDGET_S={need} (or higher) for the server.")
  if calls[0] and calls[2] > calls[0] * 0.5:
    print("NOTE: most calls came back empty; this is not only speed. Send this output to support.")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())