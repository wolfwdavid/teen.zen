// app.config.js
import 'dotenv/config';

export default {
  expo: {
    name: 'my-landing-page',
    slug: 'my-landing-page',
    version: '1.0.0',
    orientation: 'portrait',
    extra: {
      googleApiKey: process.env.GOOGLE_API_KEY,
    },
  },
};
