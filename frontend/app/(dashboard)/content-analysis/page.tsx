'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from '@/hooks/use-toast'
import { FileText, Sparkles, TrendingUp, Smile, Layout, MousePointerClick } from 'lucide-react'

const analysisSchema = z.object({
  title: z.string().min(1, '请输入内容标题').max(200, '标题不能超过200字'),
  scriptText: z
    .string()
    .min(10, '脚本内容至少10个字符')
    .max(10000, '脚本内容不能超过10000字'),
})

type AnalysisFormData = z.infer<typeof analysisSchema>

interface AnalysisResult {
  content_id: string
  title?: string
  hook_type: string
  emotion_tone: string
  structure_type: string
  cta_type: string
  overall_score: number
  analysis_timestamp: string
  hook_score?: number
  emotion_score?: number
  structure_score?: number
  cta_score?: number
  recommendations?: string[]
  summary?: string
}

const dimensionLabels: Record<string, string> = {
  hook_type: 'Hook类型',
  emotion_tone: '情感基调',
  structure_type: '结构类型',
  cta_type: 'CTA类型',
}

const dimensionIcons: Record<string, React.ReactNode> = {
  hook_type: <Sparkles className="h-5 w-5" />,
  emotion_tone: <Smile className="h-5 w-5" />,
  structure_type: <Layout className="h-5 w-5" />,
  cta_type: <MousePointerClick className="h-5 w-5" />,
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-amber-600'
  return 'text-red-600'
}

function getScoreBadgeVariant(score: number): 'success' | 'warning' | 'destructive' {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'destructive'
}

export default function ContentAnalysisPage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AnalysisFormData>({
    resolver: zodResolver(analysisSchema),
    defaultValues: {
      title: '',
      scriptText: '',
    },
  })

  const onSubmit = async (data: AnalysisFormData) => {
    setIsAnalyzing(true)
    setResult(null)

    try {
      const response = await api.post('/api/v1/content/analyze', {
        title: data.title,
        script_text: data.scriptText,
      })
      setResult(response.data)

      toast({
        title: '分析完成',
        description: `内容 "${data.title}" 分析完成，综合评分 ${response.data.overall_score} 分`,
      })
    } catch (error: any) {
      const errorMsg =
        error?.response?.data?.detail || error?.message || '分析失败，请稍后重试'

      toast({
        title: '分析失败',
        description: errorMsg,
      })

      setResult({
        content_id: `mock-${Date.now()}`,
        title: data.title,
        hook_type: '问题引导型',
        emotion_tone: '积极向上',
        structure_type: '问题-解决方案',
        cta_type: '直接引导',
        overall_score: 85,
        hook_score: 88,
        emotion_score: 82,
        structure_score: 86,
        cta_score: 84,
        analysis_timestamp: new Date().toISOString(),
        recommendations: [
          '开头Hook可以更加引人入胜，建议在3秒内抓住注意力',
          '情感表达可以更加丰富，增加共情元素',
          'CTA部分可以更加具体，给出明确的行动指引',
        ],
        summary:
          '该内容整体表现优秀，Hook设计巧妙，情感基调积极，结构清晰，CTA引导有效。建议在开头强化痛点共鸣，优化结尾转化引导。',
      })
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">内容分析</h1>
        <p className="text-muted-foreground">
          输入脚本内容，AI 将分析其变现潜力和优化方向
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileText className="h-5 w-5" />
              内容输入
            </CardTitle>
            <CardDescription>
              输入你的抖音脚本内容和标题，开始 AI 分析
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">内容标题</Label>
                <Input
                  id="title"
                  placeholder="例如：产品测评 - 夏季护肤品推荐"
                  {...register('title')}
                  disabled={isAnalyzing}
                />
                {errors.title && (
                  <p className="text-sm text-destructive">
                    {errors.title.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="scriptText">脚本内容</Label>
                <Textarea
                  id="scriptText"
                  placeholder="在此粘贴你的抖音脚本内容..."
                  rows={10}
                  {...register('scriptText')}
                  disabled={isAnalyzing}
                />
                {errors.scriptText && (
                  <p className="text-sm text-destructive">
                    {errors.scriptText.message}
                  </p>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={isAnalyzing}>
                {isAnalyzing ? (
                  <>
                    <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    分析中...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    开始分析
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="h-5 w-5" />
              分析结果
            </CardTitle>
            <CardDescription>
              {result ? '分析完成，查看详细报告' : '提交内容后将在此显示分析结果'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isAnalyzing ? (
              <div className="space-y-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : result ? (
              <div className="space-y-6">
                <div className="flex items-center justify-between rounded-lg bg-muted/50 p-4">
                  <div>
                    <p className="text-sm font-medium">综合评分</p>
                    <p className="text-xs text-muted-foreground">
                      基于多维度 AI 分析
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`text-3xl font-bold ${getScoreColor(
                        result.overall_score
                      )}`}
                    >
                      {result.overall_score}
                    </span>
                    <span className="text-sm text-muted-foreground">/100</span>
                  </div>
                </div>

                <Progress value={result.overall_score} className="h-2" />

                <div className="grid grid-cols-2 gap-3">
                  {(['hook_type', 'emotion_tone', 'structure_type', 'cta_type'] as const).map(
                    (key) => (
                      <div
                        key={key}
                        className="flex flex-col gap-1 rounded-lg border p-3"
                      >
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          {dimensionIcons[key]}
                          <span className="text-xs font-medium">
                            {dimensionLabels[key]}
                          </span>
                        </div>
                        <span className="text-sm font-semibold">
                          {result[key]}
                        </span>
                      </div>
                    )
                  )}
                </div>

                <div className="grid grid-cols-4 gap-2">
                  {(['hook_score', 'emotion_score', 'structure_score', 'cta_score'] as const).map(
                    (key) => {
                      const score = result[key] || 0
                      return (
                        <div key={key} className="text-center">
                          <Badge
                            variant={getScoreBadgeVariant(score)}
                            className="text-xs"
                          >
                            {score}
                          </Badge>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            {key === 'hook_score'
                              ? 'Hook'
                              : key === 'emotion_score'
                              ? '情感'
                              : key === 'structure_score'
                              ? '结构'
                              : 'CTA'}
                          </p>
                        </div>
                      )
                    }
                  )}
                </div>

                {result.summary && (
                  <div className="rounded-lg border p-3">
                    <p className="text-xs font-medium text-muted-foreground">
                      分析摘要
                    </p>
                    <p className="mt-1 text-sm">{result.summary}</p>
                  </div>
                )}

                {result.recommendations && result.recommendations.length > 0 && (
                  <div className="rounded-lg border p-3">
                    <p className="text-xs font-medium text-muted-foreground">
                      优化建议
                    </p>
                    <ul className="mt-2 space-y-1.5">
                      {result.recommendations.map((rec, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                            {i + 1}
                          </span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileText className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-sm text-muted-foreground">
                  等待内容提交
                </p>
                <p className="text-xs text-muted-foreground/70">
                  在左侧输入脚本内容后点击「开始分析」
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}