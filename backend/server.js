require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });
const express = require('express');
const videoRouter = require('./src/routes/video');
const aiRoutes = require('./routes/aiRoutes');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use('/api/video', videoRouter);
app.use('/api/ai', aiRoutes);

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
