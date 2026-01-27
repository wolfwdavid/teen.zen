import type { CapacitorConfig } from "@capacitor/cli";

// Optional dev-only live reload / external hosting (leave empty for Play Store builds)
const CAP_SERVER_URL = (process.env.CAP_SERVER_URL || "").trim();

// If you're using an HTTP backend during dev, enable this explicitly
const DEV_ALLOW_HTTP = (process.env.CAP_DEV_ALLOW_HTTP || "").trim() === "1";

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
        },
      }
    : {}),

  android: {
    /**
     * ✅ Play Store safe default: false
     * Turn on only for dev HTTP testing by setting:
     *   CAP_DEV_ALLOW_HTTP=1
     */
    allowMixedContent: DEV_ALLOW_HTTP,
    // Some Capacitor versions also support:
    // cleartext: DEV_ALLOW_HTTP,
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
