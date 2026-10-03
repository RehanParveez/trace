import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  Stack,
  router,
  useFocusEffect,
  useLocalSearchParams,
} from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../../api/client";
import { getProject } from "../../../../../api/projects";
import {
  createAgreement,
  getProjectSubcontractCost,
  listProjectAgreements,
  listSubcontractors,
} from "../../../../../api/subcontractors";
import type {
  AuthUser,
  Project,
  ProjectSubcontractCost,
  SubcontractAgreementCreatePayload,
  SubcontractAgreementDetail,
  Subcontractor,
} from "../../../../../api/types";
import LanguageSwitcher from "../../../../../components/LanguageSwitcher";

const PAGE_SIZE = 20;

type ItemForm = {
  description: string;
  unit: string;
  quantity: string;
  rate: string;
};

const emptyItem = (): ItemForm => ({
  description: "",
  unit: "",
  quantity: "",
  rate: "",
});

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

export default function ProjectSubcontractorsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [agreements, setAgreements] = useState<SubcontractAgreementDetail[]>([]);
  const [subcontractors, setSubcontractors] = useState<Subcontractor[]>([]);
  const [cost, setCost] = useState<ProjectSubcontractCost | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formVisible, setFormVisible] = useState(false);
  const [agreementPage, setAgreementPage] = useState(1);
  const [subcontractorPage, setSubcontractorPage] = useState(1);

  const [subcontractorId, setSubcontractorId] = useState("");
  const [scope, setScope] = useState("");
  const [startDate, setStartDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [retention, setRetention] = useState("10");
  const [retentionCap, setRetentionCap] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<ItemForm[]>([emptyItem()]);

  const permissions = user?.role.permissions.map((permission) => permission.key) ?? [];
  const canRead = permissions.includes("subcontractor:read");
  const canManage = permissions.includes("subcontractor:manage");

  const activeSubcontractors = subcontractors.filter((item) => item.is_active);
  const agreementPages = pageCount(agreements.length);
  const subcontractorPages = pageCount(activeSubcontractors.length);
  const visibleAgreements = paginate(agreements, agreementPage);
  const visibleSubcontractors = paginate(activeSubcontractors, subcontractorPage);

  const load = useCallback(
    async (refresh = false) => {
      try {
        if (refresh) setRefreshing(true);
        else setLoading(true);
        setError(null);

        if (!projectId) {
          throw new Error(t("projectSubcontractors.projectIdMissing"));
        }

        const currentUser = await restoreSession();
        if (!currentUser) {
          router.replace("/");
          return;
        }

        setUser(currentUser);
        if (
          !currentUser.role.permissions.some(
            (permission) => permission.key === "subcontractor:read",
          )
        ) {
          setProject(null);
          setAgreements([]);
          setSubcontractors([]);
          setCost(null);
          setAgreementPage(1);
          setSubcontractorPage(1);
          return;
        }

        const [projectResult, agreementRows, projectCost, directory] =
          await Promise.all([
            getProject(projectId),
            listProjectAgreements(projectId),
            getProjectSubcontractCost(projectId),
            listSubcontractors(),
          ]);

        setProject(projectResult);
        setAgreements(agreementRows);
        setCost(projectCost);
        setSubcontractors(directory);
        setAgreementPage(1);
        setSubcontractorPage(1);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("projectSubcontractors.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, t],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function resetForm() {
    setSubcontractorId("");
    setScope("");
    setStartDate(new Date().toISOString().slice(0, 10));
    setRetention("10");
    setRetentionCap("");
    setNotes("");
    setItems([emptyItem()]);
    setSubcontractorPage(1);
  }

  async function saveAgreement() {
    if (!projectId || !subcontractorId || !scope.trim()) {
      setError(t("projectSubcontractors.validation.subcontractorAndScope"));
      return;
    }

    if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
      setError(t("projectSubcontractors.validation.startDate"));
      return;
    }

    if (
      !Number.isFinite(Number(retention)) ||
      Number(retention) < 0 ||
      Number(retention) > 100
    ) {
      setError(t("projectSubcontractors.validation.retention"));
      return;
    }

    if (
      retentionCap.trim() &&
      (!Number.isFinite(Number(retentionCap)) ||
        Number(retentionCap) < 0 ||
        Number(retentionCap) > 100)
    ) {
      setError(t("projectSubcontractors.validation.retentionCap"));
      return;
    }

    if (
      items.length === 0 ||
      items.some(
        (item) =>
          !item.description.trim() ||
          !item.unit.trim() ||
          !Number.isFinite(Number(item.quantity)) ||
          Number(item.quantity) <= 0 ||
          !Number.isFinite(Number(item.rate)) ||
          Number(item.rate) < 0,
      )
    ) {
      setError(t("projectSubcontractors.validation.items"));
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const payload: SubcontractAgreementCreatePayload = {
        project_id: projectId,
        subcontractor_id: subcontractorId,
        scope_description: scope.trim(),
        start_date: startDate,
        default_retention_percentage: Number(retention),
        default_retention_cap_percentage: retentionCap.trim()
          ? Number(retentionCap)
          : null,
        notes: notes.trim() || null,
        items: items.map((item) => ({
          description: item.description.trim(),
          unit: item.unit.trim(),
          quantity: Number(item.quantity),
          rate: Number(item.rate),
        })),
      };

      await createAgreement(payload);
      setFormVisible(false);
      resetForm();
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("projectSubcontractors.createFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: t("projectSubcontractors.title") }} />
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("projectSubcontractors.loading")}
        </Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen
        options={{
          title: project?.name ?? t("projectSubcontractors.title"),
        }}
      />

      {!canRead ? (
        <View style={styles.center}>
          <View style={styles.switcherRow}>
            <LanguageSwitcher />
          </View>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("projectSubcontractors.accessUnavailable")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectSubcontractors.accessDenied")}
          </Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.page}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => void load(true)}
              tintColor={COLORS.navy}
            />
          }
        >
          <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
            <View style={styles.headerText}>
              <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
                {project?.name ?? t("projectSubcontractors.project")}
              </Text>
              <Text style={[styles.title, isUrdu && styles.rtlText]}>
                {t("projectSubcontractors.title")}
              </Text>
            </View>
            <LanguageSwitcher />
          </View>

          <View style={styles.card}>
            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("projectSubcontractors.totalBilled")}
            </Text>
            <Text style={[styles.amount, isUrdu && styles.rtlText]}>
              {cost
                ? `${cost.currency} ${Number(cost.total_billed).toLocaleString()}`
                : t("projectSubcontractors.notAvailable")}
            </Text>
          </View>

          {canManage ? (
            <Button
              label={t("projectSubcontractors.newAgreement")}
              primary
              isUrdu={isUrdu}
              onPress={() => {
                resetForm();
                setError(null);
                setFormVisible(true);
              }}
            />
          ) : null}

          {error ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
          ) : null}

          {agreements.length === 0 ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("projectSubcontractors.noAgreements")}
            </Text>
          ) : (
            <>
              {visibleAgreements.map((agreement) => {
                const contractor = subcontractors.find(
                  (item) => item.id === agreement.subcontractor_id,
                );

                return (
                  <Pressable
                    key={agreement.id}
                    style={styles.card}
                    accessibilityRole="button"
                    onPress={() =>
                      router.push({
                        pathname:
                          "/projects/[projectId]/subcontractors/[agreementId]",
                        params: {
                          projectId: projectId!,
                          agreementId: agreement.id,
                        },
                      })
                    }
                  >
                    <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                      {contractor?.name ??
                        t("projectSubcontractors.subcontractor")}
                    </Text>
                    <Text style={[styles.body, isUrdu && styles.rtlText]}>
                      {agreement.scope_description}
                    </Text>
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {t("projectSubcontractors.contractValue", {
                        currency: cost?.currency ?? "",
                        value: Number(agreement.contract_value).toLocaleString(),
                      })}
                    </Text>
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {t("projectSubcontractors.agreementDateStatus", {
                        date: agreement.start_date,
                        status: agreement.status.replaceAll("_", " "),
                      })}
                    </Text>
                    <Text style={[styles.link, isUrdu && styles.rtlText]}>
                      {t("projectSubcontractors.openAgreement")}
                    </Text>
                  </Pressable>
                );
              })}

              <Pagination
                page={agreementPage}
                pages={agreementPages}
                isUrdu={isUrdu}
                onPrevious={() =>
                  setAgreementPage((current) => Math.max(1, current - 1))
                }
                onNext={() =>
                  setAgreementPage((current) =>
                    Math.min(agreementPages, current + 1),
                  )
                }
              />
            </>
          )}
        </ScrollView>
      )}

      <Modal
        visible={formVisible}
        animationType="slide"
        onRequestClose={() => setFormVisible(false)}
      >
        <ScrollView
          contentContainerStyle={styles.page}
          keyboardShouldPersistTaps="handled"
        >
          <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
            <Text style={[styles.title, styles.headerText, isUrdu && styles.rtlText]}>
              {t("projectSubcontractors.newAgreementTitle")}
            </Text>
            <LanguageSwitcher />
          </View>

          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("projectSubcontractors.selectSubcontractor")}
          </Text>

          {visibleSubcontractors.map((item) => (
            <Pressable
              key={item.id}
              style={[
                styles.selectRow,
                subcontractorId === item.id && styles.selected,
                isUrdu && styles.rtlRow,
              ]}
              onPress={() => setSubcontractorId(item.id)}
              accessibilityRole="radio"
              accessibilityState={{ selected: subcontractorId === item.id }}
            >
              <Text style={[styles.body, isUrdu && styles.rtlText]}>
                {item.name} · {item.trade_specialization}
              </Text>
            </Pressable>
          ))}

          {activeSubcontractors.length === 0 ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>
              {t("projectSubcontractors.noActiveSubcontractors")}
            </Text>
          ) : (
            <Pagination
              page={subcontractorPage}
              pages={subcontractorPages}
              isUrdu={isUrdu}
              onPrevious={() =>
                setSubcontractorPage((current) => Math.max(1, current - 1))
              }
              onNext={() =>
                setSubcontractorPage((current) =>
                  Math.min(subcontractorPages, current + 1),
                )
              }
            />
          )}

          <Field
            label={t("projectSubcontractors.scope")}
            value={scope}
            onChangeText={setScope}
            multiline
            isUrdu={isUrdu}
          />
          <Field
            label={t("projectSubcontractors.startDate")}
            value={startDate}
            onChangeText={setStartDate}
            isUrdu={isUrdu}
          />
          <Field
            label={t("projectSubcontractors.defaultRetention")}
            value={retention}
            onChangeText={setRetention}
            keyboardType="decimal-pad"
            isUrdu={isUrdu}
          />
          <Field
            label={t("projectSubcontractors.retentionCapOptional")}
            value={retentionCap}
            onChangeText={setRetentionCap}
            keyboardType="decimal-pad"
            isUrdu={isUrdu}
          />

          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("projectSubcontractors.contractItems")}
          </Text>

          {items.map((item, index) => (
            <View key={index} style={styles.itemCard}>
              <Field
                label={t("projectSubcontractors.description")}
                value={item.description}
                onChangeText={(value) =>
                  setItems((old) =>
                    old.map((row, itemIndex) =>
                      itemIndex === index ? { ...row, description: value } : row,
                    ),
                  )
                }
                isUrdu={isUrdu}
              />
              <Field
                label={t("projectSubcontractors.unit")}
                value={item.unit}
                onChangeText={(value) =>
                  setItems((old) =>
                    old.map((row, itemIndex) =>
                      itemIndex === index ? { ...row, unit: value } : row,
                    ),
                  )
                }
                isUrdu={isUrdu}
              />
              <Field
                label={t("projectSubcontractors.quantity")}
                value={item.quantity}
                onChangeText={(value) =>
                  setItems((old) =>
                    old.map((row, itemIndex) =>
                      itemIndex === index ? { ...row, quantity: value } : row,
                    ),
                  )
                }
                keyboardType="decimal-pad"
                isUrdu={isUrdu}
              />
              <Field
                label={t("projectSubcontractors.rate")}
                value={item.rate}
                onChangeText={(value) =>
                  setItems((old) =>
                    old.map((row, itemIndex) =>
                      itemIndex === index ? { ...row, rate: value } : row,
                    ),
                  )
                }
                keyboardType="decimal-pad"
                isUrdu={isUrdu}
              />

              {items.length > 1 ? (
                <Button
                  label={t("projectSubcontractors.removeItem")}
                  isUrdu={isUrdu}
                  onPress={() =>
                    setItems((old) =>
                      old.filter((_, itemIndex) => itemIndex !== index),
                    )
                  }
                />
              ) : null}
            </View>
          ))}

          <Button
            label={t("projectSubcontractors.addItem")}
            isUrdu={isUrdu}
            onPress={() => setItems((old) => [...old, emptyItem()])}
          />
          <Field
            label={t("projectSubcontractors.notesOptional")}
            value={notes}
            onChangeText={setNotes}
            multiline
            isUrdu={isUrdu}
          />

          {error ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
          ) : null}

          <Button
            label={
              saving
                ? t("projectSubcontractors.creating")
                : t("projectSubcontractors.createAgreement")
            }
            primary
            disabled={saving}
            isUrdu={isUrdu}
            onPress={() => void saveAgreement()}
          />
          <Button
            label={t("projectSubcontractors.cancel")}
            disabled={saving}
            isUrdu={isUrdu}
            onPress={() => setFormVisible(false)}
          />
        </ScrollView>
      </Modal>
    </>
  );
}

