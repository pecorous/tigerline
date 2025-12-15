import { format, parseISO } from 'date-fns';

interface HeroSectionProps {
  score: number;
  conditionsText: string;
  boardRec: {
    primary: string;
    size_range: string;
  };
  skillLevel: {
    recommended: string;
  };
  lastUpdated: string;
  buoyStation: string;
  forecastHours: number;
}

export default function HeroSection({
  score,
  conditionsText,
  boardRec,
  skillLevel,
  lastUpdated,
  buoyStation,
  forecastHours
}: HeroSectionProps) {
  const getScoreClass = (score: number): string => {
    if (score >= 7) return 'high';
    if (score >= 4) return 'mid';
    return 'low';
  };

  const getScoreText = (score: number): string => {
    return `${score.toFixed(1)}/10`;
  };

  return (
    <div style={{
      background: '#FFFFFF',
      borderBottom: '1px solid #E0E0E0',
      padding: '32px 0'
    }}>
      <div className="container">
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: '32px',
          flexWrap: 'wrap'
        }}>
          {/* Left side - Title and Meta */}
          <div style={{ flex: '1 1 400px', minWidth: '300px' }}>
            <h1 style={{
              fontSize: '2rem',
              fontWeight: '700',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '8px',
              color: '#111'
            }}>
              16th Ave Belmar Surf Forecast
            </h1>
            <div style={{
              fontSize: '1rem',
              color: '#666',
              marginBottom: '12px'
            }}>
              Live physics-based forecast for 16th Ave, Belmar, NJ
            </div>
            <div style={{
              fontSize: '0.875rem',
              color: '#999',
              display: 'flex',
              gap: '12px',
              flexWrap: 'wrap'
            }}>
              <span>Last updated: {format(parseISO(lastUpdated), 'MMM dd, HH:mm')}</span>
              <span>·</span>
              <span>Buoy {buoyStation}</span>
              <span>·</span>
              <span>{forecastHours}h forecast</span>
            </div>
          </div>

          {/* Right side - Score Badge and Conditions */}
          <div style={{
            display: 'flex',
            gap: '24px',
            alignItems: 'center',
            flex: '1 1 400px',
            justifyContent: 'flex-end'
          }}>
            {/* Score Badge */}
            <div
              className={`score-badge ${getScoreClass(score)}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '120px',
                height: '120px',
                borderRadius: '50%',
                fontSize: '2.5rem',
                fontWeight: '700',
                color: 'white',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                flexShrink: 0
              }}
            >
              {getScoreText(score)}
            </div>

            {/* Conditions Summary */}
            <div style={{ maxWidth: '400px' }}>
              <div style={{
                fontSize: '1.125rem',
                fontWeight: '600',
                marginBottom: '12px',
                color: '#111',
                lineHeight: '1.4'
              }}>
                {conditionsText}
              </div>
              <div style={{
                fontSize: '0.9375rem',
                color: '#666',
                marginBottom: '4px'
              }}>
                <strong style={{ color: '#FF7A1A' }}>Board:</strong> {boardRec.primary} {boardRec.size_range}
              </div>
              <div style={{
                fontSize: '0.875rem',
                color: '#666'
              }}>
                Best for {skillLevel.recommended.toLowerCase()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

