import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Waves, Wind, Clock, TrendingUp, Navigation, Droplets, ArrowUp, ArrowDown, ChevronDown, ChevronUp, Thermometer } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { format, parseISO } from 'date-fns';
import PhysicsView from '../components/PhysicsView';
import { useUnits } from '../contexts/UnitContext';

interface ForecastData {
  location: string;
  coordinates: { lat: number; lon: number };
  buoy_station: string;
  forecast_hours: number;
  forecast: Array<{
    timestamp: string;
    surf_score: number;
    breaking_wave_height_m: number;
    breaking_wave_height_ft: number;
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
    temperature?: {
      celsius: number;
      fahrenheit: number;
      feels_like_celsius?: number;
      feels_like_fahrenheit?: number;
    };
    sub_scores: {
      height: number;
      period: number;
      direction: number;
      wind: number;
      tide: number;
    };
    physics: any;
  }>;
  best_time_windows?: Array<{
    start_time: string;
    end_time: string;
    average_score: number;
    wave_height_ft: number;
    wind_type: string;
    wind_speed_ms: number;
  }>;
  timestamp: string;
}

export default function Home() {
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showTable, setShowTable] = useState(false);
  const [showPhysics, setShowPhysics] = useState(false);
  const { convertTemp } = useUnits();

  useEffect(() => {
    fetchForecast();
    const interval = setInterval(fetchForecast, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchForecast = async () => {
    try {
      setLoading(true);
      setError(null);
      // Use environment variable for API URL, fallback to localhost for development
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5002';
      const response = await fetch(`${apiUrl}/forecast?hours=72`);
      if (!response.ok) throw new Error(`Failed: ${response.status}`);
      setForecastData(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <Waves className="w-12 h-12 text-orange-500" />
        </motion.div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl mb-4">Error: {error}</h1>
          <button onClick={fetchForecast} className="px-6 py-3 bg-orange-500 rounded-xl">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!forecastData || !forecastData.forecast || forecastData.forecast.length === 0) {
    return null;
  }

  // Prepare chart data from real forecast
  const chartData = forecastData.forecast.slice(0, 24).map((entry) => ({
    time: format(parseISO(entry.timestamp), 'HH:mm'),
    score: entry.surf_score,
    height: entry.breaking_wave_height_ft,
    period: entry.period_s,
    wind: entry.wind.speed_mph,
    tide: entry.tide.level_ft,
    windDir: entry.wind.type,
    condition: `${entry.surf_score >= 6 ? 'Good' : 'Fair'} – ${entry.breaking_wave_height_ft.toFixed(1)}ft, ${entry.wind.type}`
  }));

  const current = forecastData.forecast[0];
  const bestWindows = forecastData.best_time_windows?.slice(0, 3).map(w => ({
    time: `${format(parseISO(w.start_time), 'EEE HH:mm')}–${format(parseISO(w.end_time), 'HH:mm')}`,
    score: w.average_score,
    height: w.wave_height_ft,
    wind: w.wind_speed_ms * 2.237, // convert to mph
    windDir: w.wind_type,
    desc: w.average_score >= 7 ? 'Clean beachbreak, good shape' : 
          w.average_score >= 5 ? 'Surfable, mixed quality' : 'Weak conditions'
  })) || [];

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-10">
        <motion.div
          className="absolute top-20 left-10 w-96 h-96 bg-orange-500 rounded-full blur-[120px]"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute bottom-20 right-10 w-96 h-96 bg-orange-600 rounded-full blur-[120px]"
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.5, 0.3, 0.5],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      </div>

      <div className="relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-b border-white/10 backdrop-blur-sm bg-black/50"
        >
          <div className="max-w-7xl mx-auto px-6 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ rotate: [0, 5, 0, -5, 0] }}
                  transition={{ duration: 4, repeat: Infinity }}
                  className="text-orange-500"
                >
                  <Waves className="w-10 h-10" strokeWidth={2.5} />
                </motion.div>
                <div>
                  <h1 className="text-white tracking-tight">tigerline</h1>
                  <p className="text-sm text-white/60">Live physics-based forecast</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-white/60">Last updated: {format(parseISO(forecastData.timestamp), 'MMM dd, HH:mm')}</p>
                <p className="text-xs text-white/40">Buoy {forecastData.buoy_station} · 72h forecast</p>
              </div>
            </div>
          </div>
        </motion.div>

        <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
          {/* Hero Section */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="relative bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10 rounded-3xl p-8 overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-orange-500/10 rounded-full blur-3xl" />
            
            <div className="relative">
              <div className="flex items-start justify-between mb-8">
                <div>
                  <h2 className="text-white/60 mb-2">16th Ave Belmar Surf Forecast</h2>
                  <p className="text-sm text-white/40">16th Ave, Belmar, NJ</p>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                {/* Score */}
                <div className="space-y-6">
                  <div className="relative inline-block">
                    <motion.div
                      className="absolute inset-0 bg-orange-500 blur-2xl opacity-50"
                      animate={{ scale: [1, 1.1, 1] }}
                      transition={{ duration: 3, repeat: Infinity }}
                    />
                    <div className="relative flex items-baseline gap-4">
                      <div className="text-white leading-none" style={{ fontSize: '160px', fontWeight: 900 }}>
                        {current.surf_score.toFixed(1)}
                      </div>
                      <div className="text-white/40 text-2xl">/10</div>
                    </div>
                  </div>
                  <div>
                    <p className="text-xl text-white mb-2">
                      {current.surf_score >= 7 ? `Excellent conditions for 16th Ave – expect strong, hollow surf.` :
                       current.surf_score >= 5 ? `OK surf. ${current.breaking_wave_height_ft.toFixed(1)}ft with ${current.wind.type}; fun if you're keen.` :
                       `Marginal. ${current.breaking_wave_height_ft.toFixed(1)}ft, ${current.wind.type} – rideable but not exciting.`}
                    </p>
                    {current.surf_score >= 3 && (
                      <p className="text-orange-500">
                        {current.breaking_wave_height_ft < 4 ? 'Longboard or foamie' : 
                         current.breaking_wave_height_ft < 6 ? 'Shortboard' : 
                         'Step-up shortboard'} · Best for {current.breaking_wave_height_ft < 4 ? 'beginners/intermediates' : 'confident surfers'}
                      </p>
                    )}
                  </div>
                </div>

                {/* Current Conditions */}
                <div className="space-y-4">
                  <div className="bg-white/5 border border-orange-500/30 rounded-2xl p-6">
                    <div className="flex items-center gap-2 mb-4 text-orange-500">
                      <Waves className="w-5 h-5" />
                      <span className="text-sm tracking-wider">WAVES AT 16TH AVE</span>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-baseline gap-2">
                        <span className="text-5xl text-white" style={{ fontWeight: 700 }}>
                          {current.breaking_wave_height_ft.toFixed(1)}
                        </span>
                        <span className="text-xl text-white/60">ft</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-white/40">Period</p>
                          <p className="text-white">{current.period_s.toFixed(0)} s</p>
                        </div>
                        <div>
                          <p className="text-white/40">Direction</p>
                          <p className="text-white">
                            {current.wind.direction_deg < 90 ? 'NE' : 
                             current.wind.direction_deg < 180 ? 'SE' : 'S'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
                      <div className="flex items-center gap-2 mb-2 text-white/60">
                        <Wind className="w-4 h-4" />
                        <span className="text-xs">WIND</span>
                      </div>
                      <p className="text-white capitalize">{current.wind.type} · {current.wind.speed_mph.toFixed(0)} mph</p>
                    </div>
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
                      <div className="flex items-center gap-2 mb-2 text-white/60">
                        <Droplets className="w-4 h-4" />
                        <span className="text-xs">TIDE</span>
                      </div>
                      <p className="text-white">{current.tide.level_ft.toFixed(1)} ft ({current.tide.level_ft > 0 ? 'high' : 'low'})</p>
                    </div>
                    {current.temperature && (
                      <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
                        <div className="flex items-center gap-2 mb-2 text-white/60">
                          <Thermometer className="w-4 h-4" />
                          <span className="text-xs">TEMP</span>
                        </div>
                        <p className="text-white">{convertTemp(current.temperature.celsius).value.toFixed(0)} {convertTemp(current.temperature.celsius).unit}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Next Best Window */}
          {bestWindows.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-gradient-to-r from-orange-500/20 to-orange-600/10 border border-orange-500/30 rounded-2xl p-6"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="w-5 h-5 text-orange-500" />
                    <span className="text-sm text-orange-500 tracking-wider">NEXT BEST WINDOW</span>
                  </div>
                  <p className="text-2xl text-white mb-2" style={{ fontWeight: 600 }}>{bestWindows[0].time}</p>
                  <div className="flex gap-6 text-sm">
                    <span className="text-white/80">Score: {bestWindows[0].score.toFixed(1)}/10</span>
                    <span className="text-white/80">{bestWindows[0].height.toFixed(1)} ft</span>
                    <span className="text-orange-400">{bestWindows[0].windDir} · {bestWindows[0].wind.toFixed(0)} mph</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Best Paddle-out Windows */}
          {bestWindows.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <h3 className="text-white/80 mb-4">Best paddle-out windows</h3>
              <p className="text-sm text-white/40 mb-4">3-hour blocks ranked by surf score.</p>
              <div className="grid md:grid-cols-3 gap-4">
                {bestWindows.map((window, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 + i * 0.1 }}
                    whileHover={{ scale: 1.02, borderColor: 'rgba(249, 115, 22, 0.5)' }}
                    className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:bg-white/[0.07] transition-all"
                  >
                    <div className="flex items-baseline gap-2 mb-3">
                      <span className="text-2xl text-orange-500" style={{ fontWeight: 700 }}>{window.score.toFixed(1)}</span>
                      <span className="text-white/40">/10</span>
                    </div>
                    <p className="text-white mb-3">{window.time}</p>
                    <div className="space-y-2 text-sm">
                      <p className="text-white/60">{window.height.toFixed(1)} ft · {window.wind.toFixed(0)} mph {window.windDir}</p>
                      <p className="text-white/40">{window.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Forecast Graphs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <h3 className="text-white/80 mb-6">Forecast graphs</h3>
            
            {/* Surf Score Chart */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-4">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-orange-500" />
                <span className="text-white/80">Surf Score</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#ffffff40"
                    tick={{ fill: '#ffffff60', fontSize: 12 }}
                    interval={3}
                  />
                  <YAxis 
                    stroke="#ffffff40"
                    tick={{ fill: '#ffffff60', fontSize: 12 }}
                    domain={[0, 10]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#000',
                      border: '1px solid rgba(249, 115, 22, 0.3)',
                      borderRadius: '12px',
                      color: '#fff'
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#f97316" 
                    strokeWidth={3}
                    fill="url(#scoreGradient)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Wave Height Chart */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-4">
              <div className="flex items-center gap-2 mb-4">
                <Waves className="w-5 h-5 text-orange-500" />
                <span className="text-white/80">Wave Height</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#ffffff40"
                    tick={{ fill: '#ffffff60', fontSize: 12 }}
                    interval={3}
                  />
                  <YAxis 
                    stroke="#ffffff40"
                    tick={{ fill: '#ffffff60', fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#000',
                      border: '1px solid rgba(249, 115, 22, 0.3)',
                      borderRadius: '12px',
                      color: '#fff'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="height" 
                    stroke="#f97316" 
                    strokeWidth={3}
                    dot={{ fill: '#f97316', r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Multi-line Subscores */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Navigation className="w-5 h-5 text-orange-500" />
                <span className="text-white/80">Sub-scores</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#ffffff40"
                    tick={{ fill: '#ffffff60', fontSize: 12 }}
                    interval={3}
                  />
                  <YAxis 
                    stroke="#ffffff40"
                    tick={{ fill: '#ffffff60', fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#000',
                      border: '1px solid rgba(249, 115, 22, 0.3)',
                      borderRadius: '12px',
                      color: '#fff'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="height" 
                    stroke="#f97316" 
                    strokeWidth={2}
                    name="Height"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="period" 
                    stroke="#fb923c" 
                    strokeWidth={2}
                    name="Period"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="wind" 
                    stroke="#fdba74" 
                    strokeWidth={2}
                    name="Wind"
                  />
                </LineChart>
              </ResponsiveContainer>
              <div className="flex gap-6 mt-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-orange-500" />
                  <span className="text-white/60">Height</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-orange-400" />
                  <span className="text-white/60">Period</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-orange-300" />
                  <span className="text-white/60">Wind</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Detailed Hourly Forecast */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-white/80 mb-1">Detailed hourly forecast</h3>
                <p className="text-sm text-white/40">All the numbers if you want to plan around work or tides.</p>
              </div>
              <button
                onClick={() => setShowTable(!showTable)}
                className="flex items-center gap-2 px-4 py-2 bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 rounded-xl text-orange-500 transition-colors"
              >
                {showTable ? (
                  <>Hide table <ChevronUp className="w-4 h-4" /></>
                ) : (
                  <>Show table <ChevronDown className="w-4 h-4" /></>
                )}
              </button>
            </div>

            {showTable && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden"
              >
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b border-white/10">
                      <tr className="text-left">
                        <th className="px-4 py-3 text-sm text-white/60">Time</th>
                        <th className="px-4 py-3 text-sm text-white/60">Score</th>
                        <th className="px-4 py-3 text-sm text-white/60">Wave (ft)</th>
                        <th className="px-4 py-3 text-sm text-white/60">Period (s)</th>
                        <th className="px-4 py-3 text-sm text-white/60">Wind</th>
                        <th className="px-4 py-3 text-sm text-white/60">Tide (ft)</th>
                        <th className="px-4 py-3 text-sm text-white/60">Call</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastData.forecast.slice(0, 24).map((row, i) => (
                        <tr 
                          key={i} 
                          className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                        >
                          <td className="px-4 py-3 text-sm text-white/80">{format(parseISO(row.timestamp), 'MMM dd HH:mm')}</td>
                          <td className="px-4 py-3">
                            <span className={row.surf_score >= 6.5 ? 'text-orange-500' : 'text-white/80'}>
                              {row.surf_score.toFixed(1)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-white/80">{row.breaking_wave_height_ft.toFixed(1)}</td>
                          <td className="px-4 py-3 text-white/80">{row.period_s.toFixed(0)}</td>
                          <td className="px-4 py-3 text-white/80">{row.wind.type} {row.wind.speed_mph.toFixed(0)}mph</td>
                          <td className="px-4 py-3 text-white/80">
                            <span className="flex items-center gap-1">
                              {row.tide.level_ft.toFixed(1)}
                              {row.tide.level_ft > 0 ? (
                                <ArrowUp className="w-3 h-3 text-orange-500" />
                              ) : (
                                <ArrowDown className="w-3 h-3 text-blue-400" />
                              )}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-white/60">
                            {row.surf_score >= 6 ? 'Good' : 'Fair'} – {row.breaking_wave_height_ft.toFixed(1)}ft, {row.wind.type}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
          </motion.div>

          {/* Physics View */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-white/80 mb-1">Physics (for wave nerds)</h3>
                <p className="text-sm text-white/40">Buoy → shoaling → breaking → scoring.</p>
              </div>
              <button
                onClick={() => setShowPhysics(!showPhysics)}
                className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white/60 transition-colors"
              >
                {showPhysics ? (
                  <>Collapse physics view <ChevronUp className="w-4 h-4" /></>
                ) : (
                  <>Expand physics view <ChevronDown className="w-4 h-4" /></>
                )}
              </button>
            </div>

            {showPhysics && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-white/5 border border-white/10 rounded-2xl p-6"
              >
                <PhysicsView forecast={forecastData} />
              </motion.div>
            )}
          </motion.div>
        </div>

        {/* Footer */}
        <div className="max-w-7xl mx-auto px-6 py-8 mt-12 border-t border-white/10">
          <p className="text-center text-sm text-white/40">
            tigerline · Physics-based surf forecasting for the East Coast
          </p>
        </div>
      </div>
    </div>
  );
}
