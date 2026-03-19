import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ProjectPage from './pages/ProjectPage'
import AnalysisPage from './pages/AnalysisPage'
import ScenarioPage from './pages/ScenarioPage'
import Navbar from './components/Navbar'
import MultiCriteriaPage from './pages/MultiCriteriaPage'
import AdminPage from './pages/AdminPage'

function PrivateRoute({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" />
}

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={
          <PrivateRoute><DashboardPage /></PrivateRoute>
        } />
        <Route path="/projects/:id" element={
          <PrivateRoute><ProjectPage /></PrivateRoute>
        } />
        <Route path="/projects/:id/analysis" element={
          <PrivateRoute><AnalysisPage /></PrivateRoute>
        } />
        <Route path="/multicriteria" element={
          <PrivateRoute><MultiCriteriaPage /></PrivateRoute>
        } />
        <Route path="/scenario" element={
          <PrivateRoute><ScenarioPage /></PrivateRoute>
        } />
        <Route path="/admin" element={
          <PrivateRoute><AdminPage /></PrivateRoute>
        } />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  )
}