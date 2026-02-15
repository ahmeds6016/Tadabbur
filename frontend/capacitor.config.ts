import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.tafsirsimplified.app',
  appName: 'Tafsir Simplified',
  webDir: 'out',

  // Load from production server — keeps a single deployment pipeline,
  // supports dynamic routes, and lets you push updates without App Store review.
  server: {
    url: 'https://tafsir-simplified-app.vercel.app',
    cleartext: false,
  },

  ios: {
    scheme: 'tafsirsimplified',
    contentInset: 'automatic',
    backgroundColor: '#FDFBF7',
    preferredContentMode: 'mobile',
    scrollEnabled: true,
  },

  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      launchShowDuration: 2000,
      backgroundColor: '#FDFBF7',
      showSpinner: false,
      splashFullScreen: true,
      splashImmersive: true,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#FDFBF7',
    },
  },
};

export default config;
