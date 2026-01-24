import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { FileImageOutlined, SearchOutlined, UserOutlined } from '@ant-design/icons';

const Dashboard: React.FC = () => {
  const { data: samples } = useQuery({
    queryKey: ['samples', 'stats'],
    queryFn: async () => {
      const res = await api.get('/api/samples?limit=1000');
      return res.data;
    },
  });

  const { data: users } = useQuery({
    queryKey: ['users', 'stats'],
    queryFn: async () => {
      const res = await api.get('/api/users');
      return res.data;
    },
  });

  const sampleCount = samples?.length || 0;
  const userCount = users?.length || 0;

  return (
    <div>
      <h1>仪表板</h1>
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="样本总数"
              value={sampleCount}
              prefix={<FileImageOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="用户总数"
              value={userCount}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="识别次数"
              value={0}
              prefix={<SearchOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
