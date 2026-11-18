#!/usr/bin/env python3
"""Generador estático de VerificaFácil.

Uso:  python build.py            -> genera el sitio en _site/
Datos: data/directorio.csv (fuente oficial, ver config.json)
Guías: content/guias/<slug>.md  (front matter opcional: title, description, date)
"""
import csv, html, json, re, shutil, unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
BASE_URL = CFG["base_url"].rstrip("/") + "/"
BASE_PATH = "/" + BASE_URL.split("://", 1)[1].split("/", 1)[1]  # p. ej. /verificafacil/
e = html.escape
pages = []  # rutas relativas generadas (para el sitemap)


def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def url(rel=""):
    return BASE_PATH + rel


def fecha_larga(iso):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} de {meses[m - 1]} de {y}"


def tipo_label(t):
    return "Taller PIREC" if "pirec" in t.lower() else "Verificentro"


def to_int(v):
    try:
        return int(str(v).strip())
    except ValueError:
        return None


# ---------- Plantilla ----------
def layout(rel, title, description, body, jsonld=None, extra_head=""):
    canonical = BASE_URL + rel
    ld = ""
    if jsonld:
        ld = '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    fuente = (f'Datos de fuente pública: <a href="{e(CFG["data_source_url"])}" rel="nofollow noopener">{e(CFG["data_source_name"])}</a>, '
              f'consultados el {fecha_larga(CFG["data_retrieved"])}.')
    ads = ""
    if CFG["ads"]["enabled"]:
        ads = '<aside class="ad-slot" aria-label="Publicidad"><!-- código de anuncios aquí --></aside>'
    else:
        ads = '<!-- ad-slot inactivo: activar en config.json (ads.enabled) -->'
    return f"""<!doctype html>
<html lang="{CFG['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_MX">
<link rel="stylesheet" href="{url('static/style.css')}">
{ld}{extra_head}
</head>
<body>
<header class="top"><div class="wrap">
<a class="brand" href="{url()}">{e(CFG['site_name'])}</a>
<nav><a href="{url()}#municipios">Municipios</a> <a href="{url('guias/')}">Guías</a></nav>
</div></header>
<div class="disclaimer" role="note"><div class="wrap">
<strong>Sitio independiente y no oficial.</strong> No tenemos relación con el Gobierno del Estado de México ni con ninguna autoridad.
{fuente} La información puede cambiar: confírmala siempre con la autoridad o con el centro antes de acudir.
</div></div>
<main class="wrap">
{body}
{ads}
</main>
<footer class="foot"><div class="wrap">
<p><strong>{e(CFG['site_name'])}</strong> es un directorio independiente, sin afiliación gubernamental. {fuente}
Para trámites y citas usa los sitios oficiales: {" · ".join(f'<a href="{e(l["url"])}" rel="noopener">{e(l["title"])}</a>' for l in CFG["official_links"])}.</p>
<p><a href="{url('contacto/')}">Contacto</a> · <a href="{url('aviso/')}">Aviso legal</a></p>
</div></footer>
</body>
</html>
"""


def write(rel, content):
    path = OUT / rel / "index.html" if (rel == "" or rel.endswith("/")) else OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if rel == "" or rel.endswith("/"):
        pages.append(rel)


def breadcrumbs(items):
    parts = []
    for label, href in items:
        parts.append(f'<a href="{href}">{e(label)}</a>' if href else f"<span>{e(label)}</span>")
    return '<nav class="crumbs" aria-label="Migas de pan">' + " › ".join(parts) + "</nav>"


def cta_html():
    c = CFG["contact"]
    href = c["url"] if c["url"].startswith("http") else url(c["url"])
    return f'<p class="cta"><a href="{e(href)}">{e(c["cta_text"])}</a></p>'


