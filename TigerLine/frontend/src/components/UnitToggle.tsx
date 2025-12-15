import { useUnits } from '../contexts/UnitContext';
import { useTheme } from '../contexts/ThemeContext';
import { motion } from 'motion/react';

export default function UnitToggle() {
  const { units, toggleUnits } = useUnits();
  const { theme } = useTheme();
  
  const isMetric = units === 'metric';
  
  // Theme-aware colors
  const containerBg = theme === 'light' ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)';
  const containerBorder = theme === 'light' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(255, 255, 255, 0.1)';
  const labelColor = theme === 'light' ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
  
  // Toggle track colors
  const trackBg = theme === 'light' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(0, 0, 0, 0.4)';
  
  // Text colors for toggle
  const activeTextColor = '#000000';
  const inactiveTextColor = theme === 'light' ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)';

  return (
    <div
      className="flex items-center gap-2 px-3 py-2 rounded-lg border transition-all cursor-pointer"
      style={{
        background: containerBg,
        borderColor: containerBorder,
      }}
      onClick={toggleUnits}
    >
      <span className="text-xs font-medium" style={{ color: labelColor }}>
        Units
      </span>
      <div 
        className="relative h-6 rounded-full p-0.5 transition-all flex items-center"
        style={{ 
          width: '56px',
          background: trackBg,
        }}
      >
        <motion.div
          className="absolute rounded-full shadow-sm flex items-center justify-center"
          style={{
            width: '26px',
            height: '20px',
            background: '#f97316',
            top: '2px',
          }}
          initial={false}
          animate={{
            x: isMetric ? 2 : 28,
          }}
          transition={{
            type: "spring",
            stiffness: 500,
            damping: 30
          }}
        >
          <span 
            className="text-xs font-medium"
            style={{ 
              color: '#000000',
              fontSize: '12px',
              lineHeight: '1',
            }}
          >
            {isMetric ? 'm' : 'ft'}
          </span>
        </motion.div>
        <div className="relative z-10 flex h-full items-center justify-between w-full px-1.5 pointer-events-none">
          <span 
            className="text-xs font-medium"
            style={{ 
              color: isMetric ? 'transparent' : inactiveTextColor,
              fontSize: '12px',
              transition: 'color 0.2s',
              visibility: isMetric ? 'hidden' : 'visible',
            }}
          >
            m
          </span>
          <span 
            className="text-xs font-medium"
            style={{ 
              color: !isMetric ? 'transparent' : inactiveTextColor,
              fontSize: '12px',
              transition: 'color 0.2s',
              visibility: !isMetric ? 'hidden' : 'visible',
            }}
          >
            ft
          </span>
        </div>
      </div>
    </div>
  );
}
