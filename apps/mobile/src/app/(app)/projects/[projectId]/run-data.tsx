import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {listBarMarks, listDeductions, listRunLedger, listSolids, listVersionLedger,
} from "../../../../api/runData";
import type { BarMark, CursorPage, Deduction, LedgerRow, QuantitySolid } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { Action, Badge, COLORS, Field, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

type Tab = "solids" | "ledger" | "deductions" | "bars";
type Row = QuantitySolid | LedgerRow | Deduction | BarMark;

const DEDUCTION_TYPES = ["OVERLAP_ALLOCATION", "EXTENT_TRIMMING", "VOID_DEDUCTION", "MATERIAL_SUBSTITUTION", "MEASUREMENT_CONVENTION"];
const PROVENANCE = ["IFC_EXACT", "SCHEDULE_IMPORT", "MANUAL", "RULE_ESTIMATE"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function pretty(value: unknown, limit = 1500) {
  const text = JSON.stringify(value, null, 1) ?? "";
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

export default function RunDataScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; runId?: string; versionId?: string }>();
  const runId = first(params.runId);
  const versionId = first(params.versionId);

  const [tab, setTab] = useState<Tab>("ledger");
  const [rows, setRows] = useState<Row[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [more, setMore] = useState(false);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState("");

  const [role, setRole] = useState("");
  const [workItem, setWorkItem] = useState("");
  const [ledgerSource, setLedgerSource] = useState<"run" | "version">(versionId ? "version" : "run");
  const [deductionType, setDeductionType] = useState("");
  const [provenance, setProvenance] = useState("");

  const fetchPage = useCallback(
    async (cursor?: string): Promise<CursorPage<Row>> => {
      if (!runId) throw new Error(tx("runData.noRun", "This version was not built from a calculation run."));
      if (tab === "solids") return listSolids(runId, { after: cursor, role });
      if (tab === "ledger") {
        return ledgerSource === "version" && versionId
          ? listVersionLedger(versionId, { after: cursor, workItemCode: workItem })
          : listRunLedger(runId, { after: cursor, workItemCode: workItem });
      }
      if (tab === "deductions") return listDeductions(runId, { after: cursor, deductionType });
      return listBarMarks(runId, { after: cursor, provenance, role });
    },
    [runId, versionId, tab, role, workItem, ledgerSource, deductionType, provenance],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setOpenId("");
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      const page = await fetchPage();
      setRows(page.rows);
      setNext(page.next);
      setError("");
    } catch (err) {
      setRows([]);
      setNext(null);
      setError(describeError(err, tx("runData.loadFailure", "Could not load this list.")));
    } finally {
      setLoading(false);
    }
  }, [fetchPage]);

  useEffect(() => {
    void reload();
  }, [tab, ledgerSource, deductionType, provenance, runId]);

  async function loadMore() {
    if (!next) return;
    setMore(true);
    try {
      const page = await fetchPage(next);
      setRows((current) => [...current, ...page.rows]);
      setNext(page.next);
    } catch (err) {
      setError(describeError(err, tx("runData.loadFailure", "Could not load this list.")));
    } finally {
      setMore(false);
    }
  }

  function toggle(id: string) {
    setOpenId((current) => (current === id ? "" : id));
  }

  const choiceRow = (values: string[], current: string, set: (value: string) => void, allLabel: string) => (
    <View style={[ui.row, isUrdu && ui.rtlRow]}>
      <Action title={allLabel} secondary={current !== ""} isUrdu={isUrdu} onPress={() => set("")} />
      {values.map((value) => (
        <Action key={value} title={value.replaceAll("_", " ")} secondary={current !== value} isUrdu={isUrdu} onPress={() => set(value)} />
      ))}
    </View>
  );

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("runData.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("runData.title", "Calculation data")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {(
            [
              ["ledger", tx("runData.tabLedger", "Ledger")],
              ["solids", tx("runData.tabSolids", "Solids")],
              ["deductions", tx("runData.tabDeductions", "Deductions")],
              ["bars", tx("runData.tabBars", "Bar marks")],
            ] as [Tab, string][]
          ).map(([value, label]) => (
            <Action key={value} title={label} secondary={tab !== value} isUrdu={isUrdu} onPress={() => { setRows([]); setNext(null); setTab(value); }} />
          ))}
        </View>

        {tab === "ledger" ? (
          <>
            {versionId ? (
              <View style={[ui.row, isUrdu && ui.rtlRow]}>
                <Action title={tx("runData.thisVersion", "This version")} secondary={ledgerSource !== "version"} isUrdu={isUrdu} onPress={() => setLedgerSource("version")} />
                <Action title={tx("runData.thisRun", "This run")} secondary={ledgerSource !== "run"} isUrdu={isUrdu} onPress={() => setLedgerSource("run")} />
              </View>
            ) : null}
            <Field label={tx("runData.workItem", "Work item code (blank = all)")} value={workItem} onChangeText={setWorkItem} isUrdu={isUrdu} />
            <Action title={tx("runData.apply", "Apply filter")} secondary isUrdu={isUrdu} onPress={() => void reload()} />
          </>
        ) : null}
        {tab === "solids" ? (
          <>
            <Field label={tx("runData.role", "Role (for example WALL, SLAB; blank = all)")} value={role} onChangeText={setRole} isUrdu={isUrdu} />
            <Action title={tx("runData.apply", "Apply filter")} secondary isUrdu={isUrdu} onPress={() => void reload()} />
          </>
        ) : null}
        {tab === "deductions" ? choiceRow(DEDUCTION_TYPES, deductionType, setDeductionType, tx("runData.all", "All")) : null}
        {tab === "bars" ? (
          <>
            {choiceRow(PROVENANCE, provenance, setProvenance, tx("runData.all", "All"))}
            <Field label={tx("runData.barRole", "Role (blank = all)")} value={role} onChangeText={setRole} isUrdu={isUrdu} />
            <Action title={tx("runData.apply", "Apply filter")} secondary isUrdu={isUrdu} onPress={() => void reload()} />
          </>
        ) : null}

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {loading ? <ActivityIndicator color={COLORS.navy} /> : null}
        {!loading && rows.length === 0 && !error ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("runData.none", "No rows.")}</Text>
        ) : null}

        {tab === "solids"
          ? (rows as QuantitySolid[]).map((row) => (
              <Pressable key={row.id} style={ui.boqItem} onPress={() => toggle(row.id)}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${row.role} · ${row.component_type}`}</Text>
                  <Badge label={row.status} tone={row.status === "OK" || row.status === "VALID" ? "good" : "warn"} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[
                    row.gross_volume_m3 != null ? `${formatNumber(row.gross_volume_m3)} m³` : null,
                    row.gross_area_m2 != null ? `${formatNumber(row.gross_area_m2)} m²` : null,
                    row.gross_length_m != null ? `${formatNumber(row.gross_length_m)} m` : null,
                    row.count != null ? `${row.count} ${tx("runData.nos", "nos")}` : null,
                    row.geometry_kind,
                  ].filter(Boolean).join(" · ")}
                </Text>
                {openId === row.id
                  ? row.issues.map((issue, index) => (
                      <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{`${issue.severity ?? ""} ${issue.code ?? ""} ${issue.message ?? ""}`.trim()}</Text>
                    ))
                  : null}
              </Pressable>
            ))
          : null}

        {tab === "ledger"
          ? (rows as LedgerRow[]).map((row) => (
              <Pressable key={row.id} style={ui.boqItem} onPress={() => toggle(row.id)}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${row.work_item_code} · ${formatNumber(row.quantity_net)} ${row.unit}`}</Text>
                  <Badge label={row.source_kind} tone="neutral" />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[row.formula_code, row.material_grade, tx("runData.confidence", "confidence {{value}}", { value: formatNumber(row.confidence, 2) })].filter(Boolean).join(" · ")}
                </Text>
                {row.warnings.map((warning, index) => (
                  <Text key={index} style={[ui.error, isUrdu && ui.rtlText]}>{warning}</Text>
                ))}
                {openId === row.id ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{pretty(row.trace)}</Text> : null}
              </Pressable>
            ))
          : null}

        {tab === "deductions"
          ? (rows as Deduction[]).map((row) => (
              <Pressable key={row.id} style={ui.boqItem} onPress={() => toggle(row.id)}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${row.deduction_type.replaceAll("_", " ")} · ${formatNumber(row.quantity)} ${row.unit}`}</Text>
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{[row.rule_code, row.rule_version, row.explanation].filter(Boolean).join(" · ")}</Text>
                {openId === row.id ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{pretty(row.geometry)}</Text> : null}
              </Pressable>
            ))
          : null}

        {tab === "bars"
          ? (rows as BarMark[]).map((row) => (
              <Pressable key={row.id} style={ui.boqItem} onPress={() => toggle(row.id)}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${row.mark} · ${row.designation ?? `${formatNumber(row.dia_mm, 0)} mm`}`}</Text>
                  <Badge label={row.provenance.replaceAll("_", " ")} tone={row.provenance === "RULE_ESTIMATE" ? "warn" : "good"} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {`${row.role} · ${row.shape_code} · ${row.count} × ${formatNumber(row.cut_len_mm, 0)} mm · ${formatNumber(row.total_kg)} kg · ${row.review_status}`}
                </Text>
                {row.warnings.map((warning, index) => (
                  <Text key={index} style={[ui.error, isUrdu && ui.rtlText]}>{warning}</Text>
                ))}
                {openId === row.id ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {`${tx("runData.pieces", "{{count}} pieces", { count: row.pieces })} · ${formatNumber(row.total_len_m, 1)} m${row.spacing_mm != null ? ` · @${formatNumber(row.spacing_mm, 0)} mm` : ""}${row.grade ? ` · ${row.grade}` : ""}`}
                  </Text>
                ) : null}
              </Pressable>
            ))
          : null}

        {next ? (
          <Action
            title={more ? tx("runData.loading", "Loading…") : tx("runData.loadMore", "Load more")}
            secondary
            disabled={more}
            isUrdu={isUrdu}
            onPress={() => void loadMore()}
          />
        ) : null}
        {rows.length > 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("runData.shown", "{{count}} rows loaded. Tap a row for details.", { count: rows.length })}
          </Text>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}