# ---------- Datos ----------
def load_centers():
    with open(ROOT / CFG["data_file"], encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    centers = []
    for r in rows:
        r = {k: (v or "").strip() for k, v in r.items()}
        r["tipo_label"] = tipo_label(r["tipo"])
        r["mun_slug"] = slugify(r["municipio"])
        r["slug"] = slugify(r["clave"] + "-" + r["nombre"])[:80].strip("-")
        r["gas"] = to_int(r.get("lineas_gasolina", ""))
        r["die"] = to_int(r.get("lineas_diesel", ""))
        if r.get("latitud") and r.get("longitud"):
            r["maps"] = f"https://www.google.com/maps?q={r['latitud']},{r['longitud']}"
        else:
            r["maps"] = r.get("google_maps", "")
        centers.append(r)
    return centers


def lineas_txt(c):
    if c["tipo_label"] != "Verificentro":
        return "—"
    g = "" if c["gas"] is None else str(c["gas"])
    d = "" if c["die"] is None else str(c["die"])
    return f"{g} / {d}" if (g or d) else "—"


def tel_link(t):
    digits = re.sub(r"\D", "", t)
    return f'<a href="tel:+52{digits}">{e(t)}</a>' if digits else ""


# ---------- Páginas ----------
def center_page(c):
    rel = f"centro/{c['slug']}/"
    tipo = c["tipo_label"]
    title = f"{c['nombre']} – {tipo} en {c['municipio']} ({c['clave']}) | {CFG['site_name']}"
    desc = f"{tipo} {c['clave']} en {c['municipio']}, Estado de México: {c['domicilio']}. Teléfono {c['telefono_principal']}."
    desc = desc[:300]
    tels = [t.strip() for t in c["telefonos"].split("/") if t.strip()] or [c["telefono_principal"]]
    rows = [
        ("Clave", e(c["clave"])),
        ("Tipo", e(tipo)),
        ("Municipio", f'<a href="{url("municipio/" + c["mun_slug"] + "/")}">{e(c["municipio"])}</a>'),
        ("Domicilio", e(c["domicilio"])),
        ("Teléfonos", "<br>".join(tel_link(t) for t in tels)),
    ]
    if tipo == "Verificentro":
        if c["gas"] is not None:
            rows.append(("Líneas de gasolina", str(c["gas"])))
        if c["die"] is not None:
            rows.append(("Líneas de diésel", str(c["die"])))
    if c["maps"]:
        rows.append(("Ubicación", f'<a href="{e(c["maps"])}" rel="noopener">Ver en Google Maps</a>'))
    explica = ("Los talleres PIREC están autorizados para reparar vehículos que no aprobaron la verificación."
               if tipo != "Verificentro" else
               "Las citas de verificación se agendan en el sistema oficial del Gobierno del Estado de México.")
    body = breadcrumbs([("Inicio", url()), (c["municipio"], url("municipio/" + c["mun_slug"] + "/")), (c["clave"], None)])
    body += f"<h1>{e(c['nombre'])}</h1>\n<p class=\"lead\">{e(tipo)} en {e(c['municipio'])}, Estado de México.</p>\n"
    body += '<table class="ficha">' + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>\n"
    body += f'<p>{explica} <a href="{e(c["citas_oficiales"] or "https://citaverificacion.edomex.gob.mx")}" rel="noopener">Agenda tu cita en el sitio oficial</a>.</p>\n'
    body += cta_html()
    jsonld = {
        "@context": "https://schema.org",
        "@type": "AutomotiveBusiness",
        "name": c["nombre"],
        "identifier": c["clave"],
        "description": f"{tipo} autorizado en {c['municipio']}, Estado de México.",
        "url": BASE_URL + rel,
        "telephone": c["telefono_principal"],
        "address": {
            "@type": "PostalAddress",
            "streetAddress": c["domicilio"],
            "addressLocality": c["municipio"],
            "addressRegion": "Estado de México",
            "addressCountry": "MX",
        },
    }
    m = re.search(r"C\.?\s*P\.?\s*(\d{5})", c["domicilio"])
    if m:
        jsonld["address"]["postalCode"] = m.group(1)
    if c.get("latitud") and c.get("longitud"):
        jsonld["geo"] = {"@type": "GeoCoordinates", "latitude": float(c["latitud"]), "longitude": float(c["longitud"])}
        jsonld["hasMap"] = c["maps"]
    write(rel, layout(rel, title, desc, body, jsonld))


def centers_table(cs):
    head = "<tr><th>Nombre</th><th>Domicilio</th><th>Teléfono</th><th>Tipo</th><th>Líneas gasolina / diésel</th><th>Mapa</th></tr>"
    trs = []
    for c in cs:
        maps = f'<a href="{e(c["maps"])}" rel="noopener">Google Maps</a>' if c["maps"] else ""
        trs.append(
            f'<tr><td data-l="Nombre"><a href="{url("centro/" + c["slug"] + "/")}">{e(c["nombre"])}</a> <small>{e(c["clave"])}</small></td>'
            f'<td data-l="Domicilio">{e(c["domicilio"])}</td><td data-l="Teléfono">{tel_link(c["telefono_principal"])}</td>'
            f'<td data-l="Tipo">{e(c["tipo_label"])}</td><td data-l="Líneas G/D">{lineas_txt(c)}</td><td data-l="Mapa">{maps}</td></tr>')
    return f'<div class="tablewrap"><table class="dir"><thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>'


def municipio_page(name, slug, cs):
    rel = f"municipio/{slug}/"
    nv = sum(1 for c in cs if c["tipo_label"] == "Verificentro")
    np_ = len(cs) - nv
    nd = sum(1 for c in cs if c["tipo_label"] == "Verificentro" and (c["die"] or 0) > 0)
    year = CFG["data_retrieved"][:4]
    title = f"Verificentros en {name} {year}: direcciones y teléfonos | {CFG['site_name']}"
    desc = (f"{nv} verificentros y {np_} talleres PIREC en {name}, Estado de México, con dirección, teléfono, "
            f"líneas de gasolina y diésel y ubicación en Google Maps. Datos oficiales al {fecha_larga(CFG['data_retrieved'])}.")
    cs = sorted(cs, key=lambda c: (c["tipo_label"] != "Verificentro", c["nombre"]))
    body = breadcrumbs([("Inicio", url()), (name, None)])
    body += f"<h1>Verificentros en {e(name)}</h1>\n"
    resumen = f"En {e(name)} hay <strong>{nv}</strong> verificentro{'s' if nv != 1 else ''}"
    resumen += f" (<strong>{nd}</strong> con línea de diésel)" if nv else ""
    resumen += f" y <strong>{np_}</strong> taller{'es' if np_ != 1 else ''} PIREC" if np_ else ""
    resumen += f" registrados en el directorio oficial consultado el {fecha_larga(CFG['data_retrieved'])}."
    body += f'<p class="lead">{resumen}</p>\n'
    body += centers_table(cs)
    body += ('<p>PIREC = taller autorizado para reparar autos que no aprobaron la verificación. '
             '<a href="https://citaverificacion.edomex.gob.mx" rel="noopener">Agenda tu cita de verificación en el sitio oficial</a>.</p>')
    body += cta_html()
    jsonld = {
        "@context": "https://schema.org", "@type": "ItemList", "name": f"Verificentros en {name}",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": BASE_URL + "centro/" + c["slug"] + "/", "name": c["nombre"]}
                            for i, c in enumerate(cs)],
    }
    write(rel, layout(rel, title, desc, body, jsonld))


