const express = require('express');
const router = express.Router();
const { generateImage } = require('../services/comfyService');

router.post('/generate-image', async (req, res) => {
  try {
    const { prompt, negativePrompt } = req.body;

    if (!prompt) {
      return res.status(400).json({ error: 'Prompt requerido' });
    }

    const result = await generateImage(prompt, negativePrompt);

    res.json({
      success: true,
      comfy_response: result,
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error generando imagen' });
  }
});

module.exports = router;
