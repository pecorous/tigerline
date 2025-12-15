import { useState } from 'react';
import { 
  LineChart, Line, BarChart, Bar, ComposedChart, Area, AreaChart,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend 
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { useUnits } from '../contexts/UnitContext';
import { useTheme } from '../contexts/ThemeContext';

interface ShoalingPathPoint {
  x: number;
  h: number;
  H: number;
  theta_rad: number;
  theta_deg: number;
  c: number;
  cg: number;
  Ksr: number;
}

interface PhysicsViewProps {
  forecast: any;
}

export default function PhysicsView({ forecast }: PhysicsViewProps) {
  const [physicsTab, setPhysicsTab] = useState<'overview' | 'shoaling' | 'scoring' | 'raw'>('overview');
  const { convertHeight, convertDistance } = useUnits();
  const { theme } = useTheme();
  
  // Theme-aware colors - MUST be defined before early returns
  const physicsBgColor = theme === 'light' ? '#ffffff' : '#1a1a1a';
  const physicsTextColor = theme === 'light' ? '#000000' : '#ffffff';
  const physicsTextMuted = theme === 'light' ? 'rgba(0, 0, 0, 0.6)' : 'rgba(255, 255, 255, 0.6)';
  const physicsBorderColor = theme === 'light' ? '#e0e0e0' : '#333333';
  const physicsCardBg = theme === 'light' ? '#f8f8f8' : '#0a0a0a';
  
  if (!forecast || !forecast.forecast || forecast.forecast.length === 0) {
    return (
      <div>
        <p style={{ color: physicsTextMuted }}>No physics data available</p>
      </div>
    );
  }

  const current = forecast.forecast[0];
  
  if (!current || !current.physics) {
    return (
      <div>
        <p style={{ color: physicsTextMuted }}>No physics data for current conditions</p>
      </div>
    );
  }

  const offshore = current.physics.offshore || {};
  const breaking = current.physics.breaking || {};
  const propagation = current.physics.propagation || {};
  const scoring = current.physics.scoring_breakdown || {};
  // Use shoaling_path_surf (surf height) for consistency with forecast display
  const shoalingPath = current.physics.shoaling_path_surf || current.physics.shoaling_path || [];

  // Prepare shoaling visualization data
  // 500 ft = ~152 meters, -20 ft = ~-6 meters
  const MAX_DISTANCE_M = 152;
  const MIN_DISTANCE_M = -6;
  const MAX_DISTANCE = convertDistance(MAX_DISTANCE_M).value; // Convert to display units early
  const MIN_DISTANCE = convertDistance(MIN_DISTANCE_M).value;
  
  // DON'T filter shoaling path - it has points at large distances (10km, 5km, etc.)
  // We need ALL the data to interpolate for our visualization range (0-152m)
  const nearshoreData = [...shoalingPath].sort((a: any, b: any) => (b.x || 0) - (a.x || 0)); // Sort descending (offshore to shore)

  // Build bathymetry and wave data from PHYSICS - use shoaling path data
  // The shoaling path contains the actual physics: depth (h), wave height (H) at each point
  // Breaking occurs when H/h >= gamma_b (0.78) - this is determined by the physics, not arbitrary
  
  const GAMMA_B = 0.78; // Breaker index from backend
  
  // Extract bathymetry from shoaling path - this is the REAL physics data
  // Each point in shoaling_path has: x (distance from shore), h (depth), H (wave height)
  const bathymetryFromPhysics: Array<{x: number, h: number}> = [];
  
  if (shoalingPath && shoalingPath.length > 0) {
    // Shoaling path has points at large distances (10km, 5km, etc.)
    // Interpolate to create bathymetry points at our visualization range (0-152m)
    
    // Create points at regular intervals from shore to MAX_DISTANCE
    const numBathyPoints = 20;
    for (let i = 0; i <= numBathyPoints; i++) {
      const x_m = (i / numBathyPoints) * MAX_DISTANCE_M;
      
      // Interpolate depth from shoaling path
      // Find the two nearest points in shoaling path
      let closestBefore: any = null;
      let closestAfter: any = null;
      
      for (const p of shoalingPath) {
        if ((p.x || 0) >= x_m) {
          if (!closestBefore || (p.x || 0) < (closestBefore.x || Infinity)) {
            closestBefore = p;
          }
        }
        if ((p.x || 0) <= x_m) {
          if (!closestAfter || (p.x || 0) > (closestAfter.x || 0)) {
            closestAfter = p;
          }
        }
      }
      
      // Interpolate depth
      let h_interp = 0;
      if (closestBefore && closestAfter && closestBefore.x !== closestAfter.x) {
        const t = (x_m - (closestAfter.x || 0)) / ((closestBefore.x || 0) - (closestAfter.x || 0));
        h_interp = (closestAfter.h || 0) + t * ((closestBefore.h || 0) - (closestAfter.h || 0));
      } else if (closestBefore) {
        h_interp = closestBefore.h || 0;
      } else if (closestAfter) {
        h_interp = closestAfter.h || 0;
      } else {
        // Estimate depth based on distance and typical beach slope
        h_interp = Math.max(0, x_m * 0.03); // ~3% slope
      }
      
      bathymetryFromPhysics.push({ x: x_m, h: h_interp });
    }
    
    // Add beach point (x=-6m, h=-1.5m) for visualization
    bathymetryFromPhysics.push({ x: -6, h: -1.5 });
  } else {
    // Fallback if no shoaling path data
    const tideLevel = current.tide?.level_m ?? 0;
    for (let i = 0; i <= 20; i++) {
      const x_m = (i / 20) * MAX_DISTANCE_M;
      const h_m = Math.max(0, x_m * 0.03 + tideLevel); // 3% slope
      bathymetryFromPhysics.push({ x: x_m, h: h_m });
    }
    bathymetryFromPhysics.push({ x: -6, h: -1.5 });
  }
  
  // Sort by x descending (offshore to shore)
  bathymetryFromPhysics.sort((a, b) => b.x - a.x);
  
  // Find breaking point from shoaling path - where H/h >= gamma_b
  // CRITICAL: Breaking occurs when wave becomes unstable (H/h >= gamma_b)
  // This happens OFFSHORE where depth is still significant (NOT at shore where h=0)
  let breakingPointFromPhysics: {x: number, h: number, H: number, c?: number} | null = null;
  if (shoalingPath && shoalingPath.length > 0) {
    // Sort shoaling path by x descending (offshore to shore) to find first breaking point
    const sortedPath = [...shoalingPath].sort((a: any, b: any) => (b.x || 0) - (a.x || 0));
    
    for (const point of sortedPath) {
      if (point.H !== undefined && point.h !== undefined && point.h > 0) {
        const H_d_ratio = point.H / point.h;
        if (H_d_ratio >= GAMMA_B) {
          breakingPointFromPhysics = {
            x: point.x || 0,
            h: point.h,
            H: point.H,
            c: point.c || 10.0  // Store phase speed for wavelength calculation
          };
          break; // First point where breaking occurs (moving from offshore to shore)
        }
      }
    }
  }
  
  // Use breaking point from physics if found, otherwise use API values
  const breakingDepthM = breakingPointFromPhysics?.h || breaking.depth_m || 1.2;
  const breakingDistM = breakingPointFromPhysics?.x || breaking.distance_from_shore_m || 0;
  
  // Use physics-based bathymetry
  const bathymetryPoints = bathymetryFromPhysics;
  
  // Build complete visualization data structure (in meters - will convert for display)
  // ALL in depth coordinates (distance below water surface)
  const visualizationDataMeters: Array<{
    x: number;
    bathymetryY: number;
    waveCrestY: number | null;
    waveTroughY: number | null;
    waterSurfaceY: number;
  }> = [];
  
  // Build visualization data from PHYSICS - interpolate wave heights from shoaling path
  // Shoaling path has points at large distances, so we interpolate for our range
  bathymetryPoints.forEach(bathPoint => {
    const x_m = bathPoint.x;
    
    // Interpolate wave height from shoaling path
    let H_surf = 0;
    let c = 10.0;
    
    if (shoalingPath.length > 0 && x_m >= 0) {
      // Find the two nearest points in shoaling path for interpolation
      let closestBefore: any = null;
      let closestAfter: any = null;
      
      for (const p of shoalingPath) {
        if ((p.x || 0) >= x_m) {
          if (!closestBefore || (p.x || 0) < (closestBefore.x || Infinity)) {
            closestBefore = p;
          }
        }
        if ((p.x || 0) <= x_m) {
          if (!closestAfter || (p.x || 0) > (closestAfter.x || 0)) {
            closestAfter = p;
          }
        }
      }
      
      // Interpolate H and c
      if (closestBefore && closestAfter && closestBefore.x !== closestAfter.x) {
        const t = (x_m - (closestAfter.x || 0)) / ((closestBefore.x || 0) - (closestAfter.x || 0));
        H_surf = (closestAfter.H || 0) + t * ((closestBefore.H || 0) - (closestAfter.H || 0));
        c = (closestAfter.c || 10.0) + t * ((closestBefore.c || 10.0) - (closestAfter.c || 10.0));
      } else if (closestBefore) {
        H_surf = closestBefore.H || 0;
        c = closestBefore.c || 10.0;
      } else if (closestAfter) {
        H_surf = closestAfter.H || 0;
        c = closestAfter.c || 10.0;
      }
    }
    
    visualizationDataMeters.push({
      x: bathPoint.x,
      bathymetryY: bathPoint.h,  // Depth from interpolation
      // Waves oscillate ABOVE (negative) and BELOW (positive) water surface
      waveCrestY: H_surf > 0 ? -H_surf / 2 : null,  // ABOVE water (negative)
      waveTroughY: H_surf > 0 ? H_surf / 2 : null,   // BELOW water (positive)
      waterSurfaceY: 0  // At 0
    });
  });
  
  // CRITICAL: Ensure point at shore (x=0) for bathymetry and wave envelope to extend to y-axis
  const hasShorePointMeters = visualizationDataMeters.some(d => Math.abs(d.x) < 0.1);
  if (!hasShorePointMeters) {
    // Find nearest point to shore from shoaling path
    let shorePoint: any = null;
    if (shoalingPath.length > 0) {
      shorePoint = shoalingPath.reduce((closest: any, p: any) => {
        const dist = Math.abs(p.x || 0);
        const closestDist = Math.abs(closest.x || 0);
        return dist < closestDist ? p : closest;
      }, shoalingPath[0]);
    }
    
    const H_surf_shore = shorePoint?.H || 0;
    visualizationDataMeters.push({
      x: 0,
      bathymetryY: 0.0,  // Shore is at water surface
      waveCrestY: H_surf_shore > 0 ? -H_surf_shore / 2 : null,
      waveTroughY: H_surf_shore > 0 ? H_surf_shore / 2 : null,
      waterSurfaceY: 0
    });
  }
  
  // Sort by x descending (offshore to shore) for proper rendering
  visualizationDataMeters.sort((a, b) => b.x - a.x);

  // Get breaking distance in display units - use physics-based breaking point
  const breakingDistDisplay = breakingDistM > 0 
    ? convertDistance(breakingDistM).value 
    : (breaking.distance_from_shore_m !== undefined && breaking.distance_from_shore_m !== null
      ? convertDistance(breaking.distance_from_shore_m).value
      : 0);
  
  // Convert visualization data to display units
  const visualizationData = visualizationDataMeters.map(d => ({
    x: convertDistance(d.x).value,
    bathymetryY: convertHeight(d.bathymetryY).value,
    waveCrestY: d.waveCrestY !== null ? -convertHeight(Math.abs(d.waveCrestY)).value : null,
    waveTroughY: d.waveTroughY !== null ? convertHeight(d.waveTroughY).value : null,
    waterSurfaceY: 0,
  })).filter(d => d.x >= MIN_DISTANCE && d.x <= MAX_DISTANCE);
  
  // CRITICAL: Bathymetry and wave envelope MUST extend from shore (y-axis, x=0) to breaking point
  // Build bathymetryData that GUARANTEES x=0 is included and extends to breaking point
  const breakingXDisplay = breakingDistDisplay;
  
  // Step 1: Find or create shore point (x=0)
  let shorePoint = visualizationData.find(d => Math.abs(d.x) < 0.01);
  if (!shorePoint) {
    // Create shore point from nearest data point
    const nearest = visualizationData.reduce((closest, d) => 
      Math.abs(d.x) < Math.abs(closest.x) ? d : closest, visualizationData[0]
    );
    shorePoint = {
      x: 0,
      bathymetryY: 0,
      waveCrestY: nearest.waveCrestY,
      waveTroughY: nearest.waveTroughY,
      waterSurfaceY: 0
    };
  }
  
  // Step 2: Bathymetry extends from shore (x=0) to offshore (MAX_DISTANCE)
  // CRITICAL: Beach continues from shore to offshore, NOT just to breaking point
  // Only WAVE ENVELOPE and WAVE SURFACE stop at breaking point
  let bathymetryPoints_Display = visualizationData.filter(d => d.x >= 0 && d.x <= MAX_DISTANCE);
  
  // Step 3: Ensure shore point is included in bathymetry
  const hasShoreInBathy = bathymetryPoints_Display.some(d => Math.abs(d.x) < 0.01);
  if (!hasShoreInBathy && shorePoint) {
    bathymetryPoints_Display.push(shorePoint);
  }
  
  // Step 4: Sort ASCENDING (shore to offshore) for proper tooltip alignment with reversed axis
  // CRITICAL: With reversed x-axis, data must be sorted ascending for tooltips to align
  const bathymetryData = bathymetryPoints_Display.sort((a, b) => a.x - b.x);
  
  // Step 5: Create separate data for wave envelope (stops at breaking point)
  let waveEnvelopeData = visualizationData.filter(d => {
    if (breakingXDisplay <= 0) {
      return d.x >= 0 && d.x <= MAX_DISTANCE;
    } else {
      return d.x >= 0 && d.x <= breakingXDisplay;
    }
  });
  
  // Ensure wave envelope includes shore point
  const hasShoreInWave = waveEnvelopeData.some(d => Math.abs(d.x) < 0.01);
  if (!hasShoreInWave && shorePoint) {
    waveEnvelopeData.push(shorePoint);
  }
  // Sort ASCENDING for proper tooltip alignment with reversed axis
  waveEnvelopeData.sort((a, b) => a.x - b.x);
  
  // DEBUG: Verify data structure
  console.log('=== DATA DEBUG ===');
  console.log('Breaking point x:', breakingXDisplay);
  console.log('Bathymetry points (extends to shore):', bathymetryData.length);
  console.log('Wave envelope points (stops at breaking):', waveEnvelopeData.length);
  console.log('Bathymetry X range:', Math.min(...bathymetryData.map(d => d.x)), 'to', Math.max(...bathymetryData.map(d => d.x)));
  console.log('Wave envelope X range:', waveEnvelopeData.length > 0 ? Math.min(...waveEnvelopeData.map(d => d.x)) : 'N/A', 'to', waveEnvelopeData.length > 0 ? Math.max(...waveEnvelopeData.map(d => d.x)) : 'N/A');

  // Wave surface data - smooth trigonometric representation (convert for display)
  // Create proper waves that oscillate above and below water surface (y=0)
  // Wave surface should extend continuously from offshore to breaking point
  // Wave surface is DETERMINED BY BATHYMETRY through shoaling physics
  const waveShapeData: Array<{x: number, y: number}> = [];
  if (shoalingPath.length > 0) {
    // Use actual period from wave data if available, otherwise default to 11s
    const period = current.period_s || 11.0;
    
    // Use physics-based breaking distance (already calculated above)
    // breakingDistM is from physics (where H/h >= gamma_b)
    
    // Create continuous wave surface from MAX_DISTANCE_M (offshore) to breaking point
    // Generate from offshore (large x) down to breaking point (smaller x)
    // Wave height H is determined by shoaling physics: H increases as depth h decreases
    // CRITICAL: Must include breaking point exactly, and extend from shore (x=0)
    const maxXFromPath = shoalingPath.length > 0 ? Math.max(...shoalingPath.map((p: any) => p.x || 0)) : MAX_DISTANCE_M;
    const startX = Math.min(MAX_DISTANCE_M, maxXFromPath); // Start offshore
    const endX = Math.max(0, breakingDistM); // End at breaking point (at least x=0 for shore)
    const numPoints = 600; // More points for smoother wave - CRITICAL for smoothness
    
    // Calculate FIXED wavelength for smooth wave surface
    // Use wavelength at breaking point as reference wavelength throughout
    // This prevents choppiness from wavelength changes with depth
    let wavelength_ref = 50; // Default reference wavelength
    
    if (breakingPointFromPhysics && breakingPointFromPhysics.c) {
      const c_break = breakingPointFromPhysics.c;
      wavelength_ref = c_break * period;
    } else if (shoalingPath.length > 0) {
      // Use average wavelength from shoaling path
      const avgC = shoalingPath.reduce((sum: number, p: any) => sum + (p.c || 10.0), 0) / shoalingPath.length;
      wavelength_ref = avgC * period;
    }
    
    // Calculate phase offset so breaking point is at crest
    // At x = breakingDistM, we want sin(phase) = 1 (crest)
    // This means phase = π/2 at breaking point
    let globalPhaseOffset = 0;
    if (wavelength_ref > 0) {
      const k_ref = 2 * Math.PI / wavelength_ref;
      globalPhaseOffset = Math.PI / 2 - k_ref * breakingDistM;
    }
    
    for (let i = 0; i <= numPoints; i++) {
      const t = i / numPoints;
      const x_m = startX + (endX - startX) * t;
      
      // Interpolate wave properties from shoaling path (PHYSICS DATA)
      // Shoaling path has points at large distances, so we use linear interpolation
      let H_surf_m = 0;
      let c = 10.0;
      
      if (shoalingPath.length > 0) {
        // Find the two bounding points in shoaling path
        let closestBefore: any = null;
        let closestAfter: any = null;
        
        for (const p of shoalingPath) {
          if ((p.x || 0) >= x_m) {
            if (!closestBefore || (p.x || 0) < (closestBefore.x || Infinity)) {
              closestBefore = p;
            }
          }
          if ((p.x || 0) <= x_m) {
            if (!closestAfter || (p.x || 0) > (closestAfter.x || 0)) {
              closestAfter = p;
            }
          }
        }
        
        // Linear interpolation between bounding points
        if (closestBefore && closestAfter && closestBefore.x !== closestAfter.x) {
          const t_interp = (x_m - (closestAfter.x || 0)) / ((closestBefore.x || 0) - (closestAfter.x || 0));
          H_surf_m = (closestAfter.H || 0) + t_interp * ((closestBefore.H || 0) - (closestAfter.H || 0));
          c = (closestAfter.c || 10.0) + t_interp * ((closestBefore.c || 10.0) - (closestBefore.c || 10.0));
        } else if (closestBefore) {
          H_surf_m = closestBefore.H || 0;
          c = closestBefore.c || 10.0;
        } else if (closestAfter) {
          H_surf_m = closestAfter.H || 0;
          c = closestAfter.c || 10.0;
        }
      }
      
      const amplitude_m = H_surf_m / 2;
      
      // Phase calculation - use FIXED reference wavelength for smoothness
      // CRITICAL: Using local wavelength causes choppiness where wavelength changes
      // Use reference wavelength (at breaking point) throughout for smooth continuous wave
      const k_ref = 2 * Math.PI / wavelength_ref; // FIXED wave number for smoothness
      const phase = k_ref * x_m + globalPhaseOffset;
      
      // Water surface at y=0, waves oscillate above (negative) and below (positive)
      // sin(phase) = 1 → crest (negative y, above water) - THIS IS BREAKING POINT
      // sin(phase) = -1 → trough (positive y, below water)
      const y_m = -amplitude_m * Math.sin(phase);
      
      // Convert to display units, preserving sign
      const y_display = y_m < 0 
        ? -convertHeight(Math.abs(y_m)).value  // Crest above water (negative)
        : convertHeight(y_m).value;             // Trough below water (positive)
      
      const x_display = convertDistance(x_m).value;
      // Include points from shore (y-axis, x=0) to breaking point
      // CRITICAL: Must include breaking point exactly, and extend from shore
      const breakingXDisplay = breakingDistDisplay;
      if (x_display >= 0 && x_display <= Math.max(breakingXDisplay, MAX_DISTANCE)) {
        waveShapeData.push({ 
          x: x_display, 
          y: y_display
        });
      }
    }
    
    // CRITICAL: Ensure breaking point is included exactly at crest
    if (breakingDistM >= 0 && breakingPointFromPhysics) {
      const breakingXDisplay = convertDistance(breakingDistM).value;
      const breakingH = breakingPointFromPhysics.H || 0;
      const breakingC = breakingPointFromPhysics.c || 10.0;
      const breakingWavelength = breakingC * period;
      
      // Calculate phase at breaking point - MUST be π/2 for crest
      const phaseAtBreaking = Math.PI / 2;
      const amplitude_break = breakingH / 2;
      const y_break = -amplitude_break * Math.sin(phaseAtBreaking); // Should be -amplitude (crest above water)
      
      const y_break_display = y_break < 0 
        ? -convertHeight(Math.abs(y_break)).value
        : convertHeight(y_break).value;
      
      // Add breaking point explicitly at crest
      const breakingPointExists = waveShapeData.some(p => Math.abs(p.x - breakingXDisplay) < 0.1);
      if (!breakingPointExists) {
        waveShapeData.push({
          x: breakingXDisplay,
          y: y_break_display
        });
      } else {
        // Update existing point to be at crest
        const idx = waveShapeData.findIndex(p => Math.abs(p.x - breakingXDisplay) < 0.1);
        if (idx >= 0) {
          waveShapeData[idx].y = y_break_display;
        }
      }
      
      // Sort by x ASCENDING for proper tooltip alignment with reversed axis
      waveShapeData.sort((a, b) => a.x - b.x);
    }
  }
  
  // DEBUG: Log wave surface data
  console.log('=== WAVE SURFACE DATA DEBUG ===');
  console.log('Wave shape data points:', waveShapeData.length);
  if (waveShapeData.length > 0) {
    console.log('First point:', waveShapeData[0]);
    console.log('Last point:', waveShapeData[waveShapeData.length - 1]);
    console.log('X range:', Math.min(...waveShapeData.map(d => d.x)), 'to', Math.max(...waveShapeData.map(d => d.x)));
    const breakingPointInWave = waveShapeData.find(d => Math.abs(d.x - breakingXDisplay) < 1);
    console.log('Breaking point in wave surface:', breakingPointInWave);
  }

  // Calculate Y domain in display units - water surface at 0, depths positive (down), crests negative (up)
  const allYValues = visualizationData.length > 0 ? [
    ...visualizationData.map(d => d.bathymetryY),  // Positive (below water)
    ...visualizationData.map(d => d.waveCrestY).filter((y): y is number => y !== null),  // Negative (above water)
    ...visualizationData.map(d => d.waveTroughY).filter((y): y is number => y !== null),  // Positive (below water)
    0  // Water surface
  ] : [0];
  
  const minY = allYValues.length > 0 ? Math.min(...allYValues) - 0.5 : -2;
  const maxY = allYValues.length > 0 ? Math.max(...allYValues) + 0.5 : 8;

  // Segmented control style - matching Example UI
  const containerBg = theme === 'light' ? '#ececf0' : 'rgba(255, 255, 255, 0.1)';
  const activeBg = theme === 'light' ? '#ffffff' : 'rgba(255, 255, 255, 0.15)';
  const activeText = theme === 'light' ? '#000000' : '#ffffff';
  const inactiveText = theme === 'light' ? 'rgba(0, 0, 0, 0.6)' : 'rgba(255, 255, 255, 0.6)';
  const activeBorder = theme === 'light' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(255, 255, 255, 0.2)';

  const tabs = [
    { id: 'overview', label: 'Buoy → Beach' },
    { id: 'shoaling', label: 'Shoaling & Breaking' },
    { id: 'scoring', label: 'Scoring Breakdown' },
    { id: 'raw', label: 'Raw Data' },
  ];

  return (
    <div>
      {/* Physics Tabs - Segmented Control Style */}
      <div 
        className="inline-flex h-9 items-center justify-center rounded-xl p-[3px] mb-6"
        style={{ background: containerBg }}
      >
        {tabs.map((tab) => {
          const isActive = physicsTab === tab.id;
          return (
            <button
              key={tab.id}
              className="inline-flex h-[calc(100%-1px)] flex-1 items-center justify-center rounded-xl px-3 py-1 text-sm font-medium whitespace-nowrap transition-all"
              style={{
                background: isActive ? activeBg : 'transparent',
                color: isActive ? activeText : inactiveText,
                border: isActive ? `1px solid ${activeBorder}` : '1px solid transparent',
                boxShadow: isActive ? (theme === 'light' ? '0 1px 2px rgba(0, 0, 0, 0.05)' : '0 1px 2px rgba(0, 0, 0, 0.2)') : 'none',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = theme === 'light' ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.8)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = inactiveText;
                }
              }}
              onClick={() => setPhysicsTab(tab.id as any)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div style={{ marginTop: '20px' }}>
        {physicsTab === 'overview' && (() => {
          const hs = convertHeight(offshore.Hs_m || 0);
          const breakingH = convertHeight(breaking.height_m || 0);
          return (
            <div>
              <h3 className="text-lg font-semibold mb-3" style={{ color: physicsTextColor }}>Wave Transformation</h3>
              <ul className="space-y-2 mb-5" style={{ color: theme === 'light' ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.8)' }}>
                <li><strong style={{ color: physicsTextColor }}>Offshore Hs:</strong> {hs.value.toFixed(2)} {hs.unit} at buoy</li>
                <li><strong style={{ color: physicsTextColor }}>Travel time:</strong> {offshore.travel_time_hours?.toFixed(1)} hours from buoy to beach</li>
                <li><strong style={{ color: physicsTextColor }}>After shoaling:</strong> {breakingH.value.toFixed(2)} {breakingH.unit} breaking height</li>
                <li><strong style={{ color: physicsTextColor }}>Amplification:</strong> {breaking.height_m && offshore.Hs_m ? (breaking.height_m / offshore.Hs_m).toFixed(2) : 'N/A'}x (waves gain height in shallow water)</li>
              </ul>
              <p className="text-sm" style={{ color: physicsTextMuted }}>
                <strong style={{ color: theme === 'light' ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)' }}>Data sources:</strong> NDBC Station {forecast.buoy_station || '44025'}, OpenWeatherMap wind, NOAA tides
              </p>
            </div>
          );
        })()}

        {physicsTab === 'shoaling' && shoalingPath.length > 0 && (
          <div>
            <h3 className="text-lg font-bold mb-4" style={{ color: physicsTextColor }}>
              🌊 Wave Shoaling Path Visualization (Scientific Beach Cross-Section)
            </h3>
            {(() => {
              const breakingH = convertHeight(breaking.height_m || 0);
              const breakingDist = convertDistance(breaking.distance_from_shore_m || 0);
              const breakingDepth = convertHeight(breaking.depth_m || 0);
              return (
                <p className="text-sm mb-4" style={{ color: physicsTextColor }}>
                  Showing typical surf height (average individual waves, not Hs). 
                  Wave height at breaking: <strong style={{ color: '#000000' }}>{breakingH.value.toFixed(2)} {breakingH.unit}</strong>
                </p>
              );
            })()}
            
            <div style={{ background: '#ffffff', padding: '24px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', border: '1px solid #e0e0e0' }}>
              <ResponsiveContainer width="100%" height={350}>
                <ComposedChart 
                  data={bathymetryData}
                  margin={{ top: 20, right: 30, left: 60, bottom: 60 }}
                  syncId="shoaling"
                >
                  <defs>
                    {/* Water gradient */}
                    <linearGradient id="waterGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#64b5f6" stopOpacity={0.8} />
                      <stop offset="100%" stopColor="#1976d2" stopOpacity={0.4} />
                    </linearGradient>
                    {/* Beach/sand gradient */}
                    <linearGradient id="beachGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ffb74d" stopOpacity={0.9} />
                      <stop offset="100%" stopColor="#ff9800" stopOpacity={0.7} />
                    </linearGradient>
                  </defs>
                  
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" opacity={0.5} />
                  
                  {/* X-Axis: REVERSED - Shore on RIGHT, Offshore on LEFT */}
                  <XAxis 
                    dataKey="x"
                    type="number"
                    reversed={true}
                    label={{ 
                      value: `Distance from Shore (${convertDistance(100).unit}) ← Offshore | Shore →`, 
                      position: 'bottom', 
                      offset: 0,
                      style: { 
                        fontSize: '16px',
                        fontWeight: 'bold',
                        fill: '#000000'
                      } 
                    }}
                    tick={{ fontSize: '13px', fill: '#666666' }}
                    domain={[MIN_DISTANCE, MAX_DISTANCE]}
                    stroke="#666666"
                    strokeWidth={2}
                    tickFormatter={(value) => {
                      // Value is already in display units, just format it
                      return `${value.toFixed(0)}`;
                    }}
                  />
                  
                  {/* Y-Axis: Water surface at 0, negative = above, positive = below */}
                  <YAxis 
                    yAxisId="main"
                    orientation="left"
                    type="number"
                    reversed={true}
                    label={{ 
                      value: `Elevation (${convertHeight(1).unit})`, 
                      angle: -90, 
                      position: 'insideLeft', 
                      offset: 10,
                      style: { 
                        fontSize: '18px',
                        fontWeight: '900',
                        fill: '#000000'
                      } 
                    }}
                    tick={{ fontSize: '14px', fill: '#000000', fontWeight: 600 }}
                    domain={[minY, maxY]}
                    allowDataOverflow={false}
                    tickFormatter={(value) => {
                      // Value is already in display units, just format it
                      if (value === 0) return '0 (water)';
                      return `${Math.abs(value).toFixed(1)}`;
                    }}
                    stroke="#000000"
                    strokeWidth={3}
                  />
                  
                  <Tooltip 
                    contentStyle={{ 
                      background: '#ffffff', 
                      border: '2px solid #1976d2', 
                      borderRadius: '8px', 
                      padding: '12px',
                      color: '#000000',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                      fontSize: '14px'
                    }}
                    cursor={{ stroke: '#1976d2', strokeWidth: 2, strokeDasharray: '5 5' }}
                    position={{ y: 0 }}
                    allowEscapeViewBox={{ x: false, y: true }}
                    isAnimationActive={false}
                    animationDuration={0}
                    formatter={(value: any, name: string) => {
                      if (typeof value === 'number') {
                        const heightUnit = convertHeight(1).unit;
                        const distanceUnit = convertDistance(1).unit;
                        
                        if (name === 'Bathymetry') {
                          return [`Depth: ${value.toFixed(2)} ${heightUnit}`, name];
                        }
                        if (name === 'Wave Surface') {
                          return [`${value < 0 ? 'Above' : 'Below'} water: ${Math.abs(value).toFixed(2)} ${heightUnit}`, name];
                        }
                        if (name.includes('Crest')) {
                          return [`Above water: ${Math.abs(value).toFixed(2)} ${heightUnit}`, name];
                        }
                        if (name.includes('Trough')) {
                          return [`Below water: ${Math.abs(value).toFixed(2)} ${heightUnit}`, name];
                        }
                        // X-axis values (distance)
                        if (name === 'x' || name.includes('Distance')) {
                          return [`${value.toFixed(0)} ${distanceUnit}`, name];
                        }
                        return [`${value.toFixed(2)} ${heightUnit}`, name];
                      }
                      return [value, name];
                    }}
                    labelFormatter={(label) => {
                      const distanceUnit = convertDistance(1).unit;
                      return `Distance: ${label} ${distanceUnit}`;
                    }}
                    labelStyle={{ color: '#000000', fontWeight: 700, marginBottom: '8px' }}
                  />
                  
                  {/* BEACH/SAND FILL (below bathymetry to bottom of graph) - extends from shore to breaking point */}
                  {bathymetryData.length > 0 && (
                    <Area 
                      yAxisId="main"
                      type="monotone"
                      dataKey="bathymetryY"
                      stroke="none"
                      fill="url(#beachGradient)"
                      fillOpacity={1}
                      baseLine={maxY}
                      connectNulls={false}
                    />
                  )}
                  
                  {/* WATER FILL (from bathymetry to water surface at 0) - extends from shore to breaking point */}
                  {bathymetryData.length > 0 && (
                    <Area 
                      yAxisId="main"
                      type="monotone"
                      dataKey="bathymetryY"
                      stroke="none"
                      fill="url(#waterGradient)"
                      fillOpacity={0.6}
                      baseLine={0}
                      connectNulls={false}
                    />
                  )}
                  
                  {/* BATHYMETRY LINE (beach bottom) - extends from shore to offshore (MAX_DISTANCE) */}
                  {bathymetryData.length > 0 && (
                    <Line 
                      yAxisId="main"
                      type="monotone"
                      dataKey="bathymetryY"
                      stroke="#5d4037"
                      strokeWidth={4}
                      dot={false}
                      name="Bathymetry"
                      connectNulls={false}
                    />
                  )}
                  
                  {/* WAVE CREST ENVELOPE - stops at breaking point */}
                  {waveEnvelopeData.length > 0 && (
                    <Line 
                      yAxisId="main"
                      type="monotone"
                      data={waveEnvelopeData}
                      dataKey="waveCrestY"
                      stroke="#64b5f6"
                      strokeWidth={2.5}
                      strokeDasharray="6 4"
                      dot={false}
                      name="Wave Crest"
                      connectNulls={true}
                    />
                  )}
                  
                  {/* WAVE TROUGH ENVELOPE - stops at breaking point */}
                  {waveEnvelopeData.length > 0 && (
                    <Line 
                      yAxisId="main"
                      type="monotone"
                      data={waveEnvelopeData}
                      dataKey="waveTroughY"
                      stroke="#64b5f6"
                      strokeWidth={2.5}
                      strokeDasharray="6 4"
                      dot={false}
                      name="Wave Trough"
                      connectNulls={true}
                    />
                  )}
                  
                  {/* WAVE SURFACE (actual trigonometric wave shape) - smooth continuous curve */}
                  {waveShapeData.length > 0 && (
                    <Line 
                      yAxisId="main"
                      type="monotoneX"
                      data={waveShapeData}
                      dataKey="y"
                      stroke="#1565c0"
                      strokeWidth={4}
                      dot={false}
                      name="Wave Surface"
                      connectNulls={false}
                      isAnimationActive={false}
                      activeDot={{ r: 6, fill: '#1565c0' }}
                    />
                  )}
                  
                  {/* WATER SURFACE (at y=0) - Mean Sea Level */}
                  <ReferenceLine 
                    yAxisId="main"
                    y={0} 
                    stroke="#666666" 
                    strokeWidth={3}
                    strokeDasharray="8 4"
                  />
                  
                  {/* BREAKING POINT - Vertical line at breaking distance */}
                  {/* CRITICAL: Breaking point must be at wave CREST (peak), positioned correctly */}
                  {(breakingDistM !== undefined && breakingDistM !== null) && (
                    <ReferenceLine 
                      yAxisId="main"
                      x={breakingDistDisplay} 
                      stroke="#e64a19" 
                      strokeWidth={4}
                      strokeDasharray="0"
                      label={{ value: 'Breaking', position: 'top', fill: '#e64a19', fontSize: '13px', fontWeight: 'bold' }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
              
              {/* DETAILED LEGEND */}
              <div style={{ 
                marginTop: '24px', 
                padding: '20px', 
                backgroundColor: '#f5f5f5', 
                borderRadius: '8px',
                fontSize: '14px',
                lineHeight: '2',
                border: '1px solid #e0e0e0'
              }}>
                <strong style={{ color: '#1976d2', fontSize: '16px', display: 'block', marginBottom: '12px' }}>Legend Guide:</strong>
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
                  gap: '16px'
                }}>
                  {/* Bathymetry */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      width: '50px', 
                      height: '4px', 
                      backgroundColor: '#5d4037',
                      borderRadius: '2px'
                    }}></div>
                    <div>
                      <strong style={{ color: '#5d4037' }}>Bathymetry</strong>
                      <div style={{ fontSize: '13px', color: '#666' }}>Beach profile (solid brown)</div>
                    </div>
                  </div>
                  
                  {/* Wave Surface */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      width: '50px', 
                      height: '4px', 
                      backgroundColor: '#1565c0',
                      borderRadius: '2px'
                    }}></div>
                    <div>
                      <strong style={{ color: '#1565c0' }}>Wave Surface</strong>
                      <div style={{ fontSize: '13px', color: '#666' }}>Actual wave shape (solid blue)</div>
                    </div>
                  </div>
                  
                  {/* Wave Envelope */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      width: '50px', 
                      height: '3px', 
                      background: 'repeating-linear-gradient(to right, #64b5f6 0px, #64b5f6 6px, transparent 6px, transparent 10px)',
                      borderRadius: '2px'
                    }}></div>
                    <div>
                      <strong style={{ color: '#1976d2' }}>Wave Envelope</strong>
                      <div style={{ fontSize: '13px', color: '#666' }}>Crest/trough limits (dashed light blue)</div>
                    </div>
                  </div>
                  
                  {/* Breaking Point */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      width: '4px', 
                      height: '40px', 
                      backgroundColor: '#e64a19',
                      borderRadius: '2px'
                    }}></div>
                    <div>
                      <strong style={{ color: '#e64a19' }}>Breaking Point</strong>
                      <div style={{ fontSize: '13px', color: '#666' }}>Where waves break (red-orange vertical)</div>
                    </div>
                  </div>
                  
                  {/* Mean Sea Level */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      width: '50px', 
                      height: '3px', 
                      background: 'repeating-linear-gradient(to right, #666666 0px, #666666 8px, transparent 8px, transparent 12px)',
                      borderRadius: '2px'
                    }}></div>
                    <div>
                      <strong style={{ color: '#666666' }}>Mean Sea Level</strong>
                       <div style={{ fontSize: '13px', color: '#666' }}>Reference level (dashed gray)</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Physics explanation */}
            <div style={{ marginTop: '24px', padding: '20px', background: physicsCardBg, borderRadius: '8px', lineHeight: '1.8', fontSize: '14px', color: physicsTextColor, border: `1px solid ${physicsBorderColor}` }}>
              <h4 style={{ marginTop: 0, color: physicsTextColor }}>How It Works:</h4>
              <ul style={{ marginLeft: '20px' }}>
                <li><strong>Shoaling:</strong> As waves move into shallower water, group velocity decreases and wave height increases (energy conservation)</li>
                <li><strong>Breaking:</strong> Waves break when H ≥ γ × depth (γ ≈ 0.78 for random waves)</li>
                {(() => {
                  const hs = convertHeight(offshore.Hs_m || 0);
                  const breakingH = convertHeight(breaking.height_m || 0);
                  const breakingDist = convertDistance(breaking.distance_from_shore_m || 0);
                  const breakingDepth = convertHeight(breaking.depth_m || 0);
                  return (
                    <>
                      <li><strong>Breaking Point:</strong> {breakingDist.value.toFixed(0)} {breakingDist.unit} from shore at depth {breakingDepth.value.toFixed(1)} {breakingDepth.unit}</li>
                      <li><strong>Transformation:</strong> Offshore {hs.value.toFixed(2)} {hs.unit} → Breaking {breakingH.value.toFixed(2)} {breakingH.unit} ({(breaking.height_m / offshore.Hs_m).toFixed(2)}x amplification)</li>
                    </>
                  );
                })()}
              </ul>
            </div>
          </div>
        )}

        {physicsTab === 'scoring' && (() => {
          // Prepare time series data for scoring breakdown
          const scoringData = forecast.forecast.slice(0, 24).map((entry: any) => ({
            time: format(parseISO(entry.timestamp), 'HH:mm'),
            height: entry.sub_scores?.height ? entry.sub_scores.height * 10 : 0,
            period: entry.sub_scores?.period ? entry.sub_scores.period * 10 : 0,
            direction: entry.sub_scores?.direction ? entry.sub_scores.direction * 10 : 0,
            wind: entry.sub_scores?.wind ? entry.sub_scores.wind * 10 : 0,
            tide: entry.sub_scores?.tide ? entry.sub_scores.tide * 10 : 0,
            score: entry.surf_score || 0,
          }));

          return (
            <div>
              <h3 className="text-lg font-semibold mb-3" style={{ color: physicsTextColor }}>Score Breakdown</h3>
              
              {/* Sub-scores over time */}
              <div style={{ marginBottom: '24px' }}>
                <h4 className="text-sm font-medium mb-2" style={{ color: physicsTextMuted }}>Sub-scores Over Time</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={scoringData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={physicsBorderColor} />
                    <XAxis 
                      dataKey="time" 
                      tick={{ fontSize: '11px', fill: physicsTextMuted }}
                      interval={2}
                    />
                    <YAxis 
                      domain={[0, 10]} 
                      tick={{ fontSize: '11px', fill: physicsTextMuted }}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        background: physicsBgColor, 
                        border: `1px solid ${physicsBorderColor}`, 
                        borderRadius: '4px', 
                        color: physicsTextColor 
                      }} 
                    />
                    <Legend 
                      wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                      iconType="line"
                    />
                    <Line type="monotone" dataKey="height" stroke="#f97316" strokeWidth={2} dot={false} name="Height" />
                    <Line type="monotone" dataKey="period" stroke="#60a5fa" strokeWidth={2} dot={false} name="Period" />
                    <Line type="monotone" dataKey="direction" stroke="#34d399" strokeWidth={2} dot={false} name="Direction" />
                    <Line type="monotone" dataKey="wind" stroke="#fbbf24" strokeWidth={2} dot={false} name="Wind" />
                    <Line type="monotone" dataKey="tide" stroke="#a78bfa" strokeWidth={2} dot={false} name="Tide" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Overall score over time */}
              <div>
                <h4 className="text-sm font-medium mb-2" style={{ color: physicsTextMuted }}>Overall Score Over Time</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={scoringData}>
                    <defs>
                      <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={physicsBorderColor} />
                    <XAxis 
                      dataKey="time" 
                      tick={{ fontSize: '11px', fill: physicsTextMuted }}
                      interval={2}
                    />
                    <YAxis 
                      domain={[0, 10]} 
                      tick={{ fontSize: '11px', fill: physicsTextMuted }}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        background: physicsBgColor, 
                        border: `1px solid ${physicsBorderColor}`, 
                        borderRadius: '4px', 
                        color: physicsTextColor 
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
            </div>
          );
        })()}

        {physicsTab === 'raw' && (
          <div>
            <h3 className="text-lg font-semibold mb-3" style={{ color: physicsTextColor }}>Raw Physics Data (for debugging)</h3>
            
            <div style={{ fontSize: '13px', fontFamily: 'monospace', background: physicsCardBg, padding: '16px', borderRadius: '6px', overflowX: 'auto', color: physicsTextColor, border: `1px solid ${physicsBorderColor}` }}>
              <p><strong>Offshore:</strong></p>
              <pre style={{ margin: '8px 0' }}>{JSON.stringify(offshore, null, 2)}</pre>
              
              <p style={{ marginTop: '16px' }}><strong>Breaking:</strong></p>
              <pre style={{ margin: '8px 0' }}>{JSON.stringify(breaking, null, 2)}</pre>
              
              {Object.keys(propagation).length > 0 && (
                <>
                  <p style={{ marginTop: '16px' }}><strong>Propagation:</strong></p>
                  <pre style={{ margin: '8px 0' }}>{JSON.stringify(propagation, null, 2)}</pre>
                </>
              )}
              
              {Object.keys(scoring).length > 0 && (
                <>
                  <p style={{ marginTop: '16px' }}><strong>Scoring:</strong></p>
                  <pre style={{ margin: '8px 0' }}>{JSON.stringify(scoring, null, 2)}</pre>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
