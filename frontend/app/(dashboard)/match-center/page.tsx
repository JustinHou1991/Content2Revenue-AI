'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { toast } from '@/hooks/use-toast'
import {
  Link2,
  TrendingUp,
  Users,
  Target,
  Heart,
  MousePointerClick,
  Lightbulb,
  ArrowRight,
  Sparkles,
  BarChart3,
} from 'lucide-react'

interface ContentItem {
  id: string
  title: string
  hook_type: string
  overall_score: number
}

interface LeadItem {
  id: string
  name: string
  company?: string
  industry?: string
  score: number
}

interface MatchResult {
  match_score: number
  audience_fit: number
  pain_point_relevance: number
  stage_alignment: number
  cta_appropriateness: number
  emotional_resonance: number
  recommendations: string[]
  content_id?: string
  lead_id?: string
}

const dimensionConfig: {
  key: keyof Omit<MatchResult, 'recommendations' | 'content_id' | 'lead_id'>
  label: string
  icon: React.ReactNode
}[] = [
  { key: 'audience_fit', label: '受众匹配度', icon: <Users className="h-4 w-4" /> },
  {
    key: 'pain_point_relevance',
    label: '痛点相关性',
    icon: <Target className="h-4 w-4" />,
  },
  {
    key: 'stage_alignment',
    label: '阶段对齐',
    icon: <BarChart3 className="h-4 w-4" />,
  },
  {
    key: 'cta_appropriateness',
    label: 'CTA 适配性',
    icon: <MousePointerClick className="h-4 w-4" />,
  },
  {
    key: 'emotional_resonance',
    label: '情感共鸣',
    icon: <Heart className="h-4 w-4" />,
  },
]

const mockContents: ContentItem[] = [
  { id: 'content-001', title: '产品测评 - 夏季护肤品推荐', hook_type: '问题引导型', overall_score: 85 },
  { id: 'content-002', title: '创业故事 - 从0到100万', hook_type: '故事叙事型', overall_score: 78 },
  { id: 'content-003', title: '效率工具推荐 - 10个必备App', hook_type: '清单列举型', overall_score: 91 },
]

const mockLeads: LeadItem[] = [
  { id: 'lead-001', name: '张伟', company: '星辰科技', industry: 'SaaS', score: 85 },
  { id: 'lead-002', name: '李娜', company: '创意文化', industry: '数字营销', score: 72 },
  { id: 'lead-003', name: '王强', company: '未来教育', industry: '在线教育', score: 68 },
]

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-amber-600'
  return 'text-red-600'
}

function getProgressColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500'
  if (score >= 60) return 'bg-amber-500'
  return 'bg-red-500'
}

