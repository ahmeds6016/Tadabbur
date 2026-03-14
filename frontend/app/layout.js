import { Geist, Geist_Mono, Amiri } from "next/font/google";
import "./globals.css";
import PWAProvider from "./components/PWAProvider";

// Modern sans-serif font
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

// Monospace font for code
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

// Premium Arabic font for Quranic text
const amiri = Amiri({
  variable: "--font-amiri",
  subsets: ["arabic", "latin"],
  weight: ["400", "700"],
  display: "swap",
});

export const metadata = {
  title: "Tadabbur - تدبّر | Quranic Reflection & Classical Commentary",
  description: "Reflect deeply on the Quran through classical scholarship. Tadabbur synthesizes insights from Ibn Kathir, al-Qurtubi, and five additional scholarly works — personalized to your learning journey.",
  keywords: [
    "tadabbur",
    "تدبّر",
    "tafsir",
    "quran",
    "quran reflection",
    "islamic studies",
    "quranic commentary",
    "ibn kathir",
    "al-qurtubi",
    "islamic learning",
    "quran explanation",
    "arabic quran",
    "islamic education",
    "quranic exegesis",
    "تفسير",
    "القرآن"
  ],
  authors: [{ name: "Tadabbur" }],
  creator: "Tadabbur",
  publisher: "Tadabbur",

  openGraph: {
    title: "Tadabbur - تدبّر",
    description: "Deep Quranic reflection through classical scholarship — personalized to your journey",
    type: "website",
    locale: "en_US",
    alternateLocale: ["ar_SA"],
    siteName: "Tadabbur",
  },

  twitter: {
    card: "summary_large_image",
    title: "Tadabbur - Quranic Reflection Platform",
    description: "Deep Quranic reflection through classical scholarship",
  },

  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },

  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/icons/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/icons/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
    ],
    apple: [
      { url: '/icons/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },

  manifest: '/manifest.json',

  category: 'education',
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: 'cover', // For iPhone notch support
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FDFBF7" },
    { media: "(prefers-color-scheme: dark)", color: "#0F1419" },
  ],
};

export default function RootLayout({ children }) {
  return (
    <html 
      lang="en" 
      className={`${geistSans.variable} ${geistMono.variable} ${amiri.variable}`}
    >
      <head>
        {/* Preconnect to Google Fonts for better performance */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        
        {/* Meta tags for Islamic content */}
        <meta name="format-detection" content="telephone=no" />
        <meta name="color-scheme" content="light dark" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content="Tadabbur" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="mobile-web-app-capable" content="yes" />
      </head>
      <body suppressHydrationWarning>
        <PWAProvider>
          {children}
        </PWAProvider>
      </body>
    </html>
  );
}
