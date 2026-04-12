"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/flood/Header"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts"
import { MODEL_RESULTS, LEAD_TIME_ANALYSIS } from "@/lib/constants"
import { checkApiStatus } from "@/lib/api"
import { Award, TrendingDown, Info } from "lucide-react"
import { cn } from "@/lib/utils"

const comparisonData = [
  {
    metric: "Validation F1",
    "Logistic Regression": MODEL_RESULTS.logisticRegression.validationF1,
    LightGBM: MODEL_RESULTS.lightGBM.validationF1,
  },
  {
    metric: "Test F1",
    "Logistic Regression": MODEL_RESULTS.logisticRegression.testF1,
    LightGBM: MODEL_RESULTS.lightGBM.testF1,
  },
  {
    metric: "Test ROC-AUC",
    "Logistic Regression": MODEL_RESULTS.logisticRegression.testRocAuc,
    LightGBM: MODEL_RESULTS.lightGBM.testRocAuc,
  },
]

const leadTimeData = LEAD_TIME_ANALYSIS.map((d) => ({
  days: `${d.days}-day`,
  f1: d.f1,
}))

export default function ModelPerformance() {
  const [apiStatus, setApiStatus] = useState<boolean | null>(null)

  useEffect(() => {
    checkApiStatus().then(setApiStatus)
  }, [])

  return (
    <div className="min-h-screen bg-muted/30">
      <Header apiStatus={apiStatus} />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-foreground">Model Performance</h2>
          <p className="text-muted-foreground mt-1">
            Comparison of machine learning models for flood prediction
          </p>
        </div>

        {/* Model Cards */}
        <div className="grid gap-4 md:grid-cols-2 mb-6">
          {/* Logistic Regression Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Logistic Regression</CardTitle>
              <CardDescription>Baseline linear model</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-foreground">
                    {MODEL_RESULTS.logisticRegression.validationF1.toFixed(3)}
                  </p>
                  <p className="text-xs text-muted-foreground">Validation F1</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-foreground">
                    {MODEL_RESULTS.logisticRegression.testF1.toFixed(3)}
                  </p>
                  <p className="text-xs text-muted-foreground">Test F1</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-foreground">
                    {MODEL_RESULTS.logisticRegression.testRocAuc.toFixed(3)}
                  </p>
                  <p className="text-xs text-muted-foreground">ROC-AUC</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* LightGBM Card */}
          <Card className="border-[#185FA5] ring-1 ring-[#185FA5]">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">LightGBM</CardTitle>
                  <CardDescription>Gradient boosting model</CardDescription>
                </div>
                <Badge className="bg-[#185FA5] text-white">
                  <Award className="h-3 w-3 mr-1" />
                  Best Model
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-[#185FA5]">
                    {MODEL_RESULTS.lightGBM.validationF1.toFixed(3)}
                  </p>
                  <p className="text-xs text-muted-foreground">Validation F1</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-[#185FA5]">
                    {MODEL_RESULTS.lightGBM.testF1.toFixed(3)}
                  </p>
                  <p className="text-xs text-muted-foreground">Test F1</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-[#185FA5]">
                    {MODEL_RESULTS.lightGBM.testRocAuc.toFixed(3)}
                  </p>
                  <p className="text-xs text-muted-foreground">ROC-AUC</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid gap-6 lg:grid-cols-2 mb-6">
          {/* Comparison Bar Chart */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Model Comparison</CardTitle>
              <CardDescription>F1 Score and ROC-AUC comparison</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={comparisonData}
                    margin={{ top: 20, right: 20, left: 20, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis
                      dataKey="metric"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      className="fill-muted-foreground"
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      domain={[0, 1]}
                      className="fill-muted-foreground"
                    />
                    <Tooltip
                      content={({ active, payload, label }) => {
                        if (!active || !payload?.length) return null
                        return (
                          <div className="rounded-lg border bg-background px-3 py-2 shadow-md">
                            <p className="text-xs font-medium mb-1">{label}</p>
                            {payload.map((p, i) => (
                              <p key={i} className="text-xs" style={{ color: p.color }}>
                                {p.name}: {Number(p.value).toFixed(3)}
                              </p>
                            ))}
                          </div>
                        )
                      }}
                    />
                    <Bar dataKey="Logistic Regression" fill="#9ca3af" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="LightGBM" fill="#185FA5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-6 mt-2">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-[#9ca3af]" />
                  <span className="text-xs text-muted-foreground">Logistic Regression</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-[#185FA5]" />
                  <span className="text-xs text-muted-foreground">LightGBM</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Lead Time Analysis */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-amber-500" />
                Lead Time Analysis
              </CardTitle>
              <CardDescription>How accuracy changes with prediction horizon</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={leadTimeData}
                    margin={{ top: 20, right: 20, left: 20, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis
                      dataKey="days"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      className="fill-muted-foreground"
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      domain={[0, 1]}
                      className="fill-muted-foreground"
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const data = payload[0].payload
                        return (
                          <div className="rounded-lg border bg-background px-3 py-2 shadow-md">
                            <p className="text-xs text-muted-foreground">{data.days} ahead</p>
                            <p className="text-sm font-medium">F1: {data.f1.toFixed(3)}</p>
                          </div>
                        )
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="f1"
                      stroke="#185FA5"
                      strokeWidth={2}
                      dot={{ fill: "#185FA5", strokeWidth: 0, r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Explanation Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Info className="h-4 w-4 text-[#185FA5]" />
              Understanding the Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg border bg-muted/30 p-4">
                <h4 className="font-medium text-foreground mb-2">F1 Score</h4>
                <p className="text-sm text-muted-foreground">
                  Balances precision and recall. Higher is better. A score of 0.686 means the model
                  correctly identifies most floods while minimizing false alarms.
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <h4 className="font-medium text-foreground mb-2">ROC-AUC</h4>
                <p className="text-sm text-muted-foreground">
                  Measures how well the model distinguishes floods from non-floods. 0.968 is
                  excellent — the model ranks almost all flood events higher than non-flood events.
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <h4 className="font-medium text-foreground mb-2">Lead Time</h4>
                <p className="text-sm text-muted-foreground">
                  Predictions become less accurate further into the future. The model works best for
                  1-day ahead predictions with F1 of 0.786, dropping significantly beyond 3 days.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
