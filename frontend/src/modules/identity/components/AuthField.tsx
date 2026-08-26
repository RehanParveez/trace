import type {InputHTMLAttributes, ReactNode
} from "react";

type AuthFieldProps =
  InputHTMLAttributes<HTMLInputElement> & {
    label: string;
    error?: string;
    hint?:  ReactNode;
  };

export function AuthField({
  label,
  error,
  hint,
  id,
  ...props
}: AuthFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center justify-between text-[12px] font-semibold text-[#332A21]">
        <span>{label}</span>

        {hint && (
          <span className="font-normal text-[#A2957C]">
            {hint}
          </span>
        )}
      </span>

      <input
        id={id}
        {...props}
        className={[
          "h-12 w-full rounded-[9px]",
          "border bg-[#FBF8F2]",
          "px-3.5 text-[13.5px]",
          "text-[#191410]",
          "outline-none transition",
          "placeholder:text-[#A2957C]",
          "focus:border-[#D9A441]",
          "focus:ring-4",
          "focus:ring-[#D9A441]/10",
          error
            ? "border-[#C24A3A]"
            : "border-[#E1D5BC]",
        ].join(" ")}
      />

      {error && (
        <span className="mt-1.5 block text-[11.5px] text-[#C24A3A]">
          {error}
        </span>
      )}
    </label>
  );
}