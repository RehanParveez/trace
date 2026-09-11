import { useTranslation } from "react-i18next";

type Props = {
  className?: string;
  variant?: "default" | "compact";
};

export function LanguageSwitcher({ className = "", variant = "default" }: Props) {
  const { i18n, t } = useTranslation();

  const setLang = (lng: "en" | "ur") => {
    void i18n.changeLanguage(lng);
  };

  if (variant === "compact") {
    return (
      <div
        className={`inline-flex items-center gap-0.5 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-1.5 py-1 shadow-sm ${className}`}
      >
        <button
          type="button"
          onClick={() => setLang("en")}
          className={`rounded-[5px] px-2 py-0.5 text-[11px] font-semibold transition ${
            i18n.language === "en"
              ? "bg-[var(--color-trace-gold)] text-[var(--color-trace-navy)]"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]"
          }`}
        >
          EN
        </button>
        <button
          type="button"
          onClick={() => setLang("ur")}
          className={`rounded-[5px] px-2 py-0.5 text-[11px] font-semibold transition ${
            i18n.language === "ur"
              ? "bg-[var(--color-trace-gold)] text-[var(--color-trace-navy)]"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]"
          }`}
        >
          اردو
        </button>
      </div>
    );
  }

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <button
        type="button"
        onClick={() => setLang("en")}
        className={i18n.language === "en" ? "font-semibold" : "opacity-70"}
      >
        {t("lang.en")}
      </button>
      <button
        type="button"
        onClick={() => setLang("ur")}
        className={i18n.language === "ur" ? "font-semibold" : "opacity-70"}
      >
        {t("lang.ur")}
      </button>
    </div>
  );
}