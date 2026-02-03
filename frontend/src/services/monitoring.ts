import axios from 'axios';

// 性能指标接口
export interface PerformanceMetric {
  metric_name: string;
  time_range_minutes: number;
  count: number;
  average: number;
  p95: number;
  p99: number;
}

// 系统健康状态接口
export interface HealthStatus {
  status: string;
  timestamp: string;
  system?: {
    cpu_percent: number;
    memory: {
      total: number;
      available: number;
      percent: number;
      used: number;
    };
    disk: {
      total: number;
      used: number;
      free: number;
      percent: number;
    };
    process: {
      pid: number;
      memory_percent: number;
      create_time: string;
      status: string;
    };
  };
  components?: {
    database: string;
    inference_service: string;
    redis: string;
  };
}

// 日志记录接口
export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  module?: string;
  function?: string;
  line?: number;
  request_id?: string;
  duration_ms?: number;
  method?: string;
  path?: string;
  status_code?: number;
  error?: string;
}

// 系统统计信息接口
export interface SystemStats {
  users: {
    total: number;
  };
  samples: {
    total: number;
  };
  recognition: {
    total: number;
    recent_24h: number;
  };
  training: {
    total: number;
  };
}

// API响应通用接口
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  timestamp: string;
}

const API_BASE_URL = '/api/monitoring';

/**
 * 获取性能指标
 */
export const getPerformanceMetrics = async (
  metricName?: string,
  minutes = 5,
  formatType: 'summary' | 'raw' = 'summary'
): Promise<ApiResponse<PerformanceMetric | Record<string, PerformanceMetric>>> => {
  const params: any = { minutes, format_type: formatType };
  if (metricName) {
    params.metric_name = metricName;
  }

  const response = await axios.get(`${API_BASE_URL}/metrics`, { params });
  return response.data;
};

/**
 * 获取系统健康状态
 */
export const getHealthStatus = async (detailed = false): Promise<ApiResponse<HealthStatus>> => {
  const response = await axios.get(`${API_BASE_URL}/health`, {
    params: { detailed }
  });
  return response.data;
};

/**
 * 查询日志
 */
export const queryLogs = async (
  params: {
    level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
    start_time?: string;
    end_time?: string;
    limit?: number;
    keyword?: string;
  } = {}
): Promise<ApiResponse<string[]>> => {
  const response = await axios.get(`${API_BASE_URL}/logs`, { params });
  return response.data;
};

/**
 * 获取系统统计信息
 */
export const getSystemStats = async (): Promise<ApiResponse<SystemStats>> => {
  const response = await axios.get(`${API_BASE_URL}/stats`);
  return response.data;
};

/**
 * 清理旧的性能指标数据
 */
export const clearOldMetrics = async (hours = 24): Promise<ApiResponse<void>> => {
  const response = await axios.post(`${API_BASE_URL}/clear-old-metrics`, null, {
    params: { hours }
  });
  return response.data;
};
