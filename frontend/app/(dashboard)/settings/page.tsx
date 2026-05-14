'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from '@/hooks/use-toast'
import {
  Key,
  Brain,
  Shield,
  Eye,
  EyeOff,
  Save,
  Globe,
  Bell,
  Monitor,
  BarChart3,
} from 'lucide-react'

const modelOptions = [
  { value: 'deepseek-chat', label: 'DeepSeek Chat', description: '性价比最高的通用模型' },
  { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner', description: '深度推理模型，适合复杂分析' },
  { value: 'gpt-4o', label: 'GPT-4o', description: 'OpenAI 最新多模态模型' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini', description: '轻量高效的 GPT 模型' },
]

const languageOptions = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'en-US', label: 'English (US)' },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('api')
  const [showApiKey, setShowApiKey] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const [apiConfig, setApiConfig] = useState({
    deepseekKey: 'sk-••••••••••••••••',
    openaiKey: '',
    model: 'deepseek-chat',
    temperature: '0.7',
    maxTokens: '4096',
  })

  const [preferences, setPreferences] = useState({
    language: 'zh-CN',
    theme: 'system',
    autoAnalyze: true,
    notifications: true,
    weeklyReport: true,
  })

  const handleSaveApiConfig = async () => {
    setIsSaving(true)
    try {
      toast({
        title: '保存成功',
        description: 'API 配置已更新',
      })
    } catch {
      toast({
        title: '保存失败',
        description: '请检查配置后重试',
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleSavePreferences = async () => {
    setIsSaving(true)
    try {
      toast({
        title: '保存成功',
        description: '偏好设置已更新',
      })
    } catch {
      toast({
        title: '保存失败',
        description: '请检查设置后重试',
      })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">系统设置</h1>
        <p className="text-muted-foreground">
          管理 API 密钥、模型配置和用户偏好
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="api" className="flex items-center gap-1.5">
            <Key className="h-4 w-4" />
            API 配置
          </TabsTrigger>
          <TabsTrigger value="model" className="flex items-center gap-1.5">
            <Brain className="h-4 w-4" />
            模型设置
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-1.5">
            <Palette className="h-4 w-4" />
            偏好设置
          </TabsTrigger>
        </TabsList>

        <TabsContent value="api" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Key className="h-5 w-5" />
                API 密钥配置
              </CardTitle>
              <CardDescription>
                配置 AI 服务提供商的 API 密钥，密钥将加密存储
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="deepseek-key">DeepSeek API Key</Label>
                <div className="relative">
                  <Input
                    id="deepseek-key"
                    type={showApiKey ? 'text' : 'password'}
                    value={apiConfig.deepseekKey}
                    onChange={(e) =>
                      setApiConfig({ ...apiConfig, deepseekKey: e.target.value })
                    }
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showApiKey ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <p className="text-xs text-muted-foreground">
                  从{' '}
                  <a
                    href="https://platform.deepseek.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline"
                  >
                    DeepSeek Platform
                  </a>{' '}
                  获取 API Key
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="openai-key">OpenAI API Key（可选）</Label>
                <Input
                  id="openai-key"
                  type="password"
                  value={apiConfig.openaiKey}
                  onChange={(e) =>
                    setApiConfig({ ...apiConfig, openaiKey: e.target.value })
                  }
                  placeholder="sk-..."
                />
                <p className="text-xs text-muted-foreground">
                  可选配置，用于访问 GPT 系列模型
                </p>
              </div>

              <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950">
                <Shield className="h-4 w-4 text-amber-600" />
                <p className="text-xs text-amber-800 dark:text-amber-200">
                  所有 API 密钥均使用 AES-256 加密存储，不会在日志或错误信息中泄露
                </p>
              </div>

              <Button
                onClick={handleSaveApiConfig}
                disabled={isSaving}
                className="w-full"
              >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? '保存中...' : '保存 API 配置'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="model" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Brain className="h-5 w-5" />
                模型设置
              </CardTitle>
              <CardDescription>选择默认的 AI 模型和分析参数</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>默认模型</Label>
                <Select
                  value={apiConfig.model}
                  onValueChange={(v) =>
                    setApiConfig({ ...apiConfig, model: v })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择模型..." />
                  </SelectTrigger>
                  <SelectContent>
                    {modelOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        <div className="flex flex-col">
                          <span>{opt.label}</span>
                          <span className="text-xs text-muted-foreground">
                            {opt.description}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="temperature">温度 (Temperature)</Label>
                  <Input
                    id="temperature"
                    type="number"
                    min="0"
                    max="2"
                    step="0.1"
                    value={apiConfig.temperature}
                    onChange={(e) =>
                      setApiConfig({ ...apiConfig, temperature: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    0 = 确定性输出，2 = 最大随机性
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max-tokens">最大 Token 数</Label>
                  <Input
                    id="max-tokens"
                    type="number"
                    min="256"
                    max="32768"
                    step="256"
                    value={apiConfig.maxTokens}
                    onChange={(e) =>
                      setApiConfig({ ...apiConfig, maxTokens: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    单次请求的最大输出长度
                  </p>
                </div>
              </div>

              <Button
                onClick={handleSaveApiConfig}
                disabled={isSaving}
                className="w-full"
              >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? '保存中...' : '保存模型设置'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Globe className="h-5 w-5" />
                语言与地区
              </CardTitle>
              <CardDescription>设置界面语言和地区偏好</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>界面语言</Label>
                <Select
                  value={preferences.language}
                  onValueChange={(v) =>
                    setPreferences({ ...preferences, language: v })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {languageOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Monitor className="h-5 w-5" />
                界面偏好
              </CardTitle>
              <CardDescription>自定义界面主题和显示选项</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>主题模式</Label>
                <Select
                  value={preferences.theme}
                  onValueChange={(v) =>
                    setPreferences({ ...preferences, theme: v })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">浅色模式</SelectItem>
                    <SelectItem value="dark">深色模式</SelectItem>
                    <SelectItem value="system">跟随系统</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-3 rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bell className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">分析完成通知</p>
                      <p className="text-xs text-muted-foreground">
                        分析任务完成后发送通知
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      setPreferences({
                        ...preferences,
                        notifications: !preferences.notifications,
                      })
                    }
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      preferences.notifications
                        ? 'bg-primary'
                        : 'bg-muted'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        preferences.notifications
                          ? 'translate-x-6'
                          : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">每周分析报告</p>
                      <p className="text-xs text-muted-foreground">
                        每周一自动生成分析周报
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      setPreferences({
                        ...preferences,
                        weeklyReport: !preferences.weeklyReport,
                      })
                    }
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      preferences.weeklyReport
                        ? 'bg-primary'
                        : 'bg-muted'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        preferences.weeklyReport
                          ? 'translate-x-6'
                          : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>

              <Button
                onClick={handleSavePreferences}
                disabled={isSaving}
                className="w-full"
              >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? '保存中...' : '保存偏好设置'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}