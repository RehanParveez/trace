import type {ReactNode,
} from "react";

type AuthNoticeProps = {
  tone?: "error" | "success" | "info";
  children: ReactNode;
};

const styles = {
  error:
    "border-[#C24A3A]/25 bg-[#F9E5DF] text-[#9A3D31]",

  success:
    "border-[#1E9D63]/25 bg-[#E4F5EC] text-[#176F49]",

  info:
    "border-[#3B7DC4]/25 bg-[#E7F0FA] text-[#2F68A8]",
};

export function AuthNotice({
  tone = "info",
  children,
}: AuthNoticeProps) {
  return (
    <div
      className={[
        "rounded-[9px] border",
        "px-3.5 py-3",
        "text-[12px] leading-5",
        styles[tone],
      ].join(" ")}
    >
      {children}
    </div>
  );
}