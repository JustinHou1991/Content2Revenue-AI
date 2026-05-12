import api from './api';

export interface User {
  id: string;
  email: string;
  role: string;
  status: string;
  tenant_id?: string;
  created_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData extends LoginCredentials {
  tenant_name?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthTokens & { user: User }> => {
    const { data } = await api.post('/api/v1/auth/login', credentials);
    return data;
  },

  register: async (data: RegisterData): Promise<User> => {
    const { data: response } = await api.post('/api/v1/auth/register', data);
    return response;
  },

  logout: async (): Promise<void> => {
    await api.post('/api/v1/auth/logout');
  },

  getMe: async (): Promise<User> => {
    const { data } = await api.get('/api/v1/auth/me');
    return data;
  },

  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    const { data } = await api.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
    return data;
  },
};

export const setTokens = (tokens: AuthTokens) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  }
};

export const clearTokens = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
};

export const getTokens = (): Partial<AuthTokens> => {
  if (typeof window !== 'undefined') {
    return {
      access_token: localStorage.getItem('access_token') || '',
      refresh_token: localStorage.getItem('refresh_token') || '',
    };
  }
  return {};
};