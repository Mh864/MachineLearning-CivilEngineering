"use client"

import { Line, LineChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDischarge } from "@/lib/constants"

interface DischargeChartProps {
  values: number[]
}

export function DischargeChart({ values }: DischargeChartProps) {
  const chartData = values.slice(-7).map((value, index, arr) => {
    const daysAgo = arr.length - 1 - index
    return {
      day: daysAgo === 0 ? "Today" : daysAgo === 1 ? "1 day ago" : `${daysAgo} days ago`,
      discharge: value,
    }
  })

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium">Discharge Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
            Enter discharge values to see the trend chart
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">Discharge Trend (Last 7 Days)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                className="text-muted-foreground fill-muted-foreground"
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => formatDischarge(value)}
                className="text-muted-foreground fill-muted-foreground"
                width={60}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const data = payload[0].payload
                  return (
                    <div className="rounded-lg border bg-background px-3 py-2 shadow-md">
                      <p className="text-xs text-muted-foreground">{data.day}</p>
                      <p className="text-sm font-medium">
                        {formatDischarge(data.discharge)} ft³/s
                      </p>
                    </div>
                  )
                }}
              />
              <Line
                type="monotone"
                dataKey="discharge"
                stroke="#185FA5"
                strokeWidth={2}
                dot={{ fill: "#185FA5", strokeWidth: 0, r: 4 }}
                activeDot={{ r: 6, fill: "#185FA5" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
