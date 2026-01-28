import type { CapacitorConfig } from "@capacitor/cli";

// Optional dev-only live reload / external hosting (leave empty for Play Store builds)
const CAP_SERVER_URL = (process.env.CAP_SERVER_URL || "").trim();

// Enable HTTP during dev ONLY (Android emulator -> http://10.0.2.2:8000)
const DEV_ALLOW_HTTP = (process.env.CAP_DEV_ALLOW_HTTP || "").trim() === "1";

// Your emulator backend host (Android)
const DEV_ANDROID_HOST = (process.env.CAP_DEV_ANDROID_HOST || "10.0.2.2").trim();

const config: CapacitorConfig = {
  appId: "com.mkaru.teenzen",
  appName: "TeenZen",
  webDir: "dist",
  bundledWebRuntime: false,

  /**
   * 🚫 IMPORTANT
   * Do NOT set `server.url` for production builds.
   * If CAP_SERVER_URL is empty, Capacitor loads the bundled frontend from /dist.
   */
  ...(CAP_SERVER_URL
    ? {
        server: {
          url: CAP_SERVER_URL,
          cleartext: CAP_SERVER_URL.startsWith("http://"),
          // Allow navigation to the dev host (helps Android WebView)
          ...(DEV_ALLOW_HTTP
            ? { allowNavigation: [DEV_ANDROID_HOST, "localhost", "127.0.0.1"] }
            : {}),
        },
      }
    : {
        // No live reload: app loads bundled dist.
        // Still allow cleartext + navigation in DEV if you need HTTP backend access.
        ...(DEV_ALLOW_HTTP
          ? {
              server: {
                cleartext: true,
                allowNavigation: [DEV_ANDROID_HOST, "localhost", "127.0.0.1"],
              },
            }
          : {}),
      }),

  android: {
    /**
     * ✅ Dev-only: allow HTTP content for backend calls.
     * Set:
     *   CAP_DEV_ALLOW_HTTP=1
     */
    allowMixedContent: DEV_ALLOW_HTTP,
  },

  ios: {
    contentInset: "automatic",
  },

  plugins: {
    SplashScreen: {
      launchShowDuration: 0,
    },
    Keyboard: {
      resize: "body",
      style: "dark",
    },
  },
};

export default config;
