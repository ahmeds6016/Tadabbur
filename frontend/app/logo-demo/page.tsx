'use client';

import { TafsirLogo, TafsirLogoSimple } from '../components/Logo';

/**
 * Logo Demo Page
 * Shows different variations and sizes of the Tafsir Simplified logo
 */
export default function LogoDemoPage() {
  return (
    <div className="logo-demo-page">
      <div className="container">
        <h1>Tafsir Simplified Logo Showcase</h1>
        <p className="subtitle">Beautiful Arabic calligraphy with classical Islamic design</p>

        {/* Main Logo Section */}
        <section className="logo-section">
          <h2>Main Logo</h2>
          <div className="logo-display">
            <TafsirLogo size={240} />
          </div>
          <div className="arabic-text">
            <p>تفسير مُبَسَّط</p>
            <p className="transliteration">Tafsīr Mubaṣṣaṭ</p>
          </div>
        </section>

        {/* Size Variations */}
        <section className="logo-section">
          <h2>Size Variations</h2>
          <div className="size-grid">
            <div className="size-item">
              <TafsirLogo size={80} showText={false} />
              <span>80px</span>
            </div>
            <div className="size-item">
              <TafsirLogo size={120} />
              <span>120px</span>
            </div>
            <div className="size-item">
              <TafsirLogo size={160} />
              <span>160px</span>
            </div>
            <div className="size-item">
              <TafsirLogo size={200} />
              <span>200px</span>
            </div>
          </div>
        </section>

        {/* Simple Logo Variant */}
        <section className="logo-section">
          <h2>Simple Logo (For Navigation)</h2>
          <div className="simple-grid">
            <div className="simple-item">
              <TafsirLogoSimple size={32} />
              <span>32px</span>
            </div>
            <div className="simple-item">
              <TafsirLogoSimple size={48} />
              <span>48px</span>
            </div>
            <div className="simple-item">
              <TafsirLogoSimple size={64} />
              <span>64px</span>
            </div>
          </div>
        </section>

        {/* Color Backgrounds */}
        <section className="logo-section">
          <h2>On Different Backgrounds</h2>
          <div className="background-grid">
            <div className="bg-item bg-white">
              <TafsirLogo size={120} showText={false} />
              <span>White</span>
            </div>
            <div className="bg-item bg-cream">
              <TafsirLogo size={120} showText={false} />
              <span>Cream</span>
            </div>
            <div className="bg-item bg-teal">
              <TafsirLogo size={120} showText={false} />
              <span>Teal</span>
            </div>
            <div className="bg-item bg-dark">
              <TafsirLogo size={120} showText={false} />
              <span>Dark</span>
            </div>
          </div>
        </section>

        {/* Usage Examples */}
        <section className="logo-section">
          <h2>Usage Examples</h2>
          <div className="usage-examples">
            <div className="example-card">
              <div className="header-example">
                <TafsirLogoSimple size={40} />
                <span className="app-name">Tafsir Simplified</span>
              </div>
              <p>Navigation Header</p>
            </div>

            <div className="example-card">
              <div className="loading-example">
                <TafsirLogo size={100} showText={false} />
                <div className="loading-text">Loading...</div>
              </div>
              <p>Loading State</p>
            </div>

            <div className="example-card">
              <div className="splash-example">
                <TafsirLogo size={180} />
              </div>
              <p>Splash Screen</p>
            </div>
          </div>
        </section>
      </div>

      <style jsx>{`
        .logo-demo-page {
          min-height: 100vh;
          background: linear-gradient(135deg, #FDFBF7 0%, #FAF6F0 100%);
          padding: 40px 20px;
          font-family: 'Geist Sans', system-ui, sans-serif;
        }

        .container {
          max-width: 1200px;
          margin: 0 auto;
        }

        h1 {
          text-align: center;
          color: #0D9488;
          font-size: 2.5rem;
          margin-bottom: 10px;
          font-weight: 800;
        }

        .subtitle {
          text-align: center;
          color: #64748B;
          font-size: 1.1rem;
          margin-bottom: 60px;
        }

        .logo-section {
          margin-bottom: 80px;
        }

        .logo-section h2 {
          color: #1E3A5F;
          font-size: 1.8rem;
          margin-bottom: 30px;
          text-align: center;
          font-weight: 700;
        }

        .logo-display {
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 40px;
          background: white;
          border-radius: 20px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }

        .arabic-text {
          text-align: center;
          margin-top: 30px;
        }

        .arabic-text p {
          font-family: 'Amiri', serif;
          font-size: 2rem;
          color: #0D9488;
          margin: 10px 0;
        }

        .transliteration {
          font-size: 1rem !important;
          color: #64748B !important;
          font-style: italic;
          font-family: 'Georgia', serif !important;
        }

        .size-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 30px;
        }

        .size-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 15px;
          padding: 30px;
          background: white;
          border-radius: 16px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .size-item span {
          color: #64748B;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .simple-grid {
          display: flex;
          gap: 40px;
          justify-content: center;
          flex-wrap: wrap;
        }

        .simple-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
          padding: 20px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }

        .simple-item span {
          color: #64748B;
          font-size: 0.85rem;
        }

        .background-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 20px;
        }

        .bg-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 15px;
          padding: 30px;
          border-radius: 16px;
          position: relative;
        }

        .bg-item span {
          position: absolute;
          bottom: 10px;
          left: 50%;
          transform: translateX(-50%);
          color: #64748B;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .bg-white {
          background: white;
          box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .bg-cream {
          background: #FAF6F0;
        }

        .bg-teal {
          background: #0D9488;
        }

        .bg-teal span {
          color: white;
        }

        .bg-dark {
          background: #1E3A5F;
        }

        .bg-dark span {
          color: white;
        }

        .usage-examples {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 30px;
        }

        .example-card {
          background: white;
          border-radius: 16px;
          padding: 30px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .example-card p {
          margin-top: 20px;
          text-align: center;
          color: #64748B;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .header-example {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 20px;
          background: #FDFBF7;
          border-radius: 12px;
        }

        .app-name {
          font-size: 1.1rem;
          font-weight: 600;
          color: #0D9488;
        }

        .loading-example {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
          padding: 30px;
        }

        .loading-text {
          color: #0D9488;
          font-weight: 500;
          animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }

        .splash-example {
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 40px;
          background: linear-gradient(135deg, #FDFBF7 0%, #FAF6F0 100%);
          border-radius: 12px;
        }

        @media (max-width: 640px) {
          h1 {
            font-size: 2rem;
          }

          .size-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .background-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
      `}</style>
    </div>
  );
}