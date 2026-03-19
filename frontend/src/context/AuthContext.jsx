import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('token') || null)
  const [user, setUser] = useState(
    JSON.parse(localStorage.getItem('user') || 'null')
  )

  const login = (accessToken, userData) => {
    localStorage.setItem('token', accessToken)
    localStorage.setItem('user', JSON.stringify(userData))
    setToken(accessToken)
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  // Перевірки ролей
  const isAdmin    = user?.role === 'admin'
  const isAnalyst  = user?.role === 'analyst' || user?.role === 'admin'
  const isManager  = user?.role === 'manager' || user?.role === 'admin'
  const canAnalyze = isAnalyst  // тільки аналітик і адмін запускають аналіз
  const canReport  = isAnalyst || isManager  // аналітик і менеджер можуть завантажувати звіти

  return (
    <AuthContext.Provider value={{
      token, user, login, logout,
      isAdmin, isAnalyst, isManager, canAnalyze, canReport
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}