/* Types for the application */

export interface Developer {
  name: string;
  project_count: number;
  bio?: string;
  email?: string;
  phone?: string;
  locations: string[];
  technologies: string[];
  domains: string[];
  projects: string[];
  relevance_score: number;
}

export interface Project {
  name: string;
  description?: string;
  tagline?: string;
  developed_on?: string;
  developers: string[];
  technologies: string[];
  domains: string[];
  locations: string[];
  relevance_score: number;
}

export interface SearchResponse {
  query: string;
  entity_type: string;
  parsed_filters: Record<string, any>;
  developers: Developer[];
  projects: Project[];
  total_results: number;
}

export interface RecommendationResponse {
  source: string;
  source_type: string;
  recommended_projects: Project[];
  recommended_developers: Developer[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
  color?: string;
  size?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}
