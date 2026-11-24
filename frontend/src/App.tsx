import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import SearchResultsPage from './pages/SearchResultsPage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import DeveloperDetailPage from './pages/DeveloperDetailPage';
import GraphExplorerPage from './pages/GraphExplorerPage';
import ChatPage from './pages/ChatPage';
import ReviewsPage from './pages/ReviewsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div style={{ minHeight: '100vh', background: 'var(--c-bg)' }}>
            <Navbar />
            <main style={{ minHeight: 'calc(100vh - 55px)' }}>
              <Routes>
                <Route path="/"                element={<HomePage />} />
                <Route path="/search"          element={<SearchResultsPage />} />
                <Route path="/project/:name"   element={<ProjectDetailPage />} />
                <Route path="/developer/:name" element={<DeveloperDetailPage />} />
                <Route path="/graph"           element={<GraphExplorerPage />} />
                <Route path="/chat"            element={<ChatPage />} />
                <Route path="/reviews"         element={<ReviewsPage />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
