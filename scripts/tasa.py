"""Baja la tasa oficial del BCV y la guarda en tasa.json.

Fuentes: la página del BCV (la oficial, publica la tasa del próximo día hábil
apenas sale) y ve.dolarapi.com (respaldo; a veces se atrasa, sobre todo en
feriados). Se queda con la de fecha valor más reciente.
"""
import json, re, subprocess, sys

def get(url, insecure=False):
    cmd = ["curl", "-fsSL", "--retry", "3", "-m", "40", "-A", "Mozilla/5.0", url]
    if insecure:
        # bcv.org.ve tiene la cadena del certificado incompleta; la tasa se
        # compara abajo con la otra fuente antes de usarla.
        cmd.insert(1, "-k")
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout

fuentes = []
try:
    j = json.loads(get("https://ve.dolarapi.com/v1/dolares/oficial"))
    if j.get("promedio", 0) > 0:
        fuentes.append(("dolarapi", float(j["promedio"]), j["fechaActualizacion"]))
except Exception as e:
    print("dolarapi falló:", e)

try:
    html = get("https://www.bcv.org.ve/", insecure=True)
    m = re.search(r'id="dolar".*?<strong>\s*([\d.,]+)\s*</strong>', html, re.S)
    f = re.search(r'date-display-single[^>]*content="([^"]+)"', html)
    if m and f:
        v = float(m.group(1).replace(".", "").replace(",", "."))
        fuentes.append(("bcv", v, f.group(1)))
    else:
        print("BCV: no se encontró la tasa en la página")
except Exception as e:
    print("BCV falló:", e)

print(fuentes)
if not fuentes:
    sys.exit("Ninguna fuente respondió")

ref = next((v for n, v, _ in fuentes if n == "dolarapi"), None)
ok = [x for x in fuentes if x[1] > 0 and (ref is None or abs(x[1] / ref - 1) < 0.05)]
if not ok:
    sys.exit("Las tasas no pasan la revisión")
nombre, tasa, fecha = max(ok, key=lambda x: x[2][:10])

actual = {}
try:
    actual = json.load(open("tasa.json"))
except Exception:
    pass
if actual.get("fecha", "")[:10] > fecha[:10]:
    print("tasa.json ya tiene una fecha más nueva; no se cambia")
    sys.exit(0)

json.dump({"tasa": tasa, "fecha": fecha}, open("tasa.json", "w"), indent=2)
print("Usada:", nombre, tasa, fecha)
