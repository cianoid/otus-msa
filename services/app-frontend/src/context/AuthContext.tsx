import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { TokenPair } from '@/types'
import { authApi } from '@/api/client'

interface AuthContextType {
  isAuthenticated: boolean
  username: string | null
  login: (data: { username: string; password: string }) => Promise<void>
  register: (data: { username: string; password: string; email: string }) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const setTokens = useCallback((tokens: TokenPair) => {
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    try {
      const payload = JSON.parse(atob(tokens.access_token.split('.')[1]))
      setUsername(payload.sub || null)
    } catch {
      setUsername(null)
    }
    setIsAuthenticated(true)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setIsAuthenticated(false)
    setUsername(null)
  }, [])

  const login = useCallback(
    async (data: { username: string; password: string }) => {
      const tokens = await authApi.login(data)
      setTokens(tokens)
    },
    [setTokens]
  )

  const register = useCallback(
    async (data: { username: string; password: string; email: string }) => {
      const tokens = await authApi.register(data)
      setTokens(tokens)
    },
    [setTokens]
  )

  useEffect(() => {
    const accessToken = localStorage.getItem('access_token')
    const refreshToken = localStorage.getItem('refresh_token')
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    // Try decode access token
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]))
      const exp = payload.exp * 1000
      if (Date.now() < exp - 60000) {
        setUsername(payload.sub || null)
        setIsAuthenticated(true)
        setIsLoading(false)
        return
      }
    } catch {
      // invalid token
    }
    // Try refresh
    if (refreshToken) {
      authApi
        .refresh(refreshToken)
        .then((tokens) => setTokens(tokens))
        .catch(() => logout())
        .finally(() => setIsLoading(false))
    } else {
      logout()
      setIsLoading(false)
    }
  }, [setTokens, logout])

  return (
    <AuthContext.Provider value={{ isAuthenticated, username, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
