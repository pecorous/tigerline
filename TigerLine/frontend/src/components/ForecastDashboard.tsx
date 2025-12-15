import { useState } from 'react';
import { format, parseISO, isPast } from 'date-fns';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import styles from '../styles/surf.module.css';

interface ForecastEntry {
  timestamp: string;
  surf_score: number;
  breaking_wave_height_ft: number;
  breaking_wave_height_m: number;
  period_s: number;
  wind: {
    speed_ms: number;
    speed_mph: number;
    direction_deg: number;
    type: string;
  };
  tide: {
    level_m: number;
    level_ft: number;
  };
  sub_scores?: {
    height: number;
    period: number;
    direction: number;
    wind: number;
    tide: number;
  };
  board_recommendation?: {
    primary: string;
    size_range: string;
    reasoning: string;
  };
  condition_descriptor?: string;
  recommendation?: string;
}

interface BestWindow {
  start_time: string;
  end_time: string;
  average_score: number;
  wave_height_ft: number;
  wind_type: string;
  wind_speed_ms: number;
}

interface Props {
  forecast: ForecastEntry[];
  bestTimeWindows?: BestWindow[];
}

export default function ForecastDashboard({ forecast, bestTimeWindows }: Props) {
  const [activeTab, setActiveTab] = useState<'score' | 'height' | 'wind' | 'subscores'>('score');
  const [showDetailedTable, setShowDetailedTable] = useState(false);
  
  if (!forecast || forecast.length === 0) {
    return <div className={styles.container}>No forecast data available.</div>;
  }

  const current = forecast[0];

  // Helper: Get score color class
  const getScoreClass = (score: number): string => {
    if (score < 4) return styles.scoreBad;
    if (score < 7) return styles.scoreMedium;
    return styles.scoreGood;
  };

  // Helper: Get score color for text/badges
  const getScoreColor = (score: number): string => {
    if (score < 4) return '#6B7280';
    if (score < 7) return '#F59E0B';
    return '#FF7A1A';
  };

  // Helper: Generate conditions blurb
  const getConditionsBlurb = (entry: ForecastEntry): string => {
    const score = entry.surf_score;
    const height = entry.breaking_wave_height_ft;
    const windType = entry.wind.type;
    const windSpeed = entry.wind.speed_mph;
    const period = entry.period_s;

    // Wind description
    let windDesc = '';
    if (windType === 'offshore') {
      windDesc = windSpeed < 5 ? 'clean offshore' : 'offshore';
    } else if (windType === 'onshore') {
      windDesc = windSpeed < 5 ? 'light onshore' : 'bumpy onshore';
    } else {
      windDesc = windSpeed < 5 ? 'light cross-shore' : 'cross-shore';
    }

    // Size description
    let sizeDesc = '';
    if (height < 2) sizeDesc = 'knee-high';
    else if (height < 3) sizeDesc = '1-2 ft';
    else if (height < 4) sizeDesc = 'waist-high';
    else if (height < 5) sizeDesc = 'chest-high';
    else if (height < 6) sizeDesc = 'shoulder-head';
    else sizeDesc = 'overhead';

    // Score-based blurb
    if (score < 2) {
      return `Flat / not worth it. ${sizeDesc} with ${windDesc}.`;
    } else if (score < 4) {
      return `Marginal. ${sizeDesc}, ${windDesc} – rideable but not exciting.`;
    } else if (score < 6) {
      return `OK surf. ${sizeDesc} with ${windDesc}; fun if you're keen.`;
    } else if (score < 8) {
      return `Good beachbreak. ${sizeDesc}, ${windDesc}, decent shape for 16th.`;
    } else {
      return `Excellent conditions for 16th Ave – expect strong, hollow surf.`;
    }
  };

  // Helper: Generate board recommendation
  const getBoardRec = (entry: ForecastEntry): string => {
    const height = entry.breaking_wave_height_ft;
    const period = entry.period_s;

    if (height < 2) {
      return 'Longboard or foamie · Best for beginners/intermediates';
    } else if (height < 4) {
      return 'Funboard / mid-length · Best for intermediates';
    } else if (height < 6) {
      return 'Shortboard · Best for confident surfers';
    } else {
      return 'Step-up shortboard · Advanced surfers only';
    }
  };

  // Helper: Get "call" for table
  const getCall = (entry: ForecastEntry): string => {
    const score = entry.surf_score;
    const height = entry.breaking_wave_height_ft;
    const windType = entry.wind.type;

    let sizeHint = '';
    if (height < 2) sizeHint = 'knee-high';
    else if (height < 3) sizeHint = 'waist';
    else if (height < 4) sizeHint = 'waist-chest';
    else if (height < 5) sizeHint = 'chest-head';
    else sizeHint = 'overhead';

    if (score < 2) {
      return `Unrideable – ${sizeHint} dribble`;
    } else if (score < 4) {
      return `Very poor – weak, crumbly`;
    } else if (score < 6) {
      return `Fair – ${sizeHint}, ${windType}`;
    } else if (score < 8) {
      return `Good – ${sizeHint}, clean ${windType}`;
    } else {
      return `Excellent – powerful surf`;
    }
  };

  // Prepare chart data
  const chartData = forecast.slice(0, 24).map((entry) => ({
    time: format(parseISO(entry.timestamp), 'MMM dd HH:mm'),
    surfScore: entry.surf_score,
    waveHeight: entry.breaking_wave_height_ft,
    windSpeed: entry.wind.speed_mph,
    tideLevel: entry.tide.level_ft,
    heightSubscore: entry.sub_scores?.height ? entry.sub_scores.height * 10 : 0,
    periodSubscore: entry.sub_scores?.period ? entry.sub_scores.period * 10 : 0,
    windSubscore: entry.sub_scores?.wind ? entry.sub_scores.wind * 10 : 0,
  }));

  // Get next best window
  const nextBestWindow = bestTimeWindows && bestTimeWindows.length > 0 
    ? bestTimeWindows.find(w => !isPast(parseISO(w.end_time))) 
    : null;

  return (
    <div className={styles.container}>
      {/* HERO SECTION */}
      <div className={styles.hero}>
        <div className={styles.heroLeft}>
          <h1 className={styles.heroTitle}>16th Ave Belmar Surf Forecast</h1>
          <p className={styles.heroSubtitle}>Live physics-based forecast for 16th Ave, Belmar, NJ</p>
          <p className={styles.heroMeta}>
            Last updated: {format(new Date(), 'MMM dd, HH:mm')} · Buoy 44025 · 72h forecast
          </p>
        </div>

        <div className={styles.heroRight}>
          <div className={`${styles.scoreBadge} ${getScoreClass(current.surf_score)}`}>
            {current.surf_score.toFixed(1)}<span style={{fontSize: '24px'}}>/10</span>
          </div>
          
          <p className={styles.conditionsText}>
            {getConditionsBlurb(current)}
          </p>
          
          <p className={styles.boardRec}>
            {getBoardRec(current)}
          </p>
        </div>
      </div>

      {/* CURRENT CONDITIONS CARDS */}
      <div className={styles.cardsRow}>
        {/* Waves Card */}
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Waves at 16th Ave</h3>
          <div className={styles.cardBigNumber}>{current.breaking_wave_height_ft.toFixed(1)} ft</div>
          <p className={styles.cardSubtext}>Breaking height (after shoaling)</p>
          <p className={styles.cardDetail}>Period: {current.period_s.toFixed(0)} s</p>
          <p className={styles.cardDetail}>Direction: {current.wind.direction_deg < 90 ? 'NE' : current.wind.direction_deg < 180 ? 'SE' : 'S'}</p>
        </div>

        {/* Wind & Tide Card */}
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Wind & Tide</h3>
          <p className={styles.cardDetail} style={{marginTop: '16px', marginBottom: '12px'}}>
            <strong>Wind:</strong> {current.wind.type.charAt(0).toUpperCase() + current.wind.type.slice(1)} · {current.wind.speed_mph.toFixed(0)} mph
          </p>
          <p className={styles.cardDetail}>
            <strong>Tide:</strong> {current.tide.level_ft.toFixed(1)} ft {current.tide.level_ft > 0 ? '(high)' : '(low)'}
          </p>
        </div>

        {/* Best Session Card */}
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Next best window</h3>
          {nextBestWindow ? (
            <>
              <p className={styles.cardDetail} style={{marginTop: '16px', fontSize: '16px', fontWeight: '600'}}>
                {format(parseISO(nextBestWindow.start_time), 'EEE HH:mm')} – {format(parseISO(nextBestWindow.end_time), 'HH:mm')}
              </p>
              <p className={styles.cardDetail}>
                Score: {nextBestWindow.average_score.toFixed(1)}/10 · {nextBestWindow.wave_height_ft.toFixed(1)} ft
              </p>
              <p className={styles.cardDetail}>
                {nextBestWindow.wind_type} · {(nextBestWindow.wind_speed_ms * 2.237).toFixed(0)} mph
              </p>
            </>
          ) : (
            <p className={styles.cardDetail} style={{marginTop: '16px'}}>No good windows in next 72h</p>
          )}
        </div>
      </div>

      {/* BEST TIME WINDOWS */}
      {bestTimeWindows && bestTimeWindows.length > 0 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Best paddle-out windows</h2>
          <p className={styles.sectionSubtitle}>3-hour blocks ranked by surf score.</p>
          
          <div className={styles.windowsGrid}>
            {bestTimeWindows
              .sort((a, b) => parseISO(a.start_time).getTime() - parseISO(b.start_time).getTime())
              .slice(0, 6)
              .map((window, index) => {
                const isPastWindow = isPast(parseISO(window.end_time));
                return (
                  <div 
                    key={index} 
                    className={styles.windowCard}
                    style={{ opacity: isPastWindow ? 0.5 : 1 }}
                  >
                    <p className={styles.windowTime}>
                      {format(parseISO(window.start_time), 'EEE HH:mm')}–{format(parseISO(window.end_time), 'HH:mm')} · 
                      <span style={{ color: getScoreColor(window.average_score), marginLeft: '8px' }}>
                        {window.average_score.toFixed(1)}/10
                      </span>
                    </p>
                    <p className={styles.windowStats}>
                      {window.wave_height_ft.toFixed(1)} ft · {(window.wind_speed_ms * 2.237).toFixed(0)} mph {window.wind_type}
                    </p>
                    <p className={styles.windowDesc}>
                      {window.average_score >= 7 ? 'Clean beachbreak, good shape' : 
                       window.average_score >= 5 ? 'Surfable, mixed quality' : 
                       'Weak conditions'}
                    </p>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* FORECAST GRAPHS */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Forecast graphs</h2>
        
        <div className={styles.tabs}>
          <button 
            className={`${styles.tab} ${activeTab === 'score' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('score')}
          >
            Surf Score
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'height' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('height')}
          >
            Wave Height
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'wind' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('wind')}
          >
            Wind & Tide
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'subscores' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('subscores')}
          >
            Sub-scores
          </button>
        </div>

        <div className={styles.chartContainer}>
          {activeTab === 'score' && (
            <ResponsiveContainer width="100%" height={350}>

              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis 
                  dataKey="time" 
                  angle={-45} 
                  textAnchor="end" 
                  height={80}
                  tick={{ fill: '#666', fontSize: 12 }}
                />
                <YAxis 
                  domain={[0, 10]} 
                  tick={{ fill: '#666', fontSize: 12 }}
                  label={{ value: 'Score', angle: -90, position: 'insideLeft', style: { fill: '#333' } }}
                />
                <Tooltip 
                  contentStyle={{ background: '#fff', border: '1px solid #ddd', borderRadius: '4px' }}
                  labelStyle={{ color: '#333', fontWeight: 600 }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Line type="monotone" dataKey="surfScore" stroke="#FF7A1A" strokeWidth={3} name="Surf Score" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
          
          {activeTab === 'height' && (
            <ResponsiveContainer width="100%" height={350}>

              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="time" angle={-45} textAnchor="end" height={80} tick={{ fill: '#666', fontSize: 12 }} />
                <YAxis tick={{ fill: '#666', fontSize: 12 }} label={{ value: 'Height (ft)', angle: -90, position: 'insideLeft', style: { fill: '#333' } }} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #ddd', borderRadius: '4px' }} />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Line type="monotone" dataKey="waveHeight" stroke="#111111" strokeWidth={3} name="Wave Height (ft)" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
          
          {activeTab === 'wind' && (
            <ResponsiveContainer width="100%" height={350}>

              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="time" angle={-45} textAnchor="end" height={80} tick={{ fill: '#666', fontSize: 12 }} />
                <YAxis yAxisId="left" tick={{ fill: '#666', fontSize: 12 }} label={{ value: 'Wind (mph)', angle: -90, position: 'insideLeft', style: { fill: '#333' } }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: '#666', fontSize: 12 }} label={{ value: 'Tide (ft)', angle: 90, position: 'insideRight', style: { fill: '#333' } }} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #ddd', borderRadius: '4px' }} />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Line yAxisId="left" type="monotone" dataKey="windSpeed" stroke="#999" strokeWidth={2} name="Wind Speed (mph)" dot={{ r: 3 }} />
                <Line yAxisId="right" type="monotone" dataKey="tideLevel" stroke="#3B82F6" strokeWidth={2} name="Tide (ft)" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
          
          {activeTab === 'subscores' && (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="time" angle={-45} textAnchor="end" height={80} tick={{ fill: '#666', fontSize: 12 }} />
                <YAxis domain={[0, 10]} tick={{ fill: '#666', fontSize: 12 }} label={{ value: 'Subscore', angle: -90, position: 'insideLeft', style: { fill: '#333' } }} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #ddd', borderRadius: '4px' }} />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Bar dataKey="heightSubscore" fill="#FF7A1A" name="Height" />
                <Bar dataKey="periodSubscore" fill="#F59E0B" name="Period" />
                <Bar dataKey="windSubscore" fill="#6B7280" name="Wind" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* DETAILED TABLE (COLLAPSIBLE) */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Detailed hourly forecast</h2>
        <p className={styles.sectionSubtitle}>All the numbers if you want to plan around work or tides.</p>
        
        <button 
          className={styles.toggleButton}
          onClick={() => setShowDetailedTable(!showDetailedTable)}
        >
          {showDetailedTable ? 'Hide table' : 'Show table'}
          <span className={`${styles.toggleArrow} ${showDetailedTable ? styles.toggleArrowOpen : ''}`}>
            ▼
          </span>
        </button>

        <div className={`${styles.collapsible} ${showDetailedTable ? styles.collapsibleOpen : styles.collapsibleClosed}`}>
          <div style={{ overflowX: 'auto' }}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Score</th>
                  <th>Wave (ft)</th>
                  <th>Period (s)</th>
                  <th>Wind</th>
                  <th>Tide (ft)</th>
                  <th>Call</th>
                </tr>
              </thead>
              <tbody>
                {forecast.slice(0, 24).map((entry, index) => (
                  <tr key={index}>
                    <td>{format(parseISO(entry.timestamp), 'MMM dd HH:mm')}</td>
                    <td style={{ fontWeight: 600, color: getScoreColor(entry.surf_score) }}>
                      {entry.surf_score.toFixed(1)}
                    </td>
                    <td>{entry.breaking_wave_height_ft.toFixed(1)}</td>
                    <td>{entry.period_s.toFixed(0)}</td>
                    <td>{entry.wind.type} {entry.wind.speed_mph.toFixed(0)}mph</td>
                    <td>{entry.tide.level_ft.toFixed(1)}</td>
                    <td style={{ fontSize: '12px', fontStyle: 'italic' }}>{getCall(entry)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
