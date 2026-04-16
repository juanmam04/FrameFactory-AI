# Referencia del protagonista (Kontext)

Para que **Replicate (FLUX Kontext)** use tu personaje real como `input_image`:

1. Colocá el PNG en la raíz del repo, carpeta **`character_reference/`** (mismo lugar donde la app Streamlit sube archivos), por ejemplo:

   **`character_reference/character_reference_front.png`**

2. En `config/visual_bible.yaml`, `character_reference.front` debe apuntar a esa ruta relativa (p. ej. `character_reference/character_reference_front.png`).

3. Si el archivo **no existe** o la ruta no coincide con la YAML, el generador usa **solo texto** y el modelo inventa otro diseño de personaje.

**Nota:** La carpeta `references/character_reference/` (solo con este README) no es donde busca el código por defecto; antes la YAML apuntaba ahí y muchas pruebas parecían “mal” porque Kontext nunca veía el PNG.
