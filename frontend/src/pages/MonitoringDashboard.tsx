import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Select, Button, Space, Spin, Alert, Tabs } from 'antd';
import { ReloadOutlined, DeleteOutlined, ClockCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { getPerformanceMetrics, getHealthStatus, queryLogs, getSystemStats, clearOldMetrics, type HealthStatus, type LogEntry } from '../services/monitoring';
import './Monitoring.css';

const { Option } = Select;

const MonitoringDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [systemStats, setSystemStats] = useState<any>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<any>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [logLevel, setLogLevel] = useState<string | undefined>();
  const [keyword, setKeyword] = useState<string>('');
  const [logLimit, setLogLimit] = useState(100);

  // 刷新数据
  const refreshData = async () => {
    setLoading(true);
    try {
      const [health, stats, metrics] = await Promise.all([
        getHealthStatus(true),
        getSystemStats(),
        getPerformanceMetrics(undefined, 5, 'summary')
      ]);

      setHealthStatus(health.data);
      setSystemStats(stats.data);
      setPerformanceMetrics(metrics.data);
    } catch (error) {
      console.error('获取监控数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 查询日志
  const queryLogsData = async () => {
    setLoading(true);
    try {
      const response = await queryLogs({
        level: logLevel as any,
        keyword: keyword || undefined,
        limit: logLimit
      });
      setLogs(response.data);
    } catch (error) {
      console.error('查询日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 初始化和定时刷新
  useEffect(() => {
    refreshData();

    // 每30秒自动刷新一次
    const interval = setInterval(refreshData, 30000);

    return () => clearInterval(interval);
  }, []);

  // 清理旧指标
  const handleClearMetrics = async () => {
    try {
      await clearOldMetrics(24);
      refreshData();
    } catch (error) {
      console.error('清理指标失败:', error);
    }
  };

  // 解析日志行
  const parseLogLine = (line: string): LogEntry => {
    try {
      // 尝试解析JSON格式日志
      const jsonMatch = line.match(/\{.*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }

      // 如果不是JSON，返回简单的日志条目
      return {
        timestamp: new Date().toISOString(),
        level: 'INFO',
        message: line
      };
    } catch {
      return {
        timestamp: new Date().toISOString(),
        level: 'INFO',
        message: line
      };
    }
  };

  // 获取日志级别颜色
  const getLogLevelColor = (level: string) => {
    const colorMap: Record<string, string> = {
      'DEBUG': 'default',
      'INFO': 'blue',
      'WARNING': 'orange',
      'ERROR': 'red',
      'CRITICAL': 'red'
    };
    return colorMap[level] || 'default';
  };

  // 日志表格列
  const logColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp: string) => new Date(timestamp).toLocaleString('zh-CN')
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (level: string) => <Tag color={getLogLevelColor(level)}>{level}</Tag>
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      width: 200,
      ellipsis: true
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (message: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {message}
        </span>
      )
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (duration: number) => duration ? `${duration.toFixed(2)}ms` : '-'
    }
  ];

  // 解析日志数据
  const parsedLogs = logs.map(parseLogLine);

  return (
    <div className="monitoring-dashboard">
      <div className="dashboard-header">
        <h2>系统监控仪表板</h2>
        <Space>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={refreshData}
            loading={loading}
          >
            刷新
          </Button>
          <Button
            icon={<DeleteOutlined />}
            onClick={handleClearMetrics}
          >
            清理旧指标
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {/* 系统健康状态 */}
        {healthStatus && (
          <Card title="系统健康状态" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="CPU 使用率"
                  value={healthStatus.system?.cpu_percent || 0}
                  suffix="%"
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: (healthStatus.system?.cpu_percent || 0) > 80 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="内存使用率"
                  value={healthStatus.system?.memory?.percent || 0}
                  suffix="%"
                  valueStyle={{ color: (healthStatus.system?.memory?.percent || 0) > 80 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="磁盘使用率"
                  value={healthStatus.system?.disk?.percent || 0}
                  suffix="%"
                  valueStyle={{ color: (healthStatus.system?.disk?.percent || 0) > 80 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="系统状态"
                  value={healthStatus.status}
                  valueStyle={{ color: healthStatus.status === 'healthy' ? '#3f8600' : '#cf1322' }}
                />
              </Col>
            </Row>

            {/* 进程信息 */}
            {healthStatus.system?.process && (
              <div style={{ marginTop: 16 }}>
                <Alert
                  message={`进程 ID: ${healthStatus.system.process.pid} | 内存占用: ${healthStatus.system.process.memory_percent.toFixed(2)}% | 运行时间: ${healthStatus.system.process.status}`}
                  type="info"
                  showIcon
                />
              </div>
            )}
          </Card>
        )}

        {/* 系统统计 */}
        {systemStats && (
          <Card title="系统统计" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="用户总数"
                    value={systemStats.users.total}
                    prefix={<CheckCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="样本总数"
                    value={systemStats.samples.total}
                    prefix={<CheckCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="识别总数"
                    value={systemStats.recognition.total}
                    prefix={<CheckCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="最近24小时识别"
                    value={systemStats.recognition.recent_24h}
                    prefix={<ClockCircleOutlined />}
                  />
                </Card>
              </Col>
            </Row>
          </Card>
        )}

        {/* 性能指标 */}
        {performanceMetrics && (
          <Card title="性能指标（最近5分钟）" style={{ marginBottom: 16 }}>
            <Tabs defaultActiveKey="request">
              <Tabs.TabPane tab="请求性能" key="request">
                {performanceMetrics.http_request_duration_ms && (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title="平均响应时间"
                        value={performanceMetrics.http_request_duration_ms.average.toFixed(2)}
                        suffix="ms"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="P95 响应时间"
                        value={performanceMetrics.http_request_duration_ms.p95.toFixed(2)}
                        suffix="ms"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="P99 响应时间"
                        value={performanceMetrics.http_request_duration_ms.p99.toFixed(2)}
                        suffix="ms"
                      />
                    </Col>
                  </Row>
                )}
              </Tabs.TabPane>
              <Tabs.TabPane tab="请求计数" key="count">
                {performanceMetrics.http_requests_total && (
                  <Statistic
                    title="总请求数"
                    value={performanceMetrics.http_requests_total.count}
                  />
                )}
              </Tabs.TabPane>
            </Tabs>
          </Card>
        )}

        {/* 日志查询 */}
        <Card title="日志查询">
          <Space style={{ marginBottom: 16 }}>
            <Select
              placeholder="日志级别"
              style={{ width: 120 }}
              allowClear
              value={logLevel}
              onChange={setLogLevel}
            >
              <Option value="DEBUG">DEBUG</Option>
              <Option value="INFO">INFO</Option>
              <Option value="WARNING">WARNING</Option>
              <Option value="ERROR">ERROR</Option>
              <Option value="CRITICAL">CRITICAL</Option>
            </Select>
            <input
              type="text"
              placeholder="关键词搜索"
              style={{ width: 200 }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <Select
              placeholder="显示数量"
              style={{ width: 120 }}
              value={logLimit}
              onChange={setLogLimit}
            >
              <Option value={50}>50条</Option>
              <Option value={100}>100条</Option>
              <Option value={200}>200条</Option>
              <Option value={500}>500条</Option>
            </Select>
            <Button type="primary" onClick={queryLogsData}>查询</Button>
          </Space>

          <Table
            columns={logColumns}
            dataSource={parsedLogs}
            rowKey={(record, index) => `${record.timestamp}-${index}`}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条日志`
            }}
            scroll={{ x: 1200 }}
          />
        </Card>
      </Spin>
    </div>
  );
};

export default MonitoringDashboard;