def home_page(by_mun, centers, guides):
    nv = sum(1 for c in centers if c["tipo_label"] == "Verificentro")
    np_ = len(centers) - nv
    title = f"{CFG['site_name']}: verificentros en el Estado de México por municipio"
    desc = (f"Directorio independiente de {nv} verificentros y {np_} talleres PIREC en {len(by_mun)} municipios del Estado de México, "
            "con dirección, teléfono y mapa. Información sobre verificación y Hoy No Circula con enlaces oficiales.")
    items = []
    for name, slug, cs in by_mun:
        n = len(cs)
        items.append(f'<li data-q="{e(slugify(name).replace("-", " "))}"><a href="{url("municipio/" + slug + "/")}">{e(name)}</a> <span class="n">{n}</span></li>')
    centers_idx = "".join(
        f'<li data-q="{e((slugify(c["nombre"]) + " " + slugify(c["municipio"]) + " " + c["clave"].lower()).replace("-", " "))}" hidden>'
        f'<a href="{url("centro/" + c["slug"] + "/")}">{e(c["nombre"])}</a> <small>{e(c["tipo_label"])} · {e(c["municipio"])}</small></li>'
        for c in sorted(centers, key=lambda c: c["nombre"]))
    guias = ""
    if guides:
        guias = "<h2>Guías recientes</h2><ul>" + "".join(
            f'<li><a href="{url("guias/" + g["slug"] + "/")}">{e(g["title"])}</a></li>' for g in guides[:5]) + "</ul>"
    body = f"""<h1>Verificentros en el Estado de México</h1>
<p class="lead">Encuentra los {nv} verificentros y {np_} talleres PIREC del directorio oficial del Estado de México, organizados por municipio, con dirección, teléfono y mapa.</p>
<section id="municipios">
<label for="q" class="searchlabel">Busca tu municipio o un centro</label>
<input id="q" type="search" placeholder="Ej. Ecatepec, Toluca, Naucalpan…" autocomplete="off">
<ul class="muns" id="muns">{''.join(items)}</ul>
<ul class="centers" id="centers">{centers_idx}</ul>
<p id="empty" hidden>No encontramos resultados. Revisa la ortografía o elige un municipio de la lista.</p>
</section>
<section class="explica">
<h2>¿Qué es la verificación vehicular?</h2>
<p>La verificación vehicular es la revisión obligatoria de emisiones contaminantes de los vehículos que circulan en el Estado de México. Se realiza en verificentros autorizados, con cita, y el periodo que te toca depende de tu placa. Si tu auto no aprueba, puedes repararlo en un taller PIREC autorizado y volver a verificar.</p>
<p>Consulta tu calendario, requisitos y costos vigentes, y agenda tu cita, solo en los sitios oficiales: <a href="https://citaverificacion.edomex.gob.mx" rel="noopener">citaverificacion.edomex.gob.mx</a> y <a href="https://sma.edomex.gob.mx" rel="noopener">Secretaría del Medio Ambiente del Edomex</a>.</p>
<h2>¿Qué es el Hoy No Circula?</h2>
<p>El Hoy No Circula es el programa que restringe la circulación de algunos vehículos ciertos días según su holograma de verificación y su placa, en la Ciudad de México y en municipios conurbados del Estado de México. En contingencias ambientales pueden aplicar restricciones adicionales.</p>
<p>Antes de salir, confirma qué aplica hoy en la fuente oficial: <a href="https://hoynocircula.cdmx.gob.mx/" rel="noopener">hoynocircula.cdmx.gob.mx</a>.</p>
</section>
{guias}
"""
    js = f'<script src="{url("static/app.js")}" defer></script>'
    jsonld = {"@context": "https://schema.org", "@type": "WebSite", "name": CFG["site_name"], "url": BASE_URL, "inLanguage": CFG["lang"]}
    write("", layout("", title, desc, body, jsonld, js))


