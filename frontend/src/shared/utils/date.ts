const APP_TIME_ZONE = "Asia/Karachi";

export function todayLocal(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: APP_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

export function monthStartLocal(): string {
  return `${todayLocal().slice(0, 8)}01`;
}