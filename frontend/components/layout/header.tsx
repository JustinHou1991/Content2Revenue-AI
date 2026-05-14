'use client'

import { useAuth } from '@/components/providers/auth-provider'
import { useThemeStore } from '@/stores/theme'
import { Button } from '@/components/ui/button'
import { Moon, Sun, LogOut, User } from 'lucide-react'

export function Header() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useThemeStore()

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6">
      <div>
        <h2 className="text-lg font-semibold">Content2Revenue AI</h2>
        <p className="text-xs text-muted-foreground">内容变现智能平台</p>
      </div>
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label="切换主题"
        >
          {theme === 'dark' ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </Button>
        <div className="flex items-center gap-2 text-sm">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <User className="h-4 w-4 text-primary" />
          </div>
          <div className="hidden md:block">
            <p className="text-sm font-medium leading-none">
              {user?.email || '用户'}
            </p>
            <p className="text-xs text-muted-foreground">
              {user?.role === 'admin' ? '管理员' : '用户'}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={logout}
          aria-label="退出登录"
        >
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </header>
  )
}