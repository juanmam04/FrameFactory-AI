const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const VIDEO_FILTER = 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2';

/**
 * Renderiza video desde frames + voz + música opcional.
 * @param {{
 *   framesDir: string,
 *   voicePath: string,
 *   musicPath?: string,
 *   outputPath: string,
 *   secondsPerImage?: number,
 *   ffmpegPath?: string
 * }} opts
 * @returns {Promise<{ outputPath: string, sizeBytes: number }>}
 */
async function renderVideo(opts) {
  const {
    framesDir,
    voicePath,
    musicPath,
    outputPath,
    secondsPerImage = 5,
    ffmpegPath,
  } = opts;

  const ffmpegBin = process.env.FFMPEG_PATH || ffmpegPath || 'ffmpeg';
  if (process.env.DEBUG_RENDER) {
    console.log('[DEBUG_RENDER] ffmpegPath:', ffmpegBin);
    console.log('[DEBUG_RENDER] process.env.PATH:', process.env.PATH);
  }

  if (!framesDir || !fs.existsSync(framesDir)) {
    throw new Error(`framesDir no existe: ${framesDir}`);
  }
  if (!voicePath || !fs.existsSync(voicePath)) {
    throw new Error(`voicePath no existe: ${voicePath}`);
  }
  if (musicPath != null && musicPath !== '' && !fs.existsSync(musicPath)) {
    throw new Error(`musicPath no existe: ${musicPath}`);
  }

  const framesPattern = path.join(framesDir, '%04d.png');
  const inputFramerate = 1 / secondsPerImage;
  const hasMusic = musicPath && fs.existsSync(musicPath);

  const args = [];

  if (hasMusic) {
    // Entradas: [0] frames, [1] voz, [2] música
    args.push(
      '-y',
      '-framerate', String(inputFramerate),
      '-i', framesPattern,
      '-i', voicePath,
      '-i', musicPath,
      '-filter_complex',
      [
        '[1]volume=1[v1]',
        '[2]volume=0.15[v2]',
        '[v1][v2]amix=inputs=2:duration=first:dropout_transition=2[a]',
        `[0]${VIDEO_FILTER}[v]`,
        '[v][a]'
      ].join(';'),
      '-map', '[v]',
      '-map', '[a]',
      '-shortest',
      '-c:v', 'libx264',
      '-pix_fmt', 'yuv420p',
      '-r', '30',
      '-c:a', 'aac',
      '-b:a', '192k',
      outputPath
    );
  } else {
    args.push(
      '-y',
      '-framerate', String(inputFramerate),
      '-i', framesPattern,
      '-i', voicePath,
      '-vf', VIDEO_FILTER,
      '-c:v', 'libx264',
      '-pix_fmt', 'yuv420p',
      '-r', '30',
      '-c:a', 'aac',
      '-b:a', '192k',
      '-shortest',
      outputPath
    );
  }

  return new Promise((resolve, reject) => {
    const proc = spawn(ffmpegBin, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stderr = '';

    proc.stderr.on('data', (chunk) => { stderr += chunk; });
    proc.on('error', (err) => {
      if (err.code === 'ENOENT') {
        reject(new Error('FFmpeg no encontrado. En macOS Homebrew suele estar en /opt/homebrew/bin/ffmpeg. Seteá FFMPEG_PATH.'));
      } else {
        reject(err);
      }
    });
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`FFmpeg falló (code ${code}): ${stderr.slice(-500)}`));
        return;
      }
      const sizeBytes = fs.existsSync(outputPath) ? fs.statSync(outputPath).size : 0;
      resolve({ outputPath, sizeBytes });
    });
  });
}

module.exports = { renderVideo };
