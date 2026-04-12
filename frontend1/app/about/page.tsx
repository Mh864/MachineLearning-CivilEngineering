"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/flood/Header"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { STATIONS, PIPELINE_STEPS, MODEL_FEATURES } from "@/lib/constants"
import { checkApiStatus } from "@/lib/api"
import {
  Droplets,
  Cloud,
  Cog,
  Brain,
  Scale,
  Server,
  MapPin,
  Database,
  ArrowRight,
} from "lucide-react"
import { cn } from "@/lib/utils"

const stepIcons = [Droplets, Cloud, Cog, Brain, Scale, Server]

export default function About() {
  const [apiStatus, setApiStatus] = useState<boolean | null>(null)

  useEffect(() => {
    checkApiStatus().then(setApiStatus)
  }, [])

  return (
    <div className="min-h-screen bg-muted/30">
      <Header apiStatus={apiStatus} />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-foreground">About This Project</h2>
          <p className="text-muted-foreground mt-1">
            Understanding the Flood Risk Prediction System
          </p>
        </div>

        {/* Overview Section */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Droplets className="h-5 w-5 text-[#185FA5]" />
              What This Project Does
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground leading-relaxed">
              This system predicts the likelihood of river flooding based on historical river
              discharge measurements and rainfall data. By analyzing patterns in water flow rates
              over the past several days along with precipitation data, the machine learning model
              can estimate the probability of flooding occurring within the next 24 hours. The
              system monitors 10 gauge stations across the United States, providing real-time risk
              assessment for major rivers.
            </p>
          </CardContent>
        </Card>

        {/* Data Sources Section */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-[#185FA5]" />
              Data Sources
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#185FA5]/10">
                    <Droplets className="h-5 w-5 text-[#185FA5]" />
                  </div>
                  <div>
                    <h4 className="font-medium text-foreground">USGS</h4>
                    <p className="text-xs text-muted-foreground">
                      United States Geological Survey
                    </p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  Historical and real-time river discharge measurements from gauge stations across
                  the US. Data includes water flow rates measured in cubic feet per second (ft³/s).
                </p>
              </div>

              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#185FA5]/10">
                    <Cloud className="h-5 w-5 text-[#185FA5]" />
                  </div>
                  <div>
                    <h4 className="font-medium text-foreground">NOAA</h4>
                    <p className="text-xs text-muted-foreground">
                      National Oceanic and Atmospheric Administration
                    </p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  Precipitation data from weather stations near each river gauge. Rainfall
                  measurements help predict how water levels will change in the coming days.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stations Section */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-[#185FA5]" />
              Monitored Stations
            </CardTitle>
            <CardDescription>10 river gauge stations across the United States</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
              {STATIONS.map((station) => (
                <div
                  key={station.siteId}
                  className="flex items-center gap-2 rounded-lg border bg-card p-3"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-[#185FA5]/10">
                    <MapPin className="h-4 w-4 text-[#185FA5]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {station.name}
                    </p>
                    <p className="text-xs text-muted-foreground">{station.state}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Pipeline Section */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cog className="h-5 w-5 text-[#185FA5]" />
              Processing Pipeline
            </CardTitle>
            <CardDescription>How data flows from collection to prediction</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {PIPELINE_STEPS.map((step, index) => {
                const Icon = stepIcons[index]
                return (
                  <div
                    key={step.step}
                    className="relative rounded-lg border bg-card p-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#185FA5] text-white">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-muted-foreground">
                            Step {step.step}
                          </span>
                          {step.source && (
                            <Badge variant="outline" className="text-xs">
                              {step.source}
                            </Badge>
                          )}
                        </div>
                        <h4 className="font-medium text-foreground text-sm">{step.title}</h4>
                        <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
                      </div>
                    </div>
                    {index < PIPELINE_STEPS.length - 1 && (
                      <div className="absolute -right-2 top-1/2 -translate-y-1/2 hidden lg:block">
                        <ArrowRight className="h-4 w-4 text-muted-foreground/50" />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Features Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-[#185FA5]" />
              Model Features
            </CardTitle>
            <CardDescription>Input variables used for prediction</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {MODEL_FEATURES.map((feature, index) => (
                <div key={index} className="rounded-lg border bg-muted/30 p-3">
                  <code className="text-xs font-mono text-[#185FA5] bg-[#185FA5]/10 px-1.5 py-0.5 rounded">
                    {feature.name}
                  </code>
                  <p className="text-sm text-muted-foreground mt-2">{feature.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
