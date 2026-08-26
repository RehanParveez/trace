import type { PropsWithChildren } from "react";
import "../styles/landing.css";

export function PublicLayout({ children }: PropsWithChildren) {
  return <div className="public-layout">{children}</div>;
}