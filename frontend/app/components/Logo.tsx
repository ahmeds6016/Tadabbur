import React from 'react';
import Image from 'next/image';

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
    <div className={`logo-container ${className}`} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      <Image
        src="/logo-medallion.png"
        alt="Tadabbur تدبر"
        width={size}
        height={size}
        priority
        style={{ width: size, height: size }}
      />
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
