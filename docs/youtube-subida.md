# Subida a YouTube (conector MCP)

La oficina CHECK sube los Shorts terminados con el conector de FrameFactory, usando la API oficial de YouTube.

## Configuración (una sola vez)

1. En https://console.cloud.google.com creá un proyecto y activá **YouTube Data API v3**.
2. En **Pantalla de consentimiento de OAuth** elegí "Externo", completá nombre y correo, y en **Usuarios de prueba** agregá la cuenta de Google dueña del canal.
3. En **Credenciales**, creá un **ID de cliente OAuth** de tipo "Aplicación web". En "URI de redireccionamiento autorizados" poné:
   `https://<tu-dominio-de-vercel>/youtube/callback`
4. En Vercel (Settings → Environment Variables) cargá `YT_CLIENT_ID` y `YT_CLIENT_SECRET`, y hacé Redeploy.
5. Abrí `https://<tu-dominio-de-vercel>/youtube/conectar/<FF_MCP_TOKEN>`, entrá con la cuenta del canal y aceptá.
6. La página te muestra el `YT_REFRESH_TOKEN`: cargalo en Vercel y hacé Redeploy.
7. Para probar, usá la herramienta `youtube_estado`. Tiene que decir el nombre del canal.

## Límites

- Mientras el proyecto no pase la auditoría de YouTube, **todo lo subido por la API queda privado**, aunque se pida público o programado. Para pedir la auditoría se usa el formulario "YouTube API Services - Audit and Quota Extension".
- Con la app en modo "Prueba", Google vence el permiso a los 7 días y hay que repetir el paso 5. Para que no venza, publicá la app en la pantalla de consentimiento (no hace falta verificación para uso propio, Google muestra una advertencia al conectar).
- Cuota diaria por defecto: 10.000 unidades. Cada subida gasta unas 1.600, así que entran unas 6 por día.

## Herramientas

- `youtube_estado`: canal conectado.
- `youtube_iniciar_subida`: título, descripción, etiquetas, privacidad, `publicar_en` (ISO con zona) y `bytes`. Devuelve `upload_url`.
- `youtube_subir_parte`: manda el MP4 en partes de 1 o 2 MB (múltiplo de 256 KB salvo la última).
- `youtube_cambiar_privacidad`: pasa un video a público, oculto o programado.
