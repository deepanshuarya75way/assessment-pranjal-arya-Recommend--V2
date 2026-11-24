/* API client for communicating with the FastAPI backend */
import axios from 'axios';
import type { SearchResponse, Project, Developer, RecommendationResponse, GraphData } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: { 'Content-Type': 'application/json' },
});

export const searchAPI = {
  search: async (query: string): Promise<SearchResponse> => {
    const { data } = await api.post('/search', { query });
    return data;
  },
};

export const projectsAPI = {
  list: async (): Promise<Project[]> => {
    const { data } = await api.get('/projects');
    return data;
  },
  get: async (name: string): Promise<Project> => {
    const { data } = await api.get(`/projects/${encodeURIComponent(name)}`);
    return data;
  },
  recommendations: async (name: string): Promise<RecommendationResponse> => {
    const { data } = await api.get(`/projects/${encodeURIComponent(name)}/recommendations`);
    return data;
  },
};

export const developersAPI = {
  list: async (): Promise<Developer[]> => {
    const { data } = await api.get('/developers');
    return data;
  },
  get: async (name: string): Promise<Developer> => {
    const { data } = await api.get(`/developers/${encodeURIComponent(name)}`);
    return data;
  },
  recommendations: async (name: string): Promise<RecommendationResponse> => {
    const { data } = await api.get(`/developers/${encodeURIComponent(name)}/recommendations`);
    return data;
  },
};

export const graphAPI = {
  get: async (query?: string): Promise<GraphData> => {
    const { data } = await api.get('/graph', { params: { q: query } });
    return data;
  },
};

export const seedAPI = {
  seed: async () => {
    const { data } = await api.post('/seed');
    return data;
  },
};

export interface ChatMessage {
  role: string;
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  query: string;
  mode: 'llm' | 'rag';
}

export interface ChatResponse {
  answer: string;
  sources: any[];
  response_mode: 'llm' | 'rag';
}

export const chatAPI = {
  chat: async (req: ChatRequest): Promise<ChatResponse> => {
    const { data } = await api.post('/chat', req);
    return data;
  },
};
