import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.TeenZen.app',
  appName: 'Teen Zen',
  webDir: 'dist',
  server: {
    // Allow mixed content (http API from https webview)
    androidScheme: 'https',
    iosScheme: 'https',
    // Uncomment for live reload during development:
    // url: 'http://10.20.50.249:5173',
    // cleartext: true,
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#09090b',
      showSpinner: false,
      androidSpinnerStyle: 'small',
      splashFullScreen: true,
      splashImmersive: true,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#09090b',
    },
  },
  ios: {
    contentInset: 'automatic',
    preferredContentMode: 'mobile',
    backgroundColor: '#09090b',
  },
  android: {
    backgroundColor: '#09090b',
    allowMixedContent: true,
  },
};

export default config;