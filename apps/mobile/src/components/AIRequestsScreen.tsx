import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../api/client";
import { getAIUsageSummary, listAIRequests } from "../api/ai_requests";
import type {
  AIEntityType,
  AIRequestPurpose,
  AIRequestRecord,
  AIUsageSummary,
  AuthUser,
} from "../api/types";
import LanguageSwitcher from "./LanguageSwitcher";

const PAGE_SIZE = 20;

const PURPOSES: Array<AIRequestPurpose | "ALL"> = [
  "ALL",
  "MATERIAL_NORMALIZATION",
  "CAPTION_PARSING",
  "PHOTO_TAGGING",
  "PDF_SCHEDULE_EXTRACTION",
];

const ENTITY_TYPES: Array<AIEntityType | "ALL"> = [
  "ALL",
  "DRAWING_ELEMENT",
  "SITE_PHOTO",
  "WHATSAPP_MESSAGE",
  "DRAWING",
];

const C = {
  background: "#F3EEE4",
  surface: "#FFFEFB",
  surfaceMuted: "#F7F1E7",
  navy: "#080D18",
  text: "#17212F",
  secondary: "#5C5347",
  muted: "#82796C",
  border: "#E5DCCB",
  gold: "#D9A441",
  green: "#26734D",
  greenBg: "#E8F2E9",
  red: "#A33A32",
  redBg: "#F9E9E5",
};

function label(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value: string, locale?: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(locale);
}

