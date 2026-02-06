const express = require('express');
const path = require('path');
const fs = require('fs');
const { renderVideo } = require('../video/renderVideo');

const router = express.Router();
const JOBS_BASE = path.join(__dirname, '../../outputs/jobs');

/**
 * POST /api/video/render
 * Body: { jobId: string, secondsPerImage?: number, includeMusic?: boolean }
 * Responde: { ok: true, outputPath, sizeBytes } o error 400/500
 */
router.post('/render', async (req, res) => {
  try {
    const { jobId, secondsPerImage = 5, includeMusic = false } = req.body || {};

    if (!jobId || typeof jobId !== 'string') {
      return res.status(400).json({ ok: false, error: 'jobId es obligatorio' });
    }

    const jobDir = path.join(JOBS_BASE, jobId);
    const framesDir = path.join(jobDir, 'frames');
    const voicePath = path.join(jobDir, 'voice.mp3');
    const musicPath = path.join(jobDir, 'music.mp3');
    const outputPath = path.join(jobDir, 'out.mp4');

    if (!fs.existsSync(jobDir)) {
      return res.status(400).json({ ok: false, error: `Job no existe: ${jobId}` });
    }
    if (!fs.existsSync(framesDir)) {
      return res.status(400).json({ ok: false, error: `Carpeta frames no existe en el job: ${jobId}` });
    }
    if (!fs.existsSync(voicePath)) {
      return res.status(400).json({ ok: false, error: `voice.mp3 no existe en el job: ${jobId}` });
    }

    const musicPathToUse = includeMusic && fs.existsSync(musicPath) ? musicPath : undefined;

    const result = await renderVideo({
      framesDir,
      voicePath,
      musicPath: musicPathToUse,
      outputPath,
      secondsPerImage: Number(secondsPerImage) || 5,
    });

    return res.json({
      ok: true,
      outputPath: result.outputPath,
      sizeBytes: result.sizeBytes,
    });
  } catch (err) {
    const message = err.message || 'Error al renderizar video';
    const status = message.includes('no existe') || message.includes('obligatorio') ? 400 : 500;
    return res.status(status).json({ ok: false, error: message });
  }
});

module.exports = router;
