"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const inputCls =
  "rounded-md border border-border bg-background px-3 py-2 text-sm " +
  "placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring";

// Birth year can't be in the future — derive the cap so it never goes stale.
const CURRENT_YEAR = new Date().getFullYear();

/** True if (y, m, d) is a real calendar date (rejects e.g. 30 Feb, 31 Apr). */
function isRealDate(y: number, m: number, d: number): boolean {
  const dt = new Date(y, m - 1, d);
  return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
}

export function BirthForm({ showNameField = true, onSubmit }: { showNameField?: boolean; onSubmit?: (message: string) => void }) {
  const [name, setName] = useState("");
  const [day, setDay] = useState("");
  const [month, setMonth] = useState("1");
  const [year, setYear] = useState("");
  const [hour, setHour] = useState("");
  const [minute, setMinute] = useState("");
  const [place, setPlace] = useState("");
  const [unknownTime, setUnknownTime] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!day || !year || !place.trim() || submitting) return;

    // Client-side birth-data validation (FR-C2 / FR-D4) — catch impossible dates
    // before they reach the backend.
    const y = parseInt(year, 10);
    const m = parseInt(month, 10);
    const d = parseInt(day, 10);
    if (y < 1900 || y > CURRENT_YEAR) {
      setError(`Birth year must be between 1900 and ${CURRENT_YEAR}.`);
      return;
    }
    if (!isRealDate(y, m, d)) {
      setError(`${MONTHS[m - 1]} ${d}, ${y} isn't a real date — please check the day.`);
      return;
    }
    if (!unknownTime && (hour !== "" || minute !== "")) {
      const h = parseInt(hour || "0", 10);
      const mn = parseInt(minute || "0", 10);
      if (h < 0 || h > 23 || mn < 0 || mn > 59) {
        setError("Time must be between 00:00 and 23:59.");
        return;
      }
    }
    setError("");

    const monthName = MONTHS[parseInt(month) - 1];
    const namePrefix = showNameField && name.trim() ? `My name is ${name.trim()}. ` : "";
    let message: string;

    if (unknownTime) {
      message =
        namePrefix +
        `I was born on ${day} ${monthName} ${year} (birth time unknown), in ${place.trim()}.`;
    } else {
      const h = (hour || "12").padStart(2, "0");
      const m = (minute || "00").padStart(2, "0");
      message =
        namePrefix +
        `I was born on ${day} ${monthName} ${year} at ${h}:${m}, in ${place.trim()}.`;
    }

    setSubmitting(true);
    try {
      onSubmit?.(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-3">
      {/* Name (optional) */}
      {showNameField && (
        <div className="flex flex-col gap-1">
          <label htmlFor="name" className="text-sm font-medium text-foreground">Your name</label>
          <input
            id="name"
            type="text"
            placeholder="e.g. Priya"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={cn(inputCls, "w-full")}
          />
        </div>
      )}

      {/* Date */}
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-foreground">Date of Birth</label>
        <div className="flex gap-2">
          <input
            type="number"
            min="1"
            max="31"
            placeholder="DD"
            value={day}
            onChange={(e) => setDay(e.target.value)}
            required
            className={cn(inputCls, "w-16 text-center")}
          />
          <select
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className={cn(inputCls, "flex-1")}
          >
            {MONTHS.map((name, i) => (
              <option key={name} value={String(i + 1)}>
                {name}
              </option>
            ))}
          </select>
          <input
            type="number"
            min="1900"
            max={CURRENT_YEAR}
            placeholder="YYYY"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            required
            className={cn(inputCls, "w-20 text-center")}
          />
        </div>
      </div>

      {/* Time */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Time of Birth</label>
        {!unknownTime && (
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="23"
              placeholder="HH"
              value={hour}
              onChange={(e) => setHour(e.target.value)}
              className={cn(inputCls, "w-16 text-center")}
            />
            <span className="text-muted-foreground font-medium">:</span>
            <input
              type="number"
              min="0"
              max="59"
              placeholder="MM"
              value={minute}
              onChange={(e) => setMinute(e.target.value)}
              className={cn(inputCls, "w-16 text-center")}
            />
          </div>
        )}
        <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={unknownTime}
            onChange={(e) => setUnknownTime(e.target.checked)}
            className="rounded"
          />
          I don&apos;t know my exact birth time
        </label>
      </div>

      {/* Place */}
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-foreground">Place of Birth</label>
        <input
          type="text"
          placeholder="e.g. Mumbai, India"
          value={place}
          onChange={(e) => setPlace(e.target.value)}
          required
          className={cn(inputCls, "w-full")}
        />
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      <Button type="submit" disabled={submitting} className="w-full">
        {submitting ? "Computing your chart…" : "Reveal My Chart"}
      </Button>
    </form>
  );
}
