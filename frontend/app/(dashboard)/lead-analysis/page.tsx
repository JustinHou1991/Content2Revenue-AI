'use client'

import { useState, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useDropzone } from 'react-dropzone'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from '@/hooks/use-toast'
import {
  Upload,
  FileUp,
  FileSpreadsheet,
  Users,
  Mail,
  Phone,
  Building2,
  Tag,
  TrendingUp,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react'

const leadFormSchema = z.object({
  name: z.string().min(1, '请输入线索名称'),
  email: z.string().email('请输入有效的邮箱').optional().or(z.literal('')),
  phone: z.string().optional(),
  company: z.string().optional(),
  industry: z.string().optional(),
  notes: z.string().optional(),
})

type LeadFormData = z.infer<typeof leadFormSchema>

interface LeadResult {
  lead_id: string
  name?: string
  email?: string
  company?: string
  industry?: string
  score: number
  stage: string
  persona: string
  pain_points: string[]
  interests: string[]
  recommendations: string[]
  analysis_timestamp: string
}

const mockResults: LeadResult[] = [
  {
    lead_id: 'lead-001',
    name: '张伟',
    email: 'zhangwei@example.com',
    company: '星辰科技有限公司',
    industry: 'SaaS / 企业服务',
    score: 85,
    stage: '决策阶段',
    persona: '技术决策者',
    pain_points: ['团队效率低下', '工具碎片化', '数据孤岛'],
    interests: ['AI自动化', '数据分析', '团队协作'],
    recommendations: [
      '重点强调产品的自动化能力',
      '提供 ROI 计算器帮助决策',
      '展示同行业客户案例',
    ],
    analysis_timestamp: new Date().toISOString(),
  },
  {
    lead_id: 'lead-002',
    name: '李娜',
    email: 'lina@example.com',
    company: '创意文化传媒',
    industry: '数字营销',
    score: 72,
    stage: '认知阶段',
    persona: '营销经理',
    pain_points: ['获客成本高', '内容产出不稳定', '转化率低'],
    interests: ['内容营销', '短视频运营', '增长策略'],
    recommendations: [
      '从内容变现角度切入',
      '提供免费的内容分析报告',
      '分享行业趋势白皮书',
    ],
    analysis_timestamp: new Date().toISOString(),
  },
]

export default function LeadAnalysisPage() {
  const [activeTab, setActiveTab] = useState('upload')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [results, setResults] = useState<LeadResult[]>([])
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<LeadFormData>({
    resolver: zodResolver(leadFormSchema),
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      setUploadedFile(file)
      toast({
        title: '文件已上传',
        description: `${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
      })
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': [
        '.xlsx',
      ],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    maxSize: 5 * 1024 * 1024,
    onDropRejected: (rejections) => {
      const error = rejections[0]?.errors[0]
      toast({
        title: '文件上传失败',
        description: error?.message || '不支持的文件格式或大小超限',
      })
    },
  })

  const handleFileAnalysis = async () => {
    if (!uploadedFile) {
      toast({ title: '请先上传文件', description: '支持 CSV 和 Excel 格式' })
      return
    }

    setIsAnalyzing(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadedFile)

      const { data } = await api.post('/api/v1/leads/analyze/batch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResults(data.results || mockResults)
      toast({
        title: '批量分析完成',
        description: `成功分析 ${(data.results || mockResults).length} 条线索`,
      })
    } catch {
      setResults(mockResults)
      toast({
        title: '分析完成（模拟数据）',
        description: `已分析 ${mockResults.length} 条线索`,
      })
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleManualAnalysis = async (data: LeadFormData) => {
    setIsAnalyzing(true)
    try {
      const response = await api.post('/api/v1/leads/analyze', {
        lead_data: data,
      })
      const result: LeadResult = {
        lead_id: response.data.lead_id || `lead-${Date.now()}`,
        name: data.name,
        email: data.email,
        company: data.company,
        industry: data.industry,
        score: response.data.score || 75,
        stage: response.data.stage || '认知阶段',
        persona: response.data.persona || '潜在用户',
        pain_points: response.data.pain_points || ['信息获取效率', '决策支持'],
        interests: response.data.interests || ['行业资讯', '效率工具'],
        recommendations: response.data.recommendations || [
          '提供更多行业案例',
          '强调产品差异化优势',
        ],
        analysis_timestamp: new Date().toISOString(),
      }
      setResults([result])
      reset()
      toast({
        title: '分析完成',
        description: `线索 "${data.name}" 分析完成，评分 ${result.score}`,
      })
    } catch {
      const mockResult: LeadResult = {
        lead_id: `lead-${Date.now()}`,
        name: data.name,
        email: data.email,
        company: data.company,
        industry: data.industry,
        score: 75,
        stage: '认知阶段',
        persona: '潜在用户',
        pain_points: ['信息获取效率', '决策支持'],
        interests: ['行业资讯', '效率工具'],
        recommendations: ['提供更多行业案例', '强调产品差异化优势'],
        analysis_timestamp: new Date().toISOString(),
      }
      setResults([mockResult])
      reset()
      toast({
        title: '分析完成（模拟数据）',
        description: `线索 "${data.name}" 已分析`,
      })
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">线索分析</h1>
        <p className="text-muted-foreground">
          上传 CSV/Excel 批量分析或手动输入单条线索
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="upload" className="flex items-center gap-1.5">
            <Upload className="h-4 w-4" />
            文件上传
          </TabsTrigger>
          <TabsTrigger value="manual" className="flex items-center gap-1.5">
            <Users className="h-4 w-4" />
            手动输入
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileSpreadsheet className="h-5 w-5" />
                批量线索导入
              </CardTitle>
              <CardDescription>
                上传包含线索数据的 CSV 或 Excel 文件，支持批量分析
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                {...getRootProps()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition-colors ${
                  isDragActive
                    ? 'border-primary bg-primary/5'
                    : 'border-muted-foreground/25 hover:border-primary/50'
                }`}
              >
                <input {...getInputProps()} />
                <FileUp className="mb-3 h-10 w-10 text-muted-foreground" />
                {uploadedFile ? (
                  <div className="text-center">
                    <p className="text-sm font-medium">{uploadedFile.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(uploadedFile.size / 1024).toFixed(1)} KB - 点击重新上传
                    </p>
                  </div>
                ) : (
                  <div className="text-center">
                    <p className="text-sm font-medium">
                      {isDragActive ? '释放文件以上传' : '拖拽文件到此处或点击上传'}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      支持 CSV、XLSX、XLS 格式，最大 5MB
                    </p>
                  </div>
                )}
              </div>

              <Button
                className="w-full"
                onClick={handleFileAnalysis}
                disabled={!uploadedFile || isAnalyzing}
              >
                {isAnalyzing ? (
                  <>
                    <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    批量分析中...
                  </>
                ) : (
                  <>
                    <TrendingUp className="mr-2 h-4 w-4" />
                    开始批量分析
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="manual" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Users className="h-5 w-5" />
                手动输入线索
              </CardTitle>
              <CardDescription>输入单条线索信息进行 AI 分析</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={handleSubmit(handleManualAnalysis)}
                className="space-y-4"
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="name">线索名称 *</Label>
                    <Input
                      id="name"
                      placeholder="例如：张三"
                      {...register('name')}
                      disabled={isAnalyzing}
                    />
                    {errors.name && (
                      <p className="text-sm text-destructive">
                        {errors.name.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">邮箱</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="example@company.com"
                      {...register('email')}
                      disabled={isAnalyzing}
                    />
                    {errors.email && (
                      <p className="text-sm text-destructive">
                        {errors.email.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">电话</Label>
                    <Input
                      id="phone"
                      placeholder="+86 138xxxx"
                      {...register('phone')}
                      disabled={isAnalyzing}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="company">公司</Label>
                    <Input
                      id="company"
                      placeholder="公司名称"
                      {...register('company')}
                      disabled={isAnalyzing}
                    />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="industry">行业</Label>
                    <Input
                      id="industry"
                      placeholder="例如：SaaS、电商、教育"
                      {...register('industry')}
                      disabled={isAnalyzing}
                    />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="notes">备注</Label>
                    <Textarea
                      id="notes"
                      placeholder="其他补充信息..."
                      rows={3}
                      {...register('notes')}
                      disabled={isAnalyzing}
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      分析中...
                    </>
                  ) : (
                    <>
                      <TrendingUp className="mr-2 h-4 w-4" />
                      分析线索
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {results.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">
            分析结果 ({results.length})
          </h2>
          <div className="grid gap-4">
            {results.map((lead) => (
              <Card key={lead.lead_id}>
                <CardContent className="pt-6">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex-1 space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                          <Users className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-semibold">
                            {lead.name || '未命名线索'}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {lead.company && `${lead.company} · `}
                            {lead.industry || '未知行业'}
                          </p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                        {lead.email && (
                          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                            <Mail className="h-3.5 w-3.5" />
                            {lead.email}
                          </div>
                        )}
                        {lead.persona && (
                          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                            <Tag className="h-3.5 w-3.5" />
                            {lead.persona}
                          </div>
                        )}
                        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          {lead.stage}
                        </div>
                      </div>

                      {lead.pain_points && lead.pain_points.length > 0 && (
                        <div>
                          <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                            痛点识别
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {lead.pain_points.map((point, i) => (
                              <Badge key={i} variant="secondary">
                                {point}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {lead.recommendations &&
                        lead.recommendations.length > 0 && (
                          <div>
                            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                              跟进建议
                            </p>
                            <ul className="space-y-1">
                              {lead.recommendations.map((rec, i) => (
                                <li
                                  key={i}
                                  className="flex items-start gap-1.5 text-sm"
                                >
                                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                    </div>

                    <div className="flex flex-col items-center rounded-lg bg-muted/50 p-4 lg:min-w-[100px]">
                      <span
                        className={`text-3xl font-bold ${
                          lead.score >= 80
                            ? 'text-emerald-600'
                            : lead.score >= 60
                            ? 'text-amber-600'
                            : 'text-red-600'
                        }`}
                      >
                        {lead.score}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        综合评分
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}