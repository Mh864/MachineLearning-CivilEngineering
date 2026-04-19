"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { STATIONS, type Station } from "@/lib/constants"
import { Loader2, MapPin } from "lucide-react"

interface StationSelectorProps {
  selectedStation: Station
  onSelect: (station: Station) => void
  latestLoading?: boolean
}

export function StationSelector({
  selectedStation,
  onSelect,
  latestLoading = false,
}: StationSelectorProps) {
  return (
    <div className="space-y-2 w-full">
      <label
        htmlFor="gauge-station"
        className="block text-left text-sm font-medium text-foreground"
      >
        Gauge station
      </label>
      {latestLoading ? (
        <p className="flex items-center justify-start gap-1.5 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading latest data…
        </p>
      ) : null}
      <div className="w-full px-0 sm:px-1">
        <Select
          value={selectedStation.siteId}
          onValueChange={(siteId) => {
            const next = STATIONS.find((s) => s.siteId === siteId)
            if (next) onSelect(next)
          }}
          disabled={latestLoading}
        >
          <SelectTrigger
            id="gauge-station"
            className="h-auto min-h-10 w-full py-2 text-sm [&_svg:not([class*='size-'])]:size-4"
          >
            <MapPin className="shrink-0 text-[#185FA5]" aria-hidden />
            <SelectValue placeholder="Choose a river…" />
          </SelectTrigger>
          <SelectContent className="max-h-[min(320px,70vh)]">
            {STATIONS.map((station) => (
              <SelectItem key={station.siteId} value={station.siteId}>
                {station.name} ({station.state}) · {station.siteId}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
