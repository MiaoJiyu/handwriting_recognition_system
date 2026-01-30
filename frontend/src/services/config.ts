import { api } from './api';

export interface Config {
  max_upload_size: number;
  max_upload_size_mb: number;
}

export const configService = {
  getConfig: async (): Promise<Config> => {
    const res = await api.get<Config>('/config');
    return res.data;
  },
};