export function AIRequestsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = i18n.resolvedLanguage || i18n.language;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [permissionChecked, setPermissionChecked] = useState(false);
  const [canRead, setCanRead] = useState(false);

  const [rows, setRows] = useState<AIRequestRecord[]>([]);
  const [summary, setSummary] = useState<AIUsageSummary | null>(null);
  const [purpose, setPurpose] = useState<AIRequestPurpose | "ALL">("ALL");
  const [entityType, setEntityType] = useState<AIEntityType | "ALL">("ALL");
  const [pageNumber, setPageNumber] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);

  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");

  function purposeLabel(value: AIRequestPurpose | "ALL"): string {
    if (value === "ALL") return t("aiRequests.all");
    return t(`aiRequests.purpose.${value.toLowerCase()}`, {
      defaultValue: label(value),
    });
  }

  function entityTypeLabel(value: AIEntityType | "ALL"): string {
    if (value === "ALL") return t("aiRequests.all");
    return t(`aiRequests.entityType.${value.toLowerCase()}`, {
      defaultValue: label(value),
    });
  }

  async function fetchPage(page: number) {
    const [requestRows, nextRows] = await Promise.all([
      listAIRequests({
        purpose: purpose === "ALL" ? undefined : purpose,
        entity_type: entityType === "ALL" ? undefined : entityType,
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
      listAIRequests({
        purpose: purpose === "ALL" ? undefined : purpose,
        entity_type: entityType === "ALL" ? undefined : entityType,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    ]);

    return {
      rows: requestRows,
      hasNext: nextRows.length > 0,
    };
  }

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      setPageNumber(1);
      setHasNextPage(false);

      try {
        const currentUser = await restoreSession();
        if (!currentUser) {
          const { router } = await import("expo-router");
          router.replace("/");
          return;
        }
        if (!active) return;

        setUser(currentUser);
        const permitted = currentUser.role.permissions.some(
          (permission) => permission.key === "ai_request:read",
        );
        setCanRead(permitted);
        setPermissionChecked(true);

        if (!permitted) {
          setRows([]);
          setSummary(null);
          return;
        }

        const [page, usage] = await Promise.all([
          fetchPage(1),
          getAIUsageSummary(),
        ]);

        if (!active) return;
        setRows(page.rows);
        setSummary(usage);
        setPageNumber(1);
        setHasNextPage(page.hasNext);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : t("aiRequests.loadFailure"),
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [purpose, entityType, attempt, t]);

  async function goToPage(targetPage: number) {
    if (targetPage < 1 || targetPage === pageNumber || loading) return;

    setLoading(true);
    setError("");

    try {
      const page = await fetchPage(targetPage);
      setRows(page.rows);
      setPageNumber(targetPage);
      setHasNextPage(page.hasNext);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("aiRequests.loadFailure"),
      );
    } finally {
      setLoading(false);
    }
  }

  const lastAvailablePage = pageNumber + (hasNextPage ? 1 : 0);
  const firstVisiblePage = Math.max(
    1,
    Math.min(pageNumber - 2, lastAvailablePage - 4),
  );
  const visiblePages = Array.from(
    {
      length: Math.min(5, lastAvailablePage - firstVisiblePage + 1),
    },
    (_, index) => firstVisiblePage + index,
  );

  if (loading || !permissionChecked) {
    return (
      <View style={styles.page}>
        <View style={[styles.heading, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("aiRequests.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>

        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("aiRequests.loading")}
          </Text>
        </View>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <View style={[styles.heading, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("aiRequests.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {t("aiRequests.accessDenied")}
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
    >
      <View style={[styles.heading, isUrdu && styles.rtlRow]}>
        <View style={styles.headerContent}>
          <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
            {t("aiRequests.eyebrow")}
          </Text>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("aiRequests.pageTitle")}
          </Text>
        </View>

        <View style={[styles.headerActions, isUrdu && styles.rtlRow]}>
          <Pressable
            onPress={() => setAttempt((value) => value + 1)}
            accessibilityRole="button"
          >
            <Text style={styles.link}>{t("aiRequests.refresh")}</Text>
          </Pressable>
          <LanguageSwitcher />
        </View>
      </View>

      {error ? (
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error}
        </Text>
      ) : null}

      {summary ? (
        <View style={styles.card}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("aiRequests.usageSummary")}
          </Text>
          <InfoRow
            label={t("aiRequests.totalRequests")}
            value={String(summary.total_requests)}
            isUrdu={isUrdu}
          />
          <InfoRow
            label={t("aiRequests.succeeded")}
            value={String(summary.succeeded)}
            isUrdu={isUrdu}
          />
          <InfoRow
            label={t("aiRequests.failed")}
            value={String(summary.failed)}
            isUrdu={isUrdu}
          />
          <InfoRow
            label={t("aiRequests.averageLatency")}
            value={
              summary.average_latency_ms == null
                ? t("aiRequests.notAvailable")
                : t("aiRequests.milliseconds", {
                    value: Math.round(summary.average_latency_ms),
                  })
            }
            isUrdu={isUrdu}
          />
        </View>
      ) : null}

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
          {t("aiRequests.purposeLabel")}
        </Text>
        <ChoiceRow
          values={PURPOSES}
          selected={purpose}
          onSelect={setPurpose}
          getLabel={purposeLabel}
          isUrdu={isUrdu}
        />

        <Text
          style={[
            styles.sectionTitle,
            styles.filterHeading,
            isUrdu && styles.rtlText,
          ]}
        >
          {t("aiRequests.entityTypeLabel")}
        </Text>
        <ChoiceRow
          values={ENTITY_TYPES}
          selected={entityType}
          onSelect={setEntityType}
          getLabel={entityTypeLabel}
          isUrdu={isUrdu}
        />
      </View>

      <View style={[styles.heading, isUrdu && styles.rtlRow]}>
        <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
          {t("aiRequests.requestHistory")}
        </Text>
        <Text style={styles.muted}>
          {t("aiRequests.loadedCount", { count: rows.length })}
        </Text>
      </View>

      {rows.length === 0 ? (
        <View style={styles.card}>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("aiRequests.noMatches")}
          </Text>
        </View>
      ) : (
        rows.map((request) => {
          const responseStatus = request.response?.status;
          const statusLabel = responseStatus
            ? t(`aiRequests.status.${responseStatus.toLowerCase()}`, {
                defaultValue: label(responseStatus),
              })
            : t("aiRequests.status.pending");

          return (
            <View key={request.id} style={styles.card}>
              <View style={[styles.heading, isUrdu && styles.rtlRow]}>
                <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
                  {purposeLabel(request.purpose)}
                </Text>
                <Text
                  style={[
                    styles.badge,
                    responseStatus === "SUCCEEDED" && styles.succeededBadge,
                    responseStatus === "FAILED" && styles.failedBadge,
                  ]}
                >
                  {statusLabel}
                </Text>
              </View>

              <InfoRow
                label={t("aiRequests.provider")}
                value={label(request.provider)}
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("aiRequests.model")}
                value={request.model}
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("aiRequests.entity")}
                value={
                  request.entity_type
                    ? `${entityTypeLabel(request.entity_type)}${
                        request.entity_id ? ` · ${request.entity_id}` : ""
                      }`
                    : t("aiRequests.notLinked")
                }
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("aiRequests.requested")}
                value={formatDate(request.created_at, locale)}
                isUrdu={isUrdu}
              />

              {request.response?.latency_ms != null ? (
                <InfoRow
                  label={t("aiRequests.latency")}
                  value={t("aiRequests.milliseconds", {
                    value: request.response.latency_ms,
                  })}
                  isUrdu={isUrdu}
                />
              ) : null}

              {request.response?.error_message ? (
                <Text style={styles.error}>
                  {request.response.error_message}
                </Text>
              ) : null}

              {request.response?.parsed_output ? (
                <View style={styles.output}>
                  <Text
                    style={[
                      styles.outputLabel,
                      isUrdu && styles.rtlText,
                    ]}
                  >
                    {t("aiRequests.parsedOutput")}
                  </Text>
                  <Text selectable style={styles.outputText}>
                    {JSON.stringify(request.response.parsed_output, null, 2)}
                  </Text>
                </View>
              ) : null}
            </View>
          );
        })
      )}

      {rows.length > 0 ? (
        <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
          <Pressable
            style={[
              styles.pageNavButton,
              pageNumber === 1 && styles.disabled,
            ]}
            disabled={pageNumber === 1 || loading}
            onPress={() => void goToPage(pageNumber - 1)}
            accessibilityRole="button"
          >
            <Text style={styles.pageNavText}>
              {t("aiRequests.previousPage")}
            </Text>
          </Pressable>

          <View style={[styles.pageNumbers, isUrdu && styles.rtlRow]}>
            {visiblePages.map((page) => (
              <Pressable
                key={page}
                style={[
                  styles.pageNumber,
                  page === pageNumber && styles.pageNumberSelected,
                ]}
                disabled={loading || page === pageNumber}
                onPress={() => void goToPage(page)}
                accessibilityRole="button"
                accessibilityState={{ selected: page === pageNumber }}
              >
                <Text
                  style={[
                    styles.pageNumberText,
                    page === pageNumber && styles.pageNumberTextSelected,
                  ]}
                >
                  {page}
                </Text>
              </Pressable>
            ))}
          </View>

          <Pressable
            style={[
              styles.pageNavButton,
              !hasNextPage && styles.disabled,
            ]}
            disabled={!hasNextPage || loading}
            onPress={() => void goToPage(pageNumber + 1)}
            accessibilityRole="button"
          >
            <Text style={styles.pageNavText}>{t("aiRequests.nextPage")}</Text>
          </Pressable>
        </View>
      ) : null}
    </ScrollView>
  );
}

function ChoiceRow<T extends string>({
  values,
  selected,
  onSelect,
  getLabel,
  isUrdu,
}: {
  values: T[];
  selected: T;
  onSelect: (value: T) => void;
  getLabel: (value: T) => string;
  isUrdu: boolean;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <View style={[styles.choices, isUrdu && styles.rtlRow]}>
        {values.map((value) => (
          <Pressable
            key={value}
            onPress={() => onSelect(value)}
            style={[
              styles.choice,
              selected === value && styles.choiceSelected,
            ]}
          >
            <Text
              style={[
                styles.choiceText,
                selected === value && styles.choiceTextSelected,
              ]}
            >
              {getLabel(value)}
            </Text>
          </Pressable>
        ))}
      </View>
    </ScrollView>
  );
}

function InfoRow({
  label: title,
  value,
  isUrdu,
}: {
  label: string;
  value: string;
  isUrdu: boolean;
}) {
  return (
    <View style={[styles.infoRow, isUrdu && styles.rtlRow]}>
      <Text style={[styles.muted, isUrdu && styles.rtlText]}>{title}</Text>
      <Text style={[styles.infoValue, isUrdu && styles.rtlText]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: C.background },
  heading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 12 },
  headerContent: { flex: 1 },
  headerActions: { flexDirection: "row", alignItems: "center", gap: 10 },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 27, fontWeight: "800", marginTop: 5, letterSpacing: -0.4 },
  sectionTitle: { color: C.text, fontSize: 17, fontWeight: "800" },
  filterHeading: { marginTop: 18, marginBottom: 8 },
  card: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, borderRadius: 15, padding: 16, marginBottom: 12 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 9 },
  infoValue: { flex: 1, color: C.text, textAlign: "right", fontWeight: "700", fontSize: 13 },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19 },
  link: { color: C.navy, fontSize: 13, fontWeight: "800" },
  error: { color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19, marginTop: 8, marginBottom: 12 },
  badge: { color: C.secondary, backgroundColor: C.surfaceMuted, paddingHorizontal: 10, paddingVertical: 6, overflow: "hidden", borderRadius: 99, fontSize: 11, fontWeight: "800" },
  succeededBadge: { color: C.green, backgroundColor: C.greenBg },
  failedBadge: { color: C.red, backgroundColor: C.redBg },
  choices: { flexDirection: "row", gap: 8, paddingVertical: 5 },
  choice: { minHeight: 38, justifyContent: "center", borderWidth: 1, borderColor: C.border, borderRadius: 99, backgroundColor: C.surface, paddingHorizontal: 12, paddingVertical: 8 },
  choiceSelected: { backgroundColor: C.navy, borderColor: C.navy },
  choiceText: { color: C.secondary, fontSize: 12, fontWeight: "700" },
  choiceTextSelected: { color: C.surface },
  output: { backgroundColor: C.surfaceMuted, borderWidth: 1, borderColor: C.border, borderRadius: 10, padding: 12, marginTop: 12 },
  outputLabel: { fontWeight: "800", color: C.text, marginBottom: 7, fontSize: 13 },
  outputText: { color: C.secondary, fontSize: 12, lineHeight: 18 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 4, padding: 10, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13 },
  pageNavButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: C.surfaceMuted },
  pageNavText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pageNumbers: { flexDirection: "row", alignItems: "center", gap: 5 },
  pageNumber: { minWidth: 36, height: 36, alignItems: "center", justifyContent: "center", borderRadius: 9, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  pageNumberSelected: { backgroundColor: C.navy, borderColor: C.navy },
  pageNumberText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  pageNumberTextSelected: { color: C.surface },
  disabled: { opacity: 0.45 },
});