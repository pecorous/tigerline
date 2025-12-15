import { createContext, useContext, useState, ReactNode } from 'react';

type UnitSystem = 'metric' | 'imperial';

interface UnitContextType {
  units: UnitSystem;
  toggleUnits: () => void;
  
  // Conversion helpers
  convertHeight: (meters: number) => { value: number; unit: string };
  convertDistance: (meters: number) => { value: number; unit: string };
  convertTemp: (celsius: number) => { value: number; unit: string };
  convertSpeed: (metersPerSec: number) => { value: number; unit: string };
}

const UnitContext = createContext<UnitContextType | undefined>(undefined);

export function UnitProvider({ children }: { children: ReactNode }) {
  const [units, setUnits] = useState<UnitSystem>('imperial');  // Default to imperial (ft, mph, °F)

  const toggleUnits = () => {
    setUnits(prev => prev === 'metric' ? 'imperial' : 'metric');
  };

  const convertHeight = (meters: number) => {
    if (units === 'metric') {
      return { value: meters, unit: 'm' };
    }
    return { value: meters * 3.28084, unit: 'ft' };
  };

  const convertDistance = (meters: number) => {
    if (units === 'metric') {
      return { value: meters, unit: 'm' };
    }
    return { value: meters * 3.28084, unit: 'ft' };
  };

  const convertTemp = (celsius: number) => {
    if (units === 'metric') {
      return { value: celsius, unit: '°C' };
    }
    return { value: celsius * 9/5 + 32, unit: '°F' };
  };

  const convertSpeed = (metersPerSec: number) => {
    if (units === 'metric') {
      return { value: metersPerSec, unit: 'm/s' };
    }
    return { value: metersPerSec * 2.237, unit: 'mph' };
  };

  return (
    <UnitContext.Provider value={{
      units,
      toggleUnits,
      convertHeight,
      convertDistance,
      convertTemp,
      convertSpeed
    }}>
      {children}
    </UnitContext.Provider>
  );
}

export function useUnits() {
  const context = useContext(UnitContext);
  if (context === undefined) {
    throw new Error('useUnits must be used within a UnitProvider');
  }
  return context;
}

