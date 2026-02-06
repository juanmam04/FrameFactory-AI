const path = require('path');
const fs = require('fs');
const { renderVideo } = require('../src/video/renderVideo');

const JOBS_BASE = path.join(__dirname, '../outputs/jobs');
const JOB_ID = 'example';

async function main() {
  const jobDir = path.join(JOBS_BASE, JOB_ID);
  const framesDir = path.join(jobDir, 'frames');
  const voicePath = path.join(jobDir, 'voice.mp3');
  const musicPath = path.join(jobDir, 'music.mp3');
  const outputPath = path.join(jobDir, 'out.mp4');
  const includeMusic = fs.existsSync(musicPath);

  console.log('Job:', JOB_ID);
  console.log('framesDir:', framesDir);
  console.log('voicePath:', voicePath);
  console.log('includeMusic:', includeMusic);

  try {
    const result = await renderVideo({
      framesDir,
      voicePath,
      musicPath: includeMusic ? musicPath : undefined,
      outputPath,
      secondsPerImage: 5,
    });
    console.log('OK:', result);
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
}

main();
