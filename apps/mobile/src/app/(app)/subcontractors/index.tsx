import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../api/client";
import {
  createSubcontractor,
  listSubcontractors,
  updateSubcontractor,
} from "../../../api/subcontractors";
import type {
  AuthUser,
  Subcontractor,
  SubcontractorCreatePayload,
  SubcontractorUpdatePayload,
} from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

const PAGE_SIZE = 20;

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

type Form = {
  name: string;
  trade_specialization: string;
  contact_name: string;
  contact_phone: string;
  ntn_or_cnic: string;
  is_active_taxpayer: boolean;
  is_active: boolean;
  notes: string;
};

const emptyForm: Form = {
  name: "",
  trade_specialization: "",
  contact_name: "",
  contact_phone: "",
  ntn_or_cnic: "",
  is_active_taxpayer: false,
  is_active: true,
  notes: "",
};

export default function SubcontractorsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [user, setUser] = useState<AuthUser | null>(null);
  const [rows, setRows] = useState<Subcontractor[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formVisible, setFormVisible] = useState(false);
  const [editing, setEditing] = useState<Subcontractor | null>(null);
  const [form, setForm] = useState<Form>(emptyForm);
  const [pageNumber, setPageNumber] = useState(1);

  const permissions =
    user?.role.permissions.map((permission) => permission.key) ?? [];
  const canRead = permissions.includes("subcontractor:read");
  const canManage = permissions.includes("subcontractor:manage");

  const load = useCallback(
    async (refresh = false) => {
      try {
        if (refresh) setRefreshing(true);
        else setLoading(true);
        setError(null);
        setPageNumber(1);

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
          setRows([]);
          return;
        }

        setRows(await listSubcontractors());
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("subcontractors.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [t],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError(null);
    setFormVisible(true);
  }

  function openEdit(row: Subcontractor) {
    setEditing(row);
    setForm({
      name: row.name,
      trade_specialization: row.trade_specialization,
      contact_name: row.contact_name ?? "",
      contact_phone: row.contact_phone ?? "",
      ntn_or_cnic: row.ntn_or_cnic ?? "",
      is_active_taxpayer: row.is_active_taxpayer,
      is_active: row.is_active,
      notes: row.notes ?? "",
    });
    setError(null);
    setFormVisible(true);
  }

  async function save() {
    if (!form.name.trim() || !form.trade_specialization.trim()) {
      setError(t("subcontractors.requiredFields"));
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (editing) {
        const payload: SubcontractorUpdatePayload = {
          name: form.name.trim(),
          trade_specialization: form.trade_specialization.trim(),
          contact_name: form.contact_name.trim() || null,
          contact_phone: form.contact_phone.trim() || null,
          ntn_or_cnic: form.ntn_or_cnic.trim() || null,
          is_active_taxpayer: form.is_active_taxpayer,
          is_active: form.is_active,
          notes: form.notes.trim() || null,
        };
        await updateSubcontractor(editing.id, payload);
      } else {
        const payload: SubcontractorCreatePayload = {
          name: form.name.trim(),
          trade_specialization: form.trade_specialization.trim(),
          contact_name: form.contact_name.trim() || null,
          contact_phone: form.contact_phone.trim() || null,
          ntn_or_cnic: form.ntn_or_cnic.trim() || null,
          is_active_taxpayer: form.is_active_taxpayer,
          notes: form.notes.trim() || null,
        };
        await createSubcontractor(payload);
      }

      setFormVisible(false);
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("subcontractors.saveFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  const totalPages = Math.ceil(rows.length / PAGE_SIZE);
  const startIndex = (pageNumber - 1) * PAGE_SIZE;
  const visibleRows = rows.slice(startIndex, startIndex + PAGE_SIZE);
  const visiblePages = Array.from(
    { length: totalPages },
    (_, index) => index + 1,
  ).filter((page) => Math.abs(page - pageNumber) <= 2);

  if (loading) {
    return (
      <View style={styles.page}>
        <Stack.Screen options={{ title: t("subcontractors.pageTitle") }} />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("subcontractors.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("subcontractors.loading")}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: t("subcontractors.pageTitle") }} />

      {!canRead ? (
        <View style={styles.page}>
          <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("subcontractors.pageTitle")}
            </Text>
            <LanguageSwitcher />
          </View>
          <View style={styles.messageCard}>
            <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
              {t("subcontractors.accessUnavailable")}
            </Text>
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("subcontractors.accessDenied")}
            </Text>
          </View>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={[
            styles.page,
            isUrdu && styles.rtlPage,
          ]}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => void load(true)}
              tintColor={C.navy}
              colors={[C.navy]}
            />
          }
        >
          <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
            <View style={styles.headerContent}>
              <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
                {t("subcontractors.eyebrow")}
              </Text>
              <Text style={[styles.title, isUrdu && styles.rtlText]}>
                {t("subcontractors.directoryTitle")}
              </Text>
            </View>
            <LanguageSwitcher />
          </View>

          <Text style={[styles.subtitle, isUrdu && styles.rtlText]}>
            {t("subcontractors.subtitle")}
          </Text>

          {canManage ? (
            <Button
              label={t("subcontractors.addButton")}
              onPress={openCreate}
              primary
            />
          ) : null}

          {error ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>
              {error}
            </Text>
          ) : null}

          {rows.length === 0 ? (
            <Text style={[styles.empty, isUrdu && styles.rtlText]}>
              {t("subcontractors.empty")}
            </Text>
          ) : (
            <>
              {visibleRows.map((row) => (
                <View key={row.id} style={styles.card}>
                  <View style={[styles.rowBetween, isUrdu && styles.rtlRow]}>
                    <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                      {row.name}
                    </Text>
                    <Text
                      style={[
                        styles.badge,
                        row.is_active ? styles.active : styles.inactive,
                      ]}
                    >
                      {row.is_active
                        ? t("subcontractors.active")
                        : t("subcontractors.inactive")}
                    </Text>
                  </View>

                  <Text style={[styles.body, isUrdu && styles.rtlText]}>
                    {row.trade_specialization}
                  </Text>
                  {row.contact_name ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {row.contact_name}
                    </Text>
                  ) : null}
                  {row.contact_phone ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {row.contact_phone}
                    </Text>
                  ) : null}
                  {row.ntn_or_cnic ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {t("subcontractors.ntnCnic", {
                        value: row.ntn_or_cnic,
                      })}
                    </Text>
                  ) : null}
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("subcontractors.taxpayerStatus", {
                      status: row.is_active_taxpayer
                        ? t("subcontractors.taxpayerActive")
                        : t("subcontractors.taxpayerNotMarkedActive"),
                    })}
                  </Text>

                  {canManage ? (
                    <Button
                      label={t("subcontractors.edit")}
                      onPress={() => openEdit(row)}
                    />
                  ) : null}
                </View>
              ))}

              {totalPages > 1 ? (
                <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
                  <Pressable
                    style={[
                      styles.pageNavButton,
                      pageNumber === 1 && styles.disabled,
                    ]}
                    disabled={pageNumber === 1}
                    onPress={() =>
                      setPageNumber((current) => Math.max(1, current - 1))
                    }
                    accessibilityRole="button"
                  >
                    <Text style={styles.pageNavText}>
                      {t("subcontractors.previousPage")}
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
                        disabled={page === pageNumber}
                        onPress={() => setPageNumber(page)}
                        accessibilityRole="button"
                        accessibilityState={{
                          selected: page === pageNumber,
                        }}
                      >
                        <Text
                          style={[
                            styles.pageNumberText,
                            page === pageNumber &&
                              styles.pageNumberTextSelected,
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
                      pageNumber === totalPages && styles.disabled,
                    ]}
                    disabled={pageNumber === totalPages}
                    onPress={() =>
                      setPageNumber((current) =>
                        Math.min(totalPages, current + 1),
                      )
                    }
                    accessibilityRole="button"
                  >
                    <Text style={styles.pageNavText}>
                      {t("subcontractors.nextPage")}
                    </Text>
                  </Pressable>
                </View>
              ) : null}
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
          contentContainerStyle={[
            styles.page,
            isUrdu && styles.rtlPage,
          ]}
        >
          <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {editing
                ? t("subcontractors.editTitle")
                : t("subcontractors.addTitle")}
            </Text>
            <LanguageSwitcher />
          </View>

          <Field
            label={t("subcontractors.name")}
            value={form.name}
            onChangeText={(value) => setForm({ ...form, name: value })}
            isUrdu={isUrdu}
          />
          <Field
            label={t("subcontractors.tradeSpecialization")}
            value={form.trade_specialization}
            onChangeText={(value) =>
              setForm({ ...form, trade_specialization: value })
            }
            isUrdu={isUrdu}
          />
          <Field
            label={t("subcontractors.contactName")}
            value={form.contact_name}
            onChangeText={(value) =>
              setForm({ ...form, contact_name: value })
            }
            isUrdu={isUrdu}
          />
          <Field
            label={t("subcontractors.contactPhone")}
            value={form.contact_phone}
            onChangeText={(value) =>
              setForm({ ...form, contact_phone: value })
            }
            keyboardType="phone-pad"
            isUrdu={isUrdu}
          />
          <Field
            label={t("subcontractors.ntnOrCnic")}
            value={form.ntn_or_cnic}
            onChangeText={(value) =>
              setForm({ ...form, ntn_or_cnic: value })
            }
            isUrdu={isUrdu}
          />
          <Toggle
            label={t("subcontractors.activeTaxpayer")}
            value={form.is_active_taxpayer}
            onValueChange={(value) =>
              setForm({ ...form, is_active_taxpayer: value })
            }
            isUrdu={isUrdu}
          />
          {editing ? (
            <Toggle
              label={t("subcontractors.activeSubcontractor")}
              value={form.is_active}
              onValueChange={(value) =>
                setForm({ ...form, is_active: value })
              }
              isUrdu={isUrdu}
            />
          ) : null}
          <Field
            label={t("subcontractors.notes")}
            value={form.notes}
            onChangeText={(value) => setForm({ ...form, notes: value })}
            multiline
            isUrdu={isUrdu}
          />

          {error ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>
              {error}
            </Text>
          ) : null}

          <Button
            label={
              saving
                ? t("subcontractors.saving")
                : t("subcontractors.save")
            }
            onPress={() => void save()}
            primary
            disabled={saving}
          />
          <Button
            label={t("subcontractors.cancel")}
            onPress={() => setFormVisible(false)}
            disabled={saving}
          />
        </ScrollView>
      </Modal>
    </>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "phone-pad" | "numeric" | "decimal-pad";
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
        placeholderTextColor={C.muted}
      />
    </View>
  );
}

