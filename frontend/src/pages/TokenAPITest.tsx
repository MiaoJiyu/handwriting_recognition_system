import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Divider,
  Tag,
  message,
  Collapse,
  Alert,
  Empty,
  Spin
} from 'antd';
import {
  PlayCircleOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import axios from 'axios';  // Import axios directly for custom instance

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

// Create a custom axios instance for API testing (without token interceptor)
const apiTest = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

interface APIResponse {
  status: number;
  statusText: string;
  data: any;
  headers: Record<string, string>;
  duration: number;
}

const TokenAPITest: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<APIResponse | null>(null);
  const [token, setToken] = useState('');

  const endpoints = [
    // Token 基础 API
    { label: '获取当前用户信息', value: 'GET /v1/tokens/me' },
    { label: '获取 API 配置', value: 'GET /v1/tokens/config' },
    { label: '获取 API 信息', value: 'GET /v1/tokens/info' },
    { label: '验证 Token', value: 'POST /v1/tokens/verify' },

    // Token 管理器 API
    { label: '列出 Token', value: 'GET /tokens/list' },

    // 用户管理 API
    { label: '列出用户', value: 'GET /v1/users' },
    { label: '获取用户详情', value: 'GET /v1/users/1' },
    { label: '创建用户', value: 'POST /v1/users' },
    { label: '更新用户', value: 'PUT /v1/users/1' },
    { label: '设置密码', value: 'POST /v1/users/1/password' },
    { label: '删除用户', value: 'DELETE /v1/users/1' },

    // 学校管理 API
    { label: '列出学校', value: 'GET /v1/schools' },
    { label: '获取学校详情', value: 'GET /v1/schools/1' },
    { label: '创建学校', value: 'POST /v1/schools' },
    { label: '更新学校', value: 'PUT /v1/schools/1' },
    { label: '删除学校', value: 'DELETE /v1/schools/1' },

    // 配额管理 API (Token API)
    { label: '查询用户配额', value: 'POST /v1/tokens/quota/query' },
    { label: '设置用户配额', value: 'POST /v1/tokens/quota/set' },
    { label: '批量设置用户配额', value: 'POST /v1/tokens/quota/batch-set' },
    { label: '重置配额使用计数', value: 'POST /v1/tokens/quota/reset' },

    // 其他 API
    { label: '列出样本', value: 'GET /samples' },
    { label: '字迹识别', value: 'POST /recognition' },
    { label: '上传样本', value: 'POST /samples/upload' },
    { label: '获取训练记录', value: 'GET /training' }
  ];

  const handleExecute = async (values: any) => {
    setLoading(true);
    setResponse(null);

    try {
      const startTime = performance.now();

      // Parse endpoint
      const [method, path] = values.endpoint.split(' ');

      // Prepare headers
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Prepare request body
      let body = undefined;
      if (values.method === 'POST' && values.requestBody) {
        try {
          body = JSON.parse(values.requestBody);
        } catch (e) {
          message.error('请求体 JSON 格式错误');
          setLoading(false);
          return;
        }
      }

      // Make request - use custom apiTest instance
      let res;
      if (method === 'GET') {
        res = await apiTest.get(path, { headers });
      } else if (method === 'POST') {
        if (path.includes('/verify')) {
          res = await apiTest.post(path, { token: values.tokenOverride || token }, { headers });
        } else {
          res = await apiTest.post(path, body, { headers });
        }
      } else if (method === 'PUT') {
        res = await apiTest.put(path, body, { headers });
      } else if (method === 'DELETE') {
        res = await apiTest.delete(path, { headers });
      }

      const endTime = performance.now();
      const duration = Math.round(endTime - startTime);

      setResponse({
        status: res?.status || 0,
        statusText: 'OK',
        data: res?.data,
        headers: res?.headers as any,
        duration
      });

      message.success('请求成功');
    } catch (err: any) {
      const endTime = performance.now();
      const duration = Math.round(endTime - performance.now());

      setResponse({
        status: err.response?.status || 0,
        statusText: err.response?.statusText || 'Error',
        data: err.response?.data || err.message,
        headers: err.response?.headers || {},
        duration
      });

      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  const copyRequest = () => {
    const values = form.getFieldsValue();
    const curl = `curl -X ${values.endpoint.split(' ')[0]} http://localhost:8000${values.endpoint.split(' ')[1]} \\
  -H "Authorization: Bearer ${token}" \\
  -H "Content-Type: application/json" \\
  ${values.method === 'POST' ? `-d '${values.requestBody}'` : ''}`;

    navigator.clipboard.writeText(curl);
    message.success('cURL 命令已复制');
  };

  const copyResponse = () => {
    navigator.clipboard.writeText(JSON.stringify(response?.data, null, 2));
    message.success('响应已复制');
  };

  const handleEndpointChange = (value: string) => {
    const [method, path] = value.split(' ');
    form.setFieldsValue({
      endpoint: value,
      method: method,
      path: path
    });

    // Set default request body for certain endpoints
    if (path.includes('/verify')) {
      form.setFieldsValue({
        requestBody: JSON.stringify({ token: token }, null, 2)
      });
    } else if (path.includes('/users') && method === 'POST') {
      // Create user endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          username: "test_student",
          password: "password123",
          nickname: "测试学生",
          role: "student",
          school_id: 1
        }, null, 2)
      });
    } else if (path.includes('/users') && method === 'PUT') {
      // Update user endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          nickname: "测试学生（更新）"
        }, null, 2)
      });
    } else if (path.includes('/password')) {
      // Set password endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          password: "newpassword456"
        }, null, 2)
      });
    } else if (path.includes('/schools') && method === 'POST') {
      // Create school endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          name: "测试学校"
        }, null, 2)
      });
    } else if (path.includes('/schools') && method === 'PUT') {
      // Update school endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          name: "测试学校（更新）"
        }, null, 2)
      });
    } else if (path.includes('/quota/query')) {
      // Query quota endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          user_id: null
        }, null, 2)
      });
    } else if (path.includes('/quota/set')) {
      // Set quota endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          quota_type: "user",
          user_id: 1,
          minute_limit: 10,
          hour_limit: 100,
          day_limit: 1000,
          month_limit: 10000,
          total_limit: 0,
          description: "用户配额测试"
        }, null, 2)
      });
    } else if (path.includes('/quota/batch-set')) {
      // Batch set quota endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          user_ids: [1, 2, 3],
          minute_limit: 5,
          hour_limit: 50,
          day_limit: 500,
          month_limit: 5000,
          total_limit: 0,
          description: "批量用户配额测试"
        }, null, 2)
      });
    } else if (path.includes('/quota/reset')) {
      // Reset quota endpoint
      form.setFieldsValue({
        requestBody: JSON.stringify({
          quota_id: 1,
          reset_type: "all"
        }, null, 2)
      });
    } else {
      form.setFieldsValue({ requestBody: '' });
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <PlayCircleOutlined /> Token API 快速测试
      </Title>
      <Paragraph type="secondary">
        快速测试 Token API 的各项功能，包括配额管理、用户管理、学校管理等。支持通过 Token API 修改配额次数限制。
      </Paragraph>

      <Row gutter={24}>
        <Col xs={24} lg={12}>
          <Card title="API 请求配置" extra={<Button onClick={copyRequest} icon={<CopyOutlined />}>复制 cURL</Button>}>
            <Form form={form} layout="vertical" onFinish={handleExecute}>
              <Form.Item
                label="API Token"
                tooltip="输入您创建的 API Token，用于身份验证"
              >
                <Input.Password
                  placeholder="hwtk_xxx..."
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  prefix={<CheckCircleOutlined />}
                />
              </Form.Item>

              <Form.Item
                name="endpoint"
                label="API 端点"
                rules={[{ required: true, message: '请选择 API 端点' }]}
              >
                <Select
                  placeholder="选择要测试的 API"
                  onChange={handleEndpointChange}
                  options={endpoints}
                />
              </Form.Item>

              <Form.Item name="method" label="请求方法">
                <Input disabled />
              </Form.Item>

              <Form.Item name="path" label="请求路径">
                <Input disabled />
              </Form.Item>

              {form.getFieldValue('method') === 'POST' && (
                <Form.Item
                  name="requestBody"
                  label="请求体 (JSON)"
                  tooltip="POST 请求需要提供请求体"
                >
                  <TextArea
                    rows={6}
                    placeholder='{\n  "username": "teacher1",\n  "password": "password123",\n  "app_name": "MyApp"\n}'
                  />
                </Form.Item>
              )}

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={loading ? <LoadingOutlined /> : <PlayCircleOutlined />}
                  loading={loading}
                  block
                  size="large"
                >
                  发送请求
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title="API 响应"
            extra={response && <Button onClick={copyResponse} icon={<CopyOutlined />}>复制响应</Button>}
          >
            {loading ? (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <Spin size="large" tip="请求中..." />
              </div>
            ) : response ? (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <div>
                  <Space size="middle">
                    <Tag
                      icon={response.status >= 200 && response.status < 300 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                      color={response.status >= 200 && response.status < 300 ? 'success' : 'error'}
                    >
                      {response.status} {response.statusText}
                    </Tag>
                    <Tag color="blue">
                      {response.duration}ms
                    </Tag>
                  </Space>
                </div>

                <Divider>响应数据</Divider>

                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: '16px',
                    borderRadius: '4px',
                    overflow: 'auto',
                    maxHeight: '400px',
                    fontSize: '13px'
                  }}
                >
                  {JSON.stringify(response.data, null, 2)}
                </pre>

                <Collapse ghost size="small">
                  <Panel header="查看响应头" key="1">
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: '12px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        fontSize: '12px'
                      }}
                    >
                      {JSON.stringify(response.headers, null, 2)}
                    </pre>
                  </Panel>
                </Collapse>
              </Space>
            ) : (
              <Empty description="发送请求后响应将显示在这里" />
            )}
          </Card>
        </Col>
      </Row>

      <Card title="API 使用说明" style={{ marginTop: '24px' }}>
        <Collapse>
          <Panel header="获取 Token" key="1">
            <Alert
              message="步骤"
              description={
                <ol>
                  <li>前往 <Text code>Token 管理</Text> 页面</li>
                  <li>点击 <Text strong>创建 Token</Text> 按钮</li>
                  <li>配置 Token 名称、作用域和权限</li>
                  <li>保存生成的 Token（只显示一次）</li>
                </ol>
              }
              type="info"
            />
          </Panel>

          <Panel header="使用 Token" key="2">
            <Alert
              message="请求格式"
              description={
                <div>
                  <Paragraph>在所有 API 请求的 HTTP Header 中添加：</Paragraph>
                  <pre
                    style={{
                      background: '#f5f5f5',
                      padding: '12px',
                      borderRadius: '4px'
                    }}
                  >
                    Authorization: Bearer {'hwtk_xxx...'}
                  </pre>
                  <Paragraph>
                    确保将 <Text code>hwtk_xxx...</Text> 替换为您实际的 Token。
                  </Paragraph>
                </div>
              }
              type="info"
            />
          </Panel>

          <Panel header="Token 权限" key="3">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Tag color="blue">读取样本 - 可以查看和列出样本</Tag>
              <Tag color="green">写入样本 - 可以上传样本</Tag>
              <Tag color="orange">识别 - 可以执行字迹识别</Tag>
              <Tag color="cyan">读取用户 - 可以查看用户信息</Tag>
              <Tag color="purple">训练管理 - 可以管理模型训练</Tag>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>用户管理权限：</Text>
              <Tag color="cyan">管理用户 - 可以创建、编辑、删除用户，设置密码</Tag>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>学校管理权限：</Text>
              <Tag color="purple">管理学校 - 可以创建、编辑、删除学校</Tag>
            </Space>
          </Panel>

          <Panel header="用户管理 API" key="4">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Text strong>创建用户 (POST /v1/users)</Text>
              <Text>• 需要权限：manage_users</Text>
              <Text>• 教师：只能创建本校学生</Text>
              <Text>• 学校管理员：可以创建学生和教师</Text>
              <Text>• 系统管理员：可以创建任意角色用户</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>更新用户 (PUT /v1/users/`{`user_id`}`)</Text>
              <Text>• 需要权限：manage_users</Text>
              <Text>• 学生：只能编辑自己的信息</Text>
              <Text>• 教师：可以编辑本校学生</Text>
              <Text>• 管理员：可以编辑本校所有用户</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>设置密码 (POST /v1/users/`{`user_id`}`/password)</Text>
              <Text>• 需要权限：manage_users</Text>
              <Text>• 学生：只能设置自己的密码</Text>
              <Text>• 教师：可以设置本校学生密码</Text>
              <Text>• 管理员：可以设置本校任何用户密码</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>删除用户 (DELETE /v1/users/`{`user_id`}`)</Text>
              <Text>• 需要权限：manage_users</Text>
              <Text>• 不能删除自己的账户</Text>
              <Text>• 教师：只能删除本校学生</Text>
              <Text>• 学校管理员：只能删除本校学生和教师</Text>
              <Text>• 系统管理员：可以删除任何用户</Text>
            </Space>
          </Panel>

          <Panel header="学校管理 API" key="5">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Text strong>创建学校 (POST /v1/schools)</Text>
              <Text>• 需要权限：manage_schools（scope: admin）</Text>
              <Text>• 只有系统管理员可以创建学校</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>列出学校 (GET /v1/schools)</Text>
              <Text>• 需要权限：read_users</Text>
              <Text>• 任何角色都可以查看学校列表</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>更新学校 (PUT /v1/schools/`{`school_id`}`)</Text>
              <Text>• 需要权限：manage_schools（scope: admin）</Text>
              <Text>• 只有系统管理员可以更新学校</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>删除学校 (DELETE /v1/schools/`{`school_id`}`)</Text>
              <Text>• 需要权限：manage_schools（scope: admin）</Text>
              <Text>• 只有系统管理员可以删除学校</Text>
              <Text>• 不能删除有用户的学校</Text>
            </Space>
          </Panel>

          <Panel header="配额管理 API (Token API)" key="6">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Text strong>查询用户配额 (POST /v1/tokens/quota/query)</Text>
              <Text>• 权限：所有登录用户</Text>
              <Text>• 学生/教师：只能查询自己的配额</Text>
              <Text>• 学校管理员：可以查询本校用户配额</Text>
              <Text>• 系统管理员：可以查询任意用户配额</Text>
              <Text>• 返回配额限制、已使用次数和剩余次数</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>设置用户配额 (POST /v1/tokens/quota/set)</Text>
              <Text>• 需要权限：school_admin 或 system_admin</Text>
              <Text>• 学校管理员：只能设置本校用户配额</Text>
              <Text>• 系统管理员：可以设置任意用户配额</Text>
              <Text>• quota_type: "user" 或 "school"</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>批量设置配额 (POST /v1/tokens/quota/batch-set)</Text>
              <Text>• 需要权限：school_admin 或 system_admin</Text>
              <Text>• 支持同时设置多个用户或学校的配额</Text>
              <Text>• 所有配额参数将应用到选中的所有用户/学校</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>重置配额 (POST /v1/tokens/quota/reset)</Text>
              <Text>• 需要权限：school_admin 或 system_admin</Text>
              <Text>• reset_type 可选值："minute", "hour", "day", "month", "total", "all"</Text>
              <Text>• 学校管理员：只能重置本校配额</Text>
              <Text>• 系统管理员：可以重置任意配额</Text>
              <Divider style={{ margin: '8px 0' }} />
              <Alert
                message="配额限制说明"
                description={
                  <div>
                    <Text>• 所有限制值为 0 表示无限制</Text>
                    <br />
                    <Text>• minute_limit: 每分钟请求次数限制</Text>
                    <br />
                    <Text>• hour_limit: 每小时请求次数限制</Text>
                    <br />
                    <Text>• day_limit: 每天请求次数限制</Text>
                    <br />
                    <Text>• month_limit: 每月请求次数限制</Text>
                    <br />
                    <Text>• total_limit: 总请求次数限制</Text>
                  </div>
                }
                type="info"
                showIcon
              />
            </Space>
          </Panel>

          <Panel header="错误处理" key="7">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Text strong>常见错误代码：</Text>
              <Text>• 401 Unauthorized - Token 无效或已过期</Text>
              <Text>• 403 Forbidden - Token 权限不足或用户角色不允许该操作</Text>
              <Text>• 404 Not Found - 请求的资源不存在</Text>
              <Text>• 400 Bad Request - 用户名已存在、角色无效、尝试删除自己</Text>
              <Text>• 413 Payload Too Large - 文件过大</Text>
              <Text>• 429 Too Many Requests - 配额限制已触发</Text>
            </Space>
          </Panel>
        </Collapse>
      </Card>
    </div>
  );
};

export default TokenAPITest;
