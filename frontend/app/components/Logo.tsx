import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
}

/**
 * Tafsir Simplified Logo
 * Clean, modern rounded-square with open book motif and Arabic letter
 */
export const TafsirLogo: React.FC<LogoProps> = ({
  size = 120,
  className = '',
}) => {
  return (
    <div className={`logo-container ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="logo-svg"
      >
        <defs>
          <linearGradient id="logoBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0D9488" />
            <stop offset="100%" stopColor="#0F766E" />
          </linearGradient>
          <linearGradient id="logoAccent" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#D4AF37" />
            <stop offset="100%" stopColor="#C49B2A" />
          </linearGradient>
        </defs>

        {/* Rounded square background */}
        <rect
          x="2" y="2" width="96" height="96"
          rx="22"
          fill="url(#logoBg)"
        />

        {/* Open book shape — two pages */}
        <path
          d="M50 28 C50 28 34 30 22 36 L22 72 C34 66 50 64 50 64"
          fill="white"
          fillOpacity="0.15"
        />
        <path
          d="M50 28 C50 28 66 30 78 36 L78 72 C66 66 50 64 50 64"
          fill="white"
          fillOpacity="0.2"
        />

        {/* Book spine */}
        <line
          x1="50" y1="28" x2="50" y2="64"
          stroke="white"
          strokeWidth="1.5"
          strokeOpacity="0.3"
        />

        {/* Arabic تفسير — top line */}
        <text
          x="50"
          y="48"
          fontFamily="'Amiri', 'Traditional Arabic', serif"
          fontSize="22"
          fontWeight="700"
          fill="white"
          textAnchor="middle"
        >
          تفسير
        </text>

        {/* Arabic مبسط — bottom line, gold accent */}
        <text
          x="50"
          y="68"
          fontFamily="'Amiri', 'Traditional Arabic', serif"
          fontSize="18"
          fontWeight="600"
          fill="url(#logoAccent)"
          textAnchor="middle"
        >
          مُبَسَّط
        </text>
      </svg>

      <style jsx>{`
        .logo-container {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }

        .logo-svg {
          transition: transform 0.2s ease;
        }
      `}</style>
    </div>
  );
};

/**
 * Simplified logo variant for headers/navigation
 */
export const TafsirLogoSimple: React.FC<LogoProps> = ({
  size = 48,
  className = ''
}) => {
  return (
    <TafsirLogo size={size} className={className} showText={false} />
  );
};

export default TafsirLogo;
