const axios = require('axios');

const COMFY_URL = (process.env.COMFYUI_URL || 'http://127.0.0.1:8188').replace(/\/$/, '');
const COMFY_CHECKPOINT = process.env.COMFYUI_CHECKPOINT || 'v1-5-pruned-emaonly.safetensors';
const COMFY_TIMEOUT_MS = parseInt(process.env.COMFYUI_TIMEOUT_POST || '90000', 10);

async function generateImage(promptText, negativePrompt = '') {
  const workflow = {
    prompt: {
      '3': {
        class_type: 'CheckpointLoaderSimple',
        inputs: {
          ckpt_name: COMFY_CHECKPOINT,
        },
      },
      '4': {
        class_type: 'CLIPTextEncode',
        inputs: {
          text: promptText,
          clip: ['3', 1],
        },
      },
      '5': {
        class_type: 'CLIPTextEncode',
        inputs: {
          text: negativePrompt || 'blurry, low quality, bad anatomy',
          clip: ['3', 1],
        },
      },
      '6': {
        class_type: 'EmptyLatentImage',
        inputs: {
          width: 512,
          height: 512,
          batch_size: 1,
        },
      },
      '7': {
        class_type: 'KSampler',
        inputs: {
          model: ['3', 0],
          positive: ['4', 0],
          negative: ['5', 0],
          latent_image: ['6', 0],
          seed: Math.floor(Math.random() * 999999),
          steps: 20,
          cfg: 8,
          sampler_name: 'euler',
          scheduler: 'normal',
          denoise: 1.0,
        },
      },
      '8': {
        class_type: 'VAEDecode',
        inputs: {
          samples: ['7', 0],
          vae: ['3', 2],
        },
      },
      '9': {
        class_type: 'SaveImage',
        inputs: {
          filename_prefix: 'api_gen',
          images: ['8', 0],
        },
      },
    },
  };

  const response = await axios.post(`${COMFY_URL}/prompt`, { prompt: workflow.prompt }, { timeout: COMFY_TIMEOUT_MS });
  return response.data;
}

module.exports = { generateImage };
