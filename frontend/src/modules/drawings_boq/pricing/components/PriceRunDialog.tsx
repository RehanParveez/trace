import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, Field, inputClass, Modal, Toggle } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { usePriceVersion, useRateBooks } from "../hooks";
import type { PriceVersionResult } from "../types/pricing.types";
import { canPriceWith, rateBookTitle, todayIso } from "../utils/pricing.utils";
import { FormError } from "./FormError";

interface PriceRunDialogProps {
  projectId: string;
  versionId: string;
  onClose: () => void;
  onDone: (result: PriceVersionResult) => void;
}

export function PriceRunDialog({ projectId, versionId, onClose, onDone }: PriceRunDialogProps) {
  const { t } = useTranslation();
  const booksQuery = useRateBooks({});
  const price = usePriceVersion(projectId, versionId);

  const [asOf, setAsOf] = useState(todayIso());
  const [automatic, setAutomatic] = useState(true);
  const [chosen, setChosen] = useState<string[]>([]);
  const [overwriteManual, setOverwriteManual] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usable = useMemo(() => booksQuery.books.filter(canPriceWith), [booksQuery.books]);
  const byId = useMemo(() => new Map(usable.map((b) => [b.id, b])), [usable]);

  function toggleBook(id: string) {
    setChosen((current) => (current.includes(id) ? current.filter((c) => c !== id) : [...current, id]));
  }

  function move(id: string, direction: -1 | 1) {
    setChosen((current) => {
      const index = current.indexOf(id);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    price.mutate(
      {
        as_of: asOf || null,
        rate_book_ids: automatic ? null : chosen,
        overwrite_manual: overwriteManual,
      },
      {
        onSuccess: (result) => {
          onDone(result);
          onClose();
        },
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.run.error", "Pricing failed. Nothing was changed."))),
      },
    );
  }

  return (
    <Modal
      title={t("pricing.run.title", "Price this BOQ")}
      description={t(
        "pricing.run.desc",
        "Fills in rates from project overrides, then your rate books in the order below, then the material library. Approved lines, estimated labour lines and manual rates are left alone unless you choose otherwise.",
      )}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-5">
        <Field
          label={t("pricing.run.asOf", "Price as of")}
          hint={t("pricing.run.asOfHint", "Decides which rate books are in effect and which escalation factors apply.")}
        >
          <input type="date" required className={inputClass} value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        </Field>

        <div>
          <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
            {t("pricing.run.books", "Rate books")}
          </div>
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setAutomatic(true)}
              className={`rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${automatic ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}
            >
              {t("pricing.run.automatic", "Automatic")}
            </button>
            <button
              type="button"
              onClick={() => setAutomatic(false)}
              className={`rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${!automatic ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}
            >
              {t("pricing.run.choose", "Choose books")}
            </button>
          </div>

          {automatic ? (
            <p className="text-[13px] leading-5 text-[var(--color-text-secondary)]">
              {t(
                "pricing.run.automaticHelp",
                "Every active rate book in effect on that date: your own books first (newest effective date first), then system books.",
              )}
            </p>
          ) : (
            <div className="space-y-2">
              {usable.length === 0 ? (
                <p className="text-[13px] text-[var(--color-text-secondary)]">
                  {t("pricing.run.noBooks", "There are no published rate books yet. Publish a draft first.")}
                </p>
              ) : (
                <ul className="space-y-1.5">
                  {usable.map((book) => {
                    const position = chosen.indexOf(book.id);
                    return (
                      <li key={book.id} className="flex items-center justify-between gap-3 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2">
                        <label className="flex min-w-0 items-center gap-2.5 text-[13px]">
                          <input type="checkbox" checked={position >= 0} onChange={() => toggleBook(book.id)} />
                          <span className="truncate">{rateBookTitle(book)}</span>
                          {book.is_system ? <Badge tone="blue">{t("pricing.system", "System")}</Badge> : null}
                          {book.status === "SUPERSEDED" ? <Badge tone="slate">{t("pricing.status.SUPERSEDED", "Superseded")}</Badge> : null}
                        </label>
                        {position >= 0 ? (
                          <span className="flex items-center gap-1 text-[12px] text-[var(--color-text-secondary)]">
                            #{position + 1}
                            <Button type="button" variant="ghost" size="sm" disabled={position === 0} aria-label={t("pricing.run.moveUp", "Move up")} onClick={() => move(book.id, -1)}>↑</Button>
                            <Button type="button" variant="ghost" size="sm" disabled={position === chosen.length - 1} aria-label={t("pricing.run.moveDown", "Move down")} onClick={() => move(book.id, 1)}>↓</Button>
                          </span>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
              <p className="text-[12px] text-[var(--color-text-muted)]">
                {t("pricing.run.orderHelp", "The first book with a matching rate wins, so put the book you trust most first.")}
              </p>
            </div>
          )}
        </div>

        <div className="flex items-start gap-3 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
          <Toggle checked={overwriteManual} onChange={() => setOverwriteManual((v) => !v)} label={t("pricing.run.overwrite", "Replace manual rates")} />
          <div>
            <div className="text-[13px] font-semibold">{t("pricing.run.overwrite", "Replace manual rates")}</div>
            <div className="text-[12.5px] leading-5 text-[var(--color-text-secondary)]">
              {overwriteManual
                ? t("pricing.run.overwriteOn", "Rates typed in by hand will be replaced wherever a book or override has one. Approved lines are still protected.")
                : t("pricing.run.overwriteOff", "Rates typed in by hand are kept.")}
            </div>
          </div>
        </div>

        <FormError message={error} />

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={price.isPending}>{t("common.cancel", "Cancel")}</Button>
          <Button
            type="submit"
            variant="primary"
            disabled={price.isPending || !asOf || (!automatic && chosen.filter((id) => byId.has(id)).length === 0)}
          >
            {price.isPending ? t("pricing.run.running", "Pricing…") : t("pricing.run.start", "Price BOQ")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
