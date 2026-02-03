import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import SampleUpload from './pages/SampleUpload';
import SampleList from './pages/SampleList';
import Recognition from './pages/Recognition';
import UserManagement from './pages/UserManagement';
import TrainingManagement from './pages/TrainingManagement';
import SystemManagement from './pages/SystemManagement';
import TokenManagement from './pages/TokenManagement';
import TokenAPITest from './pages/TokenAPITest';
import UserCenter from './pages/UserCenter';
import ScheduledTasks from './pages/ScheduledTasks';
import QuotaManagement from './pages/QuotaManagement';
import MonitoringDashboard from './pages/MonitoringDashboard';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import './App.css';

const queryClient = new QueryClient();

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div>加载中...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN}>
        <AuthProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/samples/upload" element={<SampleUpload />} />
                        <Route path="/samples" element={<SampleList />} />
                        <Route path="/recognition" element={<Recognition />} />
                        <Route path="/users" element={<UserManagement />} />
                        <Route path="/training" element={<TrainingManagement />} />
                        <Route path="/scheduled-tasks" element={<ScheduledTasks />} />
                        <Route path="/monitoring" element={<MonitoringDashboard />} />
                        <Route path="/system" element={<SystemManagement />} />
                        <Route path="/tokens" element={<TokenManagement />} />
                        <Route path="/api-test" element={<TokenAPITest />} />
                        <Route path="/user-center" element={<UserCenter />} />
                        <Route path="/quotas" element={<QuotaManagement />} />
                      </Routes>
                    </Layout>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

export default App;