def parse_md(path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        _, fm, text = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
    html_body = markdown.markdown(text, extensions=["tables", "toc", "sane_lists"])
    if "title" not in meta:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html_body)
        meta["title"] = re.sub("<[^>]+>", "", m.group(1)) if m else path.stem.replace("-", " ").capitalize()
    if "description" not in meta:
        plain = re.sub("<[^>]+>", " ", html_body)
        meta["description"] = re.sub(r"\s+", " ", plain).strip()[:155]
    return meta, html_body


def build_guides():
    guides = []
    for p in sorted((ROOT / "content" / "guias").glob("*.md")):
        if p.name.startswith(("_", ".")) or p.name.lower() == "readme.md":
            continue
        meta, body_html = parse_md(p)
        slug = meta.get("slug") or slugify(p.stem)
        guides.append({"slug": slug, "title": meta["title"], "description": meta["description"],
                       "date": meta.get("date", ""), "html": body_html})
    guides.sort(key=lambda g: (g["date"], g["slug"]), reverse=True)
    for g in guides:
        rel = f"guias/{g['slug']}/"
        body = breadcrumbs([("Inicio", url()), ("Guías", url("guias/")), (g["title"], None)])
        if not re.search(r"<h1", g["html"]):
            body += f"<h1>{e(g['title'])}</h1>"
        if g["date"]:
            body += f'<p class="meta">Publicado: {e(fecha_larga(g["date"]))}</p>'
        body += f'<article class="guia">{g["html"]}</article>'
        jsonld = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"], "inLanguage": CFG["lang"],
                  "mainEntityOfPage": BASE_URL + rel}
        if g["date"]:
            jsonld["datePublished"] = g["date"]
        write(rel, layout(rel, f"{g['title']} | {CFG['site_name']}", g["description"], body, jsonld))
    lis = "".join(f'<li><a href="{url("guias/" + g["slug"] + "/")}">{e(g["title"])}</a>'
                  + (f' <small>{e(fecha_larga(g["date"]))}</small>' if g["date"] else "") + "</li>" for g in guides)
    body = breadcrumbs([("Inicio", url()), ("Guías", None)]) + "<h1>Guías de verificación y Hoy No Circula</h1>"
    body += f"<ul class=\"guias\">{lis}</ul>" if guides else "<p>Muy pronto publicaremos aquí guías prácticas. Mientras tanto, consulta el <a href=\"" + url() + "#municipios\">directorio por municipio</a>.</p>"
    write("guias/", layout("guias/", f"Guías de verificación vehicular | {CFG['site_name']}",
                           "Guías prácticas sobre verificación vehicular, citas, talleres PIREC y Hoy No Circula en el Estado de México.", body))
    return guides


