-- FrameFactory: liberar cuota en Supabase (pegar en SQL Editor cuando el proyecto responda).
-- NO borra final.mp4 ni imágenes ni audio ni project.json.

DELETE FROM ff_blobs WHERE rel_path LIKE 'render/clips/%';
DELETE FROM ff_blobs WHERE rel_path IN (
  'render/final_master.mp4',
  'render/final_captions.mp4',
  'render/final_burn.mp4',
  'render/preview.mp4',
  'render/preview_captions.mp4',
  'render/captions_preview.srt'
);
DELETE FROM ff_blobs WHERE rel_path LIKE '%.thumb.%';
DELETE FROM ff_blobs WHERE rel_path LIKE 'logs/%';

VACUUM (VERBOSE) ff_blobs;

SELECT
  split_part(rel_path, '/', 1) AS top,
  count(*) AS files,
  pg_size_pretty(sum(octet_length(content))::bigint) AS bytes
FROM ff_blobs
GROUP BY 1
ORDER BY sum(octet_length(content)) DESC;
