import { useTheme } from '../contexts/ThemeContext';
import { Sun, Moon } from 'lucide-react';
import { motion } from 'motion/react';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all"
      aria-label="Toggle theme"
    >
      <motion.div
        animate={{ rotate: theme === 'dark' ? 0 : 180 }}
        transition={{ duration: 0.3 }}
      >
        {theme === 'dark' ? (
          <Sun className="w-5 h-5 text-orange-500" />
        ) : (
          <Moon className="w-5 h-5 text-orange-500" />
        )}
      </motion.div>
    </button>
  );
}

