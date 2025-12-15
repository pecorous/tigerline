import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Theme = 'dark' | 'light';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>('dark');

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;
    
    // Remove both classes
    document.documentElement.classList.remove('light', 'dark');
    // Add current theme
    document.documentElement.classList.add(theme);
    // Apply background color
    if (theme === 'light') {
      document.body.style.background = '#ffffff';
      document.body.style.color = '#000000';
    } else {
      document.body.style.background = '#000000';
      document.body.style.color = '#ffffff';
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

