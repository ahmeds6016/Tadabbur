import { Geist, Geist_Mono, Amiri } from "next/font/google";
import "./globals.css";


// Modern sans-serif font
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

// Monospace font for code
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

// Arabic font for Quranic text
const amiri = Amiri({
  variable: "--font-amiri",
  subsets: ["arabic"],
  weight: ["400", "700"],
  display: "swap",
});

export const metadata = {
  title: "Tafsir Simplified - AI-Powered Quranic Commentary",
  description: "Explore classical Islamic tafsir with AI-powered semantic search across Ibn Kathir, al-Qurtubi, and al-Jalalayn. Personalized Quranic commentary for every knowledge level.",
  keywords: ["tafsir", "quran", "islamic studies", "quranic commentary", "ibn kathir", "al-qurtubi", "al-jalalayn"],
  authors: [{ name: "Tafsir Simplified Team" }],
  openGraph: {
    title: "Tafsir Simplified - AI-Powered Quranic Commentary",
    description: "Explore classical Islamic tafsir with AI-powered semantic search",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Tafsir Simplified",
    description: "AI-Powered Quranic Commentary Platform",
  },
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
  },
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
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
        
        {/* Additional Arabic fonts for Quranic text */}
        <link 
          href="https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