function Toggle(props: {
  label: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
  isUrdu: boolean;
}) {
  return (
    <View style={[styles.rowBetween, props.isUrdu && styles.rtlRow]}>
      <Text style={[styles.body, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <Switch
        value={props.value}
        onValueChange={props.onValueChange}
        trackColor={{ false: C.border, true: C.gold }}
        thumbColor={props.value ? C.navy : C.surface}
      />
    </View>
  );
}

function Button(props: {
  label: string;
  onPress: () => void;
  primary?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={props.disabled}
      onPress={props.onPress}
      style={[
        styles.button,
        props.primary && styles.primaryButton,
        props.disabled && styles.disabled,
      ]}
    >
      <Text
        style={[
          styles.buttonText,
          props.primary && styles.primaryButtonText,
        ]}
      >
        {props.label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    backgroundColor: C.background,
    padding: 22,
    paddingTop: 28,
    paddingBottom: 40,
    gap: 12,
  },
  rtlPage: {
    direction: "rtl",
  },
  rtlRow: {
    flexDirection: "row-reverse",
  },
  rtlText: {
    textAlign: "right",
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 8,
  },
  headerContent: {
    flex: 1,
  },
  eyebrow: {
    color: C.muted,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.4,
  },
  title: {
    color: C.text,
    fontSize: 25,
    fontWeight: "800",
  },
  subtitle: {
    color: C.secondary,
    fontSize: 14,
    lineHeight: 21,
  },
  center: {
    flex: 1,
    backgroundColor: C.background,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
    gap: 12,
  },
  messageCard: {
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 15,
    padding: 18,
  },
  card: {
    backgroundColor: C.surface,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: C.border,
    borderTopColor: C.gold,
    borderTopWidth: 2,
    padding: 16,
    gap: 8,
  },
  cardTitle: {
    color: C.text,
    fontSize: 17,
    fontWeight: "800",
    flex: 1,
  },
  body: {
    color: C.text,
    fontSize: 14,
    lineHeight: 20,
  },
  muted: {
    color: C.secondary,
    fontSize: 13,
    lineHeight: 19,
  },
  empty: {
    color: C.secondary,
    textAlign: "center",
    padding: 28,
    backgroundColor: C.surface,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: C.border,
  },
  error: {
    color: C.red,
    backgroundColor: C.redBg,
    borderWidth: 1,
    borderColor: "#EAC6C0",
    borderRadius: 11,
    fontSize: 13,
    lineHeight: 19,
    padding: 12,
  },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  badge: {
    overflow: "hidden",
    borderRadius: 99,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 11,
    fontWeight: "800",
  },
  active: {
    color: C.green,
    backgroundColor: C.greenBg,
  },
  inactive: {
    color: C.secondary,
    backgroundColor: C.surfaceMuted,
  },
  field: {
    gap: 6,
  },
  label: {
    color: C.secondary,
    fontSize: 12,
    fontWeight: "700",
  },
  input: {
    minHeight: 46,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    color: C.text,
    fontSize: 14,
  },
  multiline: {
    minHeight: 90,
    textAlignVertical: "top",
    paddingTop: 10,
  },
  button: {
    minHeight: 46,
    borderRadius: 11,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.surface,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
    marginTop: 4,
  },
  buttonText: {
    color: C.navy,
    fontSize: 13,
    fontWeight: "800",
  },
  primaryButton: {
    backgroundColor: C.navy,
    borderColor: C.navy,
  },
  primaryButtonText: {
    color: C.surface,
  },
  pagination: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
    marginTop: 8,
    padding: 10,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 13,
  },
  pageNavButton: {
    minHeight: 38,
    justifyContent: "center",
    paddingHorizontal: 10,
    borderRadius: 9,
    backgroundColor: C.surfaceMuted,
  },
  pageNavText: {
    color: C.navy,
    fontSize: 12,
    fontWeight: "800",
  },
  pageNumbers: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  pageNumber: {
    minWidth: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 9,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.surface,
  },
  pageNumberSelected: {
    backgroundColor: C.navy,
    borderColor: C.navy,
  },
  pageNumberText: {
    color: C.secondary,
    fontSize: 13,
    fontWeight: "700",
  },
  pageNumberTextSelected: {
    color: C.surface,
  },
  disabled: {
    opacity: 0.45,
  },
});