# Referencia del protagonista

Para que **Replicate (FLUX Kontext)** mantenga la misma cara y cuerpo entre escenas:

1. Guardá tu imagen de referencia (cuerpo completo o tres cuartos, buena luz) como:

   **`character_reference_front.png`**

   en esta carpeta (`references/character_reference/`).

2. En `config/visual_bible.yaml`, la clave `character_reference.front` ya apunta a esa ruta. Podés añadir `side` o `closeup` si agregás más archivos.

3. Si la imagen no existe, el generador sigue con texto solo (o outfit ref si aplica).

**Nota:** Si Cursor guardó tu PNG en `.cursor/projects/.../assets/` con un nombre largo, copiá y renombrá el archivo manualmente a `character_reference_front.png` aquí.
