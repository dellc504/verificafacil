# VerificaFácil

Directorio **independiente y no oficial** de verificentros y talleres PIREC del Estado de México, con información sobre verificación y Hoy No Circula.

Sitio: https://dellc504.github.io/verificafacil/

## Cómo funciona

- `data/directorio.csv`: datos de los centros (fuente oficial: https://datos-abiertos.edomex.gob.mx/index.php/verificentros/csv2, consultada el 2026-11-18). Para actualizar, reemplaza el CSV y cambia `data_retrieved` en `config.json`.
- `content/guias/<slug>.md`: cada guía en Markdown se publica en `/guias/<slug>/` (ver `content/guias/README.md`).
- `config.json`: nombre del sitio, URL base, fuente de datos, contacto del botón "Destaca tu ficha" (placeholder) y espacio de anuncios (inactivo).
- `build.py`: genera el sitio en `_site/` (inicio, una página por municipio, una por centro, guías, sitemap.xml y robots.txt).
- `.github/workflows/deploy.yml`: en cada push a `main` construye y publica en GitHub Pages.

## Local

```
pip install -r requirements.txt
python build.py
python -m http.server -d _site 8000   # las rutas usan /verificafacil/, así que abre las páginas vía el sitio publicado o ajusta base_url
```

Nunca se inventan datos: toda la información de centros viene del CSV.