function Pagination(props: {
  page: number;
  pages: number;
  isUrdu: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const { t } = useTranslation();

  return (
    <View style={[styles.pagination, props.isUrdu && styles.rtlRow]}>
      <Button
        label={t("projectSubcontractors.previous")}
        disabled={props.page <= 1}
        isUrdu={props.isUrdu}
        onPress={props.onPrevious}
      />
      <Text style={[styles.pageText, props.isUrdu && styles.rtlText]}>
        {t("projectSubcontractors.pageOf", {
          page: props.page,
          pages: props.pages,
        })}
      </Text>
      <Button
        label={t("projectSubcontractors.next")}
        disabled={props.page >= props.pages}
        isUrdu={props.isUrdu}
        onPress={props.onNext}
      />
    </View>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  multiline?: boolean;
  isUrdu: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={[styles.label, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <TextInput
        style={[
          styles.input,
          props.multiline && styles.multiline,
          props.isUrdu && styles.rtlText,
        ]}
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType={props.keyboardType ?? "default"}
        multiline={props.multiline}
        textAlign={props.isUrdu ? "right" : "left"}
      />
    </View>
  );
}

function Button(props: {
  label: string;
  onPress: () => void;
  primary?: boolean;
  disabled?: boolean;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={props.disabled}
      onPress={props.onPress}
      style={[
        styles.button,
        props.primary && styles.primary,
        props.disabled && styles.disabled,
      ]}
    >
      <Text
        style={[
          styles.buttonText,
          props.primary && styles.primaryText,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.label}
      </Text>
    </Pressable>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#F7F3EC",
  navy: "#080D18",
  text: "#171C26",
  secondary: "#5C5347",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
  red: "#A63A32",
  redBackground: "#FBEAE7",
  green: "#287456",
};

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 36, gap: 12, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 12, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 6 },
  rtlRow: { flexDirection: "row-reverse" },
  headerText: { flex: 1 },
  eyebrow: { color: COLORS.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.2, textTransform: "uppercase" },
  title: { color: COLORS.text, fontSize: 25, fontWeight: "800", marginTop: 4 },
  sectionTitle: { color: COLORS.text, fontSize: 17, fontWeight: "800" },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700" },
  body: { color: COLORS.text, fontSize: 14, lineHeight: 21 },
  muted: { color: COLORS.muted, fontSize: 13, lineHeight: 19 },
  amount: { color: COLORS.navy, fontSize: 22, fontWeight: "800", marginTop: 5 },
  card: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 16, gap: 9 },
  cardTitle: { color: COLORS.text, fontSize: 16, fontWeight: "800" },
  link: { color: COLORS.navy, fontSize: 13, fontWeight: "800", marginTop: 2 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19 },
  field: { gap: 6 },
  input: { minHeight: 46, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 12, paddingVertical: 10, color: COLORS.text, fontSize: 14 },
  multiline: { minHeight: 78, textAlignVertical: "top" },
  itemCard: { backgroundColor: COLORS.surfaceMuted, borderWidth: 1, borderColor: COLORS.border, borderRadius: 12, padding: 13, gap: 10 },
  selectRow: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, padding: 13 },
  selected: { borderColor: COLORS.gold, borderWidth: 2 },
  button: { minHeight: 44, borderWidth: 1, borderColor: COLORS.border, backgroundColor: COLORS.surface, borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 10 },
  buttonText: { color: COLORS.navy, fontSize: 13, fontWeight: "800", textAlign: "center" },
  primary: { backgroundColor: COLORS.navy, borderColor: COLORS.navy },
  primaryText: { color: COLORS.surface },
  disabled: { opacity: 0.5 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});