def static_pages():
    body = breadcrumbs([("Inicio", url()), ("Contacto", None)]) + """<h1>Contacto</h1>
<p>¿Eres dueño o encargado de un verificentro o taller PIREC? Muy pronto podrás destacar tu ficha y corregir tus datos desde aquí.</p>
<p>Este sitio no agenda citas ni realiza trámites. Para eso, usa <a href="https://citaverificacion.edomex.gob.mx" rel="noopener">el sistema oficial de citas</a>.</p>"""
    write("contacto/", layout("contacto/", f"Contacto | {CFG['site_name']}", "Contacto para verificentros y talleres PIREC que quieran destacar o corregir su ficha.", body))
    body = breadcrumbs([("Inicio", url()), ("Aviso legal", None)]) + f"""<h1>Aviso legal</h1>
<p>{e(CFG['site_name'])} es un sitio independiente e informativo. No es un sitio oficial ni tiene relación con el Gobierno del Estado de México, la Ciudad de México ni ninguna dependencia.</p>
<p>Los datos de verificentros y talleres PIREC provienen de <a href="{e(CFG['data_source_url'])}" rel="noopener">{e(CFG['data_source_name'])}</a>, consultados el {fecha_larga(CFG['data_retrieved'])}. Pueden contener errores o estar desactualizados; confirma siempre con la autoridad o con el centro antes de acudir.</p>"""
    write("aviso/", layout("aviso/", f"Aviso legal | {CFG['site_name']}", "Aviso legal: sitio independiente y no oficial con datos de fuente pública.", body))
    nf = layout("404.html", f"Página no encontrada | {CFG['site_name']}", "Página no encontrada.",
                f'<h1>Página no encontrada</h1><p><a href="{url()}">Volver al inicio</a></p>')
    (OUT / "404.html").write_text(nf.replace('<link rel="canonical"', '<meta name="robots" content="noindex"><link rel="canonical"', 1), encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")
    shutil.copy(ROOT / CFG["data_file"], OUT / "directorio.csv")
    centers = load_centers()
    groups = defaultdict(list)
    for c in centers:
        groups[(c["municipio"], c["mun_slug"])].append(c)
    by_mun = sorted(((n, s, cs) for (n, s), cs in groups.items()), key=lambda x: slugify(x[0]))
    for c in centers:
        center_page(c)
    for n, s, cs in by_mun:
        municipio_page(n, s, cs)
    guides = build_guides()
    home_page(by_mun, centers, guides)
    static_pages()
    today = date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{e(BASE_URL + p)}</loc><lastmod>{today}</lastmod></url>" for p in sorted(pages)]
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"OK: {len(pages)} páginas ({len(centers)} centros, {len(by_mun)} municipios, {len(guides)} guías) en {OUT}")


if __name__ == "__main__":
    main()
