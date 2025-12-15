import '../styles/globals.css';
import type { AppProps } from 'next/app';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { UnitProvider } from '../contexts/UnitContext';
import { ThemeProvider } from '../contexts/ThemeContext';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <UnitProvider>
          <Component {...pageProps} />
        </UnitProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
