'use client'

import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import {
  FileText,
  Users,
  Link2,
  TrendingUp,
  ArrowRight,
  Activity,
} from 'lucide-react'
import Link from 'next/link'

interface DashboardStats {
  totalContentAnalyses: number
  totalLeadAnalyses: number
  totalMatches: number
  avgMatchScore: number
  recentContentAnalyses: number
  recentLeadAnalyses: number
  recentMatches: number
}

interface MonthlyData {
  month: string
  contentAnalyses: number
  leadAnalyses: number
  matches: number
}

interface ContentTypeData {
  name: string
  value: number
}

const COLORS = ['hsl(var(--primary))', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

const monthlyMockData: MonthlyData[] = [
  { month: '1月', contentAnalyses: 12, leadAnalyses: 8, matches: 5 },
  { month: '2月', contentAnalyses: 19, leadAnalyses: 15, matches: 10 },
  { month: '3月', contentAnalyses: 15, leadAnalyses: 20, matches: 12 },
  { month: '4月', contentAnalyses: 25, leadAnalyses: 22, matches: 18 },
  { month: '5月', contentAnalyses: 30, leadAnalyses: 28, matches: 22 },
  { month: '6月', contentAnalyses: 22, leadAnalyses: 18, matches: 15 },
]

const contentTypeMockData: ContentTypeData[] = [
  { name: '教程类', value: 35 },
  { name: '故事类', value: 25 },
  { name: '评测类', value: 20 },
  { name: '娱乐类', value: 15 },
  { name: '其他', value: 5 },
]

const quickActions = [
  {
    title: '内容分析',
    description: '分析脚本内容的变现潜力',
    icon: FileText,
    href: '/content-analysis',
    color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30',
  },
  {
    title: '线索分析',
    description: '批量分析商业线索数据',
    icon: Users,
    href: '/lead-analysis',
    color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30',
  },
  {
    title: '匹配中心',
    description: '智能匹配内容与商业线索',
    icon: Link2,
    href: '/match-center',
    color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30',
  },
  {
    title: '数据报表',
    description: '查看详细的分析报表',
    icon: TrendingUp,
    href: '/dashboard',
    color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
  },
]

const recentActivities = [
  {
    id: 1,
    type: 'content',
    name: '产品测评脚本 v3',
    action: '内容分析完成',
    score: 85,
    time: '10 分钟前',
  },
  {
    id: 2,
    type: 'lead',
    name: 'Q2 潜在客户列表',
    action: '线索分析完成',
    score: 72,
    time: '25 分钟前',
  },
  {
    id: 3,
    type: 'match',
    name: '教程系列 × 教育行业',
    action: '匹配分析完成',
    score: 91,
    time: '1 小时前',
  },
  {
    id: 4,
    type: 'content',
    name: '品牌故事脚本',
    action: '内容分析完成',
    score: 78,
    time: '2 小时前',
  },
  {
    id: 5,
    type: 'lead',
    name: '电商线索数据',
    action: '线索分析完成',
    score: 66,
    time: '3 小时前',
  },
]

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      try {
        const { data } = await api.get('/api/v1/dashboard/stats')
        return data
      } catch {
        return {
          totalContentAnalyses: 45,
          totalLeadAnalyses: 38,
          totalMatches: 22,
          avgMatchScore: 78,
          recentContentAnalyses: 12,
          recentLeadAnalyses: 8,
          recentMatches: 5,
        }
      }
    },
    refetchInterval: 30000,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">仪表盘</h1>
        <p className="text-muted-foreground">
          欢迎回来，查看最新的分析数据和业务概览
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-8 rounded" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
                <Skeleton className="mt-2 h-3 w-24" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  内容分析总数
                </CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.totalContentAnalyses ?? 0}</div>
                <p className="text-xs text-muted-foreground">
                  本月新增 {stats?.recentContentAnalyses ?? 0} 条
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  线索分析总数
                </CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.totalLeadAnalyses ?? 0}</div>
                <p className="text-xs text-muted-foreground">
                  本月新增 {stats?.recentLeadAnalyses ?? 0} 条
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  匹配总数
                </CardTitle>
                <Link2 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.totalMatches ?? 0}</div>
                <p className="text-xs text-muted-foreground">
                  本月新增 {stats?.recentMatches ?? 0} 条
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  平均匹配得分
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.avgMatchScore ?? 0}%</div>
                <p className="text-xs text-muted-foreground">
                  整体匹配质量良好
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">月度分析趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthlyMockData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="month" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                />
                <Legend />
                <Bar
                  dataKey="contentAnalyses"
                  name="内容分析"
                  fill="hsl(var(--primary))"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="leadAnalyses"
                  name="线索分析"
                  fill="#10b981"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="matches"
                  name="匹配"
                  fill="#8b5cf6"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">内容类型分布</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={contentTypeMockData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {contentTypeMockData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">
                <div className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  最近活动
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentActivities.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-full ${
                          activity.type === 'content'
                            ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30'
                            : activity.type === 'lead'
                            ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30'
                            : 'bg-purple-100 text-purple-600 dark:bg-purple-900/30'
                        }`}
                      >
                        {activity.type === 'content' ? (
                          <FileText className="h-4 w-4" />
                        ) : activity.type === 'lead' ? (
                          <Users className="h-4 w-4" />
                        ) : (
                          <Link2 className="h-4 w-4" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium">{activity.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {activity.action}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={
                          activity.score >= 80
                            ? 'success'
                            : activity.score >= 60
                            ? 'warning'
                            : 'destructive'
                        }
                      >
                        {activity.score}分
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {activity.time}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">快捷操作</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {quickActions.map((action) => (
                <Link key={action.href} href={action.href}>
                  <Button
                    variant="outline"
                    className="w-full justify-start gap-3 h-auto py-3"
                  >
                    <div
                      className={`flex h-9 w-9 items-center justify-center rounded-lg ${action.color}`}
                    >
                      <action.icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-medium">{action.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {action.description}
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}