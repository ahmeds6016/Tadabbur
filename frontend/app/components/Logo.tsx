import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
}

/**
 * Tafsir Simplified Logo Component
 * Features beautiful Arabic calligraphy "تفسير مبسط" in a circular design
 * Inspired by classical Islamic geometric patterns and calligraphy
 */
export const TafsirLogo: React.FC<LogoProps> = ({
  size = 120,
  className = '',
  showText = true
}) => {
  return (
    <div className={`logo-container ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 240 240"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="logo-svg"
      >
        {/* Outer decorative ring with Islamic pattern */}
        <defs>
          {/* Gradient for the outer ring */}
          <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0D9488" stopOpacity="0.9" />
            <stop offset="50%" stopColor="#D4AF37" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#0D9488" stopOpacity="0.9" />
          </linearGradient>

          {/* Gradient for the inner circle */}
          <radialGradient id="innerGradient" cx="50%" cy="50%">
            <stop offset="0%" stopColor="#FDFBF7" />
            <stop offset="100%" stopColor="#FAF6F0" />
          </radialGradient>

          {/* Gold gradient for calligraphy */}
          <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#B8941F" />
            <stop offset="50%" stopColor="#D4AF37" />
            <stop offset="100%" stopColor="#B8941F" />
          </linearGradient>

          {/* Pattern for Islamic geometric design */}
          <pattern id="islamicPattern" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M20,5 L35,20 L20,35 L5,20 Z"
              fill="none"
              stroke="#D4AF37"
              strokeWidth="0.5"
              opacity="0.3"
            />
            <circle cx="20" cy="20" r="3" fill="#D4AF37" opacity="0.2" />
          </pattern>

          {/* Shadow filter */}
          <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" floodOpacity="0.15" />
          </filter>
        </defs>

        {/* Outer decorative ring */}
        <circle
          cx="120"
          cy="120"
          r="115"
          stroke="url(#ringGradient)"
          strokeWidth="2"
          fill="none"
        />

        {/* Islamic pattern ring */}
        <circle
          cx="120"
          cy="120"
          r="110"
          fill="url(#islamicPattern)"
          opacity="0.5"
        />

        {/* Main circle background */}
        <circle
          cx="120"
          cy="120"
          r="105"
          fill="url(#innerGradient)"
          filter="url(#shadow)"
        />

        {/* Inner decorative border */}
        <circle
          cx="120"
          cy="120"
          r="100"
          stroke="#D4AF37"
          strokeWidth="1"
          fill="none"
          opacity="0.6"
        />

        {/* Top decorative element (bismillah style ornament) */}
        <path
          d="M120,25 Q130,30 140,25 Q135,35 120,38 Q105,35 100,25 Q110,30 120,25"
          fill="#D4AF37"
          opacity="0.8"
        />

        {/* Arabic Calligraphy: تفسير */}
        <g transform="translate(120, 85)">
          {/* تفسير - Tafsir in Arabic */}
          <text
            x="0"
            y="0"
            fontFamily="'Amiri', 'Traditional Arabic', serif"
            fontSize="36"
            fontWeight="700"
            fill="url(#goldGradient)"
            textAnchor="middle"
            style={{ letterSpacing: '2px' }}
          >
            تفسير
          </text>
        </g>

        {/* Arabic Calligraphy: مبسط */}
        <g transform="translate(120, 125)">
          {/* مبسط - Mubassaṭ (Simplified) in Arabic */}
          <text
            x="0"
            y="0"
            fontFamily="'Amiri', 'Traditional Arabic', serif"
            fontSize="32"
            fontWeight="600"
            fill="#0D9488"
            textAnchor="middle"
            style={{ letterSpacing: '1.5px' }}
          >
            مُبَسَّط
          </text>
        </g>

        {/* Decorative dots pattern (traditional Arabic style) */}
        <g opacity="0.4">
          <circle cx="60" cy="120" r="2" fill="#D4AF37" />
          <circle cx="180" cy="120" r="2" fill="#D4AF37" />
          <circle cx="70" cy="100" r="1.5" fill="#D4AF37" />
          <circle cx="170" cy="100" r="1.5" fill="#D4AF37" />
          <circle cx="70" cy="140" r="1.5" fill="#D4AF37" />
          <circle cx="170" cy="140" r="1.5" fill="#D4AF37" />
        </g>

        {/* Bottom decorative flourish */}
        <path
          d="M80,180 Q120,170 160,180"
          stroke="#D4AF37"
          strokeWidth="1.5"
          fill="none"
          opacity="0.6"
        />
        <path
          d="M90,185 Q120,178 150,185"
          stroke="#0D9488"
          strokeWidth="1"
          fill="none"
          opacity="0.5"
        />

        {/* Corner ornaments */}
        <g opacity="0.3">
          <path d="M40,40 L50,40 L40,50 Z" fill="#D4AF37" />
          <path d="M200,40 L200,50 L190,40 Z" fill="#D4AF37" />
          <path d="M40,200 L40,190 L50,200 Z" fill="#D4AF37" />
          <path d="M200,200 L190,200 L200,190 Z" fill="#D4AF37" />
        </g>

        {/* Small English text at bottom */}
        {showText && (
          <text
            x="120"
            y="205"
            fontFamily="'Geist', system-ui, sans-serif"
            fontSize="12"
            fontWeight="500"
            fill="#0D9488"
            textAnchor="middle"
            opacity="0.8"
          >
            TAFSIR SIMPLIFIED
          </text>
        )}
      </svg>

      <style jsx>{`
        .logo-container {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }

        .logo-svg {
          transition: transform 0.3s ease;
        }

        .logo-container:hover .logo-svg {
          transform: scale(1.05);
        }

        @keyframes shimmer {
          0% {
            opacity: 0.8;
          }
          50% {
            opacity: 1;
          }
          100% {
            opacity: 0.8;
          }
        }

        .logo-svg circle,
        .logo-svg path {
          animation: shimmer 3s ease-in-out infinite;
          animation-delay: calc(var(--delay, 0) * 0.1s);
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
    <div className={`logo-simple-container ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="simpleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0D9488" />
            <stop offset="100%" stopColor="#D4AF37" />
          </linearGradient>
        </defs>

        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="48"
          fill="white"
          stroke="url(#simpleGradient)"
          strokeWidth="2"
        />

        {/* Arabic Text: ت (First letter of تفسير) */}
        <text
          x="50"
          y="40"
          fontFamily="'Amiri', serif"
          fontSize="28"
          fontWeight="700"
          fill="#0D9488"
          textAnchor="middle"
        >
          ت
        </text>

        {/* Arabic Text: م (First letter of مبسط) */}
        <text
          x="50"
          y="65"
          fontFamily="'Amiri', serif"
          fontSize="24"
          fontWeight="600"
          fill="#D4AF37"
          textAnchor="middle"
        >
          م
        </text>

        {/* Small decorative dots */}
        <circle cx="30" cy="50" r="1.5" fill="#D4AF37" opacity="0.5" />
        <circle cx="70" cy="50" r="1.5" fill="#D4AF37" opacity="0.5" />
      </svg>

      <style jsx>{`
        .logo-simple-container {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: transform 0.2s ease;
        }

        .logo-simple-container:hover {
          transform: scale(1.1);
        }
      `}</style>
    </div>
  );
};

export default TafsirLogo;