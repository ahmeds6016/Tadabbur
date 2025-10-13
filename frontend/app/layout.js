import { Geist, Geist_Mono, Amiri } from "next/font/google";
import "./globals.css";

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
  title: "Tafsir Simplified - تفسير مبسط | AI-Powered Islamic Commentary",
  description: "Explore authentic classical Islamic tafsir with AI-powered semantic search. Access insights from Ibn Kathir, al-Qurtubi, and other renowned scholars. Personalized Quranic commentary for every knowledge level - from new Muslims to advanced scholars.",
  keywords: [
    "tafsir", 
    "quran", 
    "islamic studies", 
    "quranic commentary", 
    "ibn kathir", 
    "al-qurtubi",
    "tafsir ibn kathir",
    "islamic learning",
    "quran explanation",
    "arabic quran",
    "quran translation",
    "islamic education",
    "muslim learning",
    "quranic exegesis",
    "تفسير",
    "القرآن"
  ],
  authors: [{ name: "Tafsir Simplified Team" }],
  creator: "Tafsir Simplified",
  publisher: "Tafsir Simplified",
  
  openGraph: {
    title: "Tafsir Simplified - تفسير مبسط",
    description: "AI-powered access to classical Islamic tafsir from Ibn Kathir, al-Qurtubi, and renowned scholars",
    type: "website",
    locale: "en_US",
    alternateLocale: ["ar_SA"],
    siteName: "Tafsir Simplified",
  },
  
  twitter: {
    card: "summary_large_image",
    title: "Tafsir Simplified - Islamic Commentary Platform",
    description: "AI-Powered Classical Quranic Commentary for Modern Learners",
  },
  
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
  },
  
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FDFBF7" },
    { media: "(prefers-color-scheme: dark)", color: "#0F1419" },
  ],
  
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
      { url: '/icon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/icon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
  
  manifest: '/site.webmanifest',
  
  category: 'education',
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
        
        {/* Additional Premium Arabic fonts for Quranic text */}
        <link 
          href="https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Scheherazade+New:wght@400;700&family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap" 
          rel="stylesheet" 
        />
        
        {/* Meta tags for Islamic content */}
        <meta name="format-detection" content="telephone=no" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
      </head>
      <body suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