export default function MatchCenterPage() {
  const [selectedContentId, setSelectedContentId] = useState<string>('')
  const [selectedLeadId, setSelectedLeadId] = useState<string>('')
  const [isMatching, setIsMatching] = useState(false)
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null)

  const { data: contents, isLoading: contentsLoading } = useQuery<ContentItem[]>(
    {
      queryKey: ['contents-for-match'],
      queryFn: async () => {
        try {
          const { data } = await api.get('/api/v1/content')
          return data.items || mockContents
        } catch {
          return mockContents
        }
      },
    }
  )

  const { data: leads, isLoading: leadsLoading } = useQuery<LeadItem[]>({
    queryKey: ['leads-for-match'],
    queryFn: async () => {
      try {
        const { data } = await api.get('/api/v1/leads')
        return data.items || mockLeads
      } catch {
        return mockLeads
      }
    },
  })

  const handleMatch = async () => {
    if (!selectedContentId || !selectedLeadId) {
      toast({
        title: '请选择内容和线索',
        description: '需要同时选择内容和线索才能进行匹配',
      })
      return
    }

    setIsMatching(true)
    setMatchResult(null)

    try {
      const { data } = await api.post('/api/v1/match', {
        content_id: selectedContentId,
        lead_id: selectedLeadId,
      })
      setMatchResult(data)
      toast({
        title: '匹配完成',
        description: `综合匹配得分 ${data.match_score} 分`,
      })
    } catch {
      setMatchResult({
        match_score: 87.5,
        audience_fit: 90.0,
        pain_point_relevance: 85.0,
        stage_alignment: 88.0,
        cta_appropriateness: 82.0,
        emotional_resonance: 91.0,
        content_id: selectedContentId,
        lead_id: selectedLeadId,
        recommendations: [
          '建议在视频前3秒强化痛点共鸣',
          'CTA按钮颜色建议改为橙色以提高点击率',
          '目标受众与内容调性高度匹配，建议加大投放',
          '可以在内容中增加行业案例来提升信任感',
        ],
      })
      toast({
        title: '匹配完成（模拟数据）',
        description: '综合匹配得分 87.5 分',
      })
    } finally {
      setIsMatching(false)
    }
  }

  const selectedContent = contents?.find((c) => c.id === selectedContentId)
  const selectedLead = leads?.find((l) => l.id === selectedLeadId)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">匹配中心</h1>
        <p className="text-muted-foreground">
          智能匹配内容与商业线索，找到最佳变现组合
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5" />
              选择内容
            </CardTitle>
            <CardDescription>选择已完成分析的内容</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {contentsLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <div className="space-y-2">
                <Label>内容列表</Label>
                <Select
                  value={selectedContentId}
                  onValueChange={setSelectedContentId}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择一条内容..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(contents || []).map((content) => (
                      <SelectItem key={content.id} value={content.id}>
                        <div className="flex items-center gap-2">
                          <span className="truncate max-w-[200px]">
                            {content.title}
                          </span>
                          <Badge variant="secondary" className="text-[10px]">
                            {content.overall_score}分
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {selectedContent && (
              <div className="rounded-lg border p-3">
                <p className="text-sm font-medium">{selectedContent.title}</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="outline">{selectedContent.hook_type}</Badge>
                  <span
                    className={`text-sm font-semibold ${getScoreColor(
                      selectedContent.overall_score
                    )}`}
                  >
                    {selectedContent.overall_score} 分
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Target className="h-5 w-5" />
              选择线索
            </CardTitle>
            <CardDescription>选择已完成分析的商业线索</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {leadsLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <div className="space-y-2">
                <Label>线索列表</Label>
                <Select
                  value={selectedLeadId}
                  onValueChange={setSelectedLeadId}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择一条线索..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(leads || []).map((lead) => (
                      <SelectItem key={lead.id} value={lead.id}>
                        <div className="flex items-center gap-2">
                          <span>{lead.name}</span>
                          {lead.company && (
                            <span className="text-xs text-muted-foreground">
                              ({lead.company})
                            </span>
                          )}
                          <Badge variant="secondary" className="text-[10px]">
                            {lead.score}分
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {selectedLead && (
              <div className="rounded-lg border p-3">
                <p className="text-sm font-medium">
                  {selectedLead.name}
                  {selectedLead.company && ` · ${selectedLead.company}`}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  {selectedLead.industry && (
                    <Badge variant="outline">{selectedLead.industry}</Badge>
                  )}
                  <span
                    className={`text-sm font-semibold ${getScoreColor(
                      selectedLead.score
                    )}`}
                  >
                    {selectedLead.score} 分
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-center">
        <Button
          size="lg"
          onClick={handleMatch}
          disabled={
            !selectedContentId || !selectedLeadId || isMatching
          }
          className="min-w-[200px]"
        >
          {isMatching ? (
            <>
              <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              匹配分析中...
            </>
          ) : (
            <>
              <Link2 className="mr-2 h-5 w-5" />
              开始匹配分析
            </>
          )}
        </Button>
      </div>

      {matchResult && (
        <div className="space-y-6">
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center gap-2 sm:flex-row sm:justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">综合匹配得分</p>
                  <p className="text-3xl font-bold">
                    <span className={getScoreColor(matchResult.match_score)}>
                      {matchResult.match_score}
                    </span>
                    <span className="text-lg text-muted-foreground">/100</span>
                  </p>
                </div>
                <div className="w-full max-w-xs">
                  <Progress
                    value={matchResult.match_score}
                    className={`h-3 [&>div]:${getProgressColor(matchResult.match_score)}`}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {dimensionConfig.map((dim) => {
              const score = matchResult[dim.key] as number
              return (
                <Card key={dim.key}>
                  <CardContent className="pt-6">
                    <div className="flex flex-col items-center gap-2 text-center">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                        {dim.icon}
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">
                          {dim.label}
                        </p>
                        <p
                          className={`text-xl font-bold ${getScoreColor(
                            score
                          )}`}
                        >
                          {score}
                        </p>
                      </div>
                      <Progress value={score} className="h-1.5 w-full" />
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {matchResult.recommendations &&
            matchResult.recommendations.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Lightbulb className="h-5 w-5" />
                    优化建议
                  </CardTitle>
                  <CardDescription>
                    基于匹配分析结果的优化方向
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {matchResult.recommendations.map((rec, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 rounded-lg border p-4"
                      >
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                          <span className="text-xs font-bold text-primary">
                            {i + 1}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm">{rec}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
        </div>
      )}
    </div>
  )
}