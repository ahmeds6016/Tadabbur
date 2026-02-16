import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
}

/**
 * Tadabbur Logo
 * Circular medallion with gold ornamental border, cream center, dark green Arabic تدبر
 */
export const TadabburLogo: React.FC<LogoProps> = ({
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
          <linearGradient id="goldBorder" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#D4AF37" />
            <stop offset="50%" stopColor="#F4D668" />
            <stop offset="100%" stopColor="#C49B2A" />
          </linearGradient>
          <linearGradient id="darkGold" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8B6914" />
            <stop offset="100%" stopColor="#6B5210" />
          </linearGradient>
          <radialGradient id="creamCenter" cx="50%" cy="45%" r="50%">
            <stop offset="0%" stopColor="#FDF8EE" />
            <stop offset="100%" stopColor="#F5EDDA" />
          </radialGradient>
        </defs>

        {/* Outer cream circle */}
        <circle cx="50" cy="50" r="48" fill="#FAF6F0" />

        {/* Gold ornamental ring — outer */}
        <circle cx="50" cy="50" r="44" fill="url(#goldBorder)" />

        {/* Gold pattern dots around the ring */}
        {Array.from({ length: 24 }).map((_, i) => {
          const angle = (i * 15) * (Math.PI / 180);
          const x = 50 + 41.5 * Math.cos(angle);
          const y = 50 + 41.5 * Math.sin(angle);
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="1"
              fill="#8B6914"
              opacity="0.6"
            />
          );
        })}

        {/* Inner dark border ring */}
        <circle cx="50" cy="50" r="38" fill="#3D2E14" />

        {/* Second gold ring — inner */}
        <circle cx="50" cy="50" r="36" fill="url(#goldBorder)" />

        {/* Cream/parchment center */}
        <circle cx="50" cy="50" r="33" fill="url(#creamCenter)" />

        {/* Arabic تدبر — dark green, centered */}
        <text
          x="50"
          y="57"
          fontFamily="'Amiri', 'Traditional Arabic', serif"
          fontSize="28"
          fontWeight="700"
          fill="#1A5632"
          textAnchor="middle"
        >
          تدبر
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
export const TadabburLogoSimple: React.FC<LogoProps> = ({
  size = 48,
  className = ''
}) => {
  return (
    <TadabburLogo size={size} className={className} showText={false} />
  );
};

// Backward-compatible aliases
export const TafsirLogo = TadabburLogo;
export const TafsirLogoSimple = TadabburLogoSimple;

export default TadabburLogo;
