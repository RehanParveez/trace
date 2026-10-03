import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {createClient, deleteClient, deleteProject, getProject, listClients, updateClient, updateProject,
} from "../../../../api/projects";
import type { Client, Project, ProjectStatus } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";

const PAGE_SIZE = 5;

const statuses: ProjectStatus[] = [
  "PLANNING",
  "ACTIVE",
  "ON_HOLD",
  "COMPLETED",
  "CANCELLED",
];

function clean(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function validDate(value: string): boolean {
  if (!value) return true;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return (
    !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
  );
}

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

export default function ManageProjectScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clientsPage, setClientsPage] = useState(1);

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [startDate, setStartDate] = useState("");
  const [expectedEndDate, setExpectedEndDate] = useState("");
  const [actualEndDate, setActualEndDate] = useState("");
  const [status, setStatus] = useState<ProjectStatus>("PLANNING");
  const [clientId, setClientId] = useState("");

  const [clientName, setClientName] = useState("");
  const [clientContact, setClientContact] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [editingClientId, setEditingClientId] = useState("");

  const canUpdate = permissions.includes("project.update");
  const canDelete = permissions.includes("project.delete");
  const clientsPages = pageCount(clients.length);
  const visibleClients = paginate(clients, clientsPage);

  const load = useCallback(async () => {
    if (!projectId) {
      setError(t("manageProject.projectNotFound"));
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }

      const granted = user.role.permissions.map((permission) => permission.key);
      setPermissions(granted);

      const projectResult = await getProject(projectId);
      setProject(projectResult);
      setName(projectResult.name);
      setCode(projectResult.code ?? "");
      setDescription(projectResult.description ?? "");
      setLocation(projectResult.location ?? "");
      setStartDate(projectResult.start_date ?? "");
      setExpectedEndDate(projectResult.expected_end_date ?? "");
      setActualEndDate(projectResult.actual_end_date ?? "");
      setStatus(projectResult.status);
      setClientId(projectResult.client_id ?? "");

      try {
        setClients(await listClients());
        setClientsPage(1);
      } catch {
        // Client directory is optional for this screen.
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("manageProject.loadFailure"),
      );
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");

    try {
      await action();
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("manageProject.actionFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveProject() {
    if (!projectId || !name.trim()) {
      setError(t("manageProject.validation.projectName"));
      return;
    }

    if (![startDate, expectedEndDate, actualEndDate].every(validDate)) {
      setError(t("manageProject.validation.dates"));
      return;
    }

    await run(() =>
      updateProject(projectId, {
        name: name.trim(),
        code: clean(code),
        description: clean(description),
        location: clean(location),
        client_id: clientId || null,
        status,
        start_date: startDate || null,
        expected_end_date: expectedEndDate || null,
        actual_end_date: actualEndDate || null,
      }),
    );
  }

  function confirmDeleteProject() {
    if (!projectId) return;

    Alert.alert(
      t("manageProject.deleteProjectConfirmTitle"),
      t("manageProject.deleteProjectConfirmMessage"),
      [
        {
          text: t("manageProject.cancel"),
          style: "cancel",
        },
        {
          text: t("manageProject.delete"),
          style: "destructive",
          onPress: () => {
            void run(async () => {
              await deleteProject(projectId);
              router.replace("/projects");
            });
          },
        },
      ],
    );
  }

  async function saveClient() {
    if (!clientName.trim()) {
      setError(t("manageProject.validation.clientName"));
      return;
    }

    const payload = {
      name: clientName.trim(),
      contact_name: clean(clientContact),
      email: clean(clientEmail),
      phone: clean(clientPhone),
    };

    await run(async () => {
      if (editingClientId) {
        await updateClient(editingClientId, payload);
      } else {
        await createClient(payload);
      }
      clearClientForm();
    });
  }

  function clearClientForm() {
    setClientName("");
    setClientContact("");
    setClientEmail("");
    setClientPhone("");
    setEditingClientId("");
  }

  function beginEditClient(client: Client) {
    setEditingClientId(client.id);
    setClientName(client.name);
    setClientContact(client.contact_name ?? "");
    setClientEmail(client.email ?? "");
    setClientPhone(client.phone ?? "");
  }

  async function assignClient(id: string) {
    if (!projectId) return;
    setClientId(id);
    await run(() => updateProject(projectId, { client_id: id || null }));
  }

  function confirmDeleteClient(client: Client) {
    Alert.alert(
      t("manageProject.deleteClientConfirmTitle"),
      t("manageProject.deleteClientConfirmMessage", { name: client.name }),
      [
        {
          text: t("manageProject.cancel"),
          style: "cancel",
        },
        {
          text: t("manageProject.delete"),
          style: "destructive",
          onPress: () =>
            void run(async () => {
              await deleteClient(client.id);
              if (clientId === client.id && projectId) {
                await updateProject(projectId, { client_id: null });
                setClientId("");
              }
            }),
        },
      ],
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("manageProject.loading")}
        </Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, styles.headerCopy, isUrdu && styles.rtlText]}>
            {t("manageProject.title")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error || t("manageProject.projectNotFound")}
        </Text>
        <Pressable onPress={() => router.back()}>
          <Text style={[styles.link, isUrdu && styles.rtlText]}>
            {t("manageProject.backToProject")}
          </Text>
        </Pressable>
      </View>
    );
  }

  if (!canUpdate && !canDelete) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, styles.headerCopy, isUrdu && styles.rtlText]}>
            {t("manageProject.title")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {t("manageProject.accessDenied")}
        </Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("manageProject.backToProjectName", { name: project.name })}
              </Text>
            </Pressable>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("manageProject.title")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
        ) : null}

        {canUpdate ? (
          <>
            <Text style={[styles.section, isUrdu && styles.rtlText]}>
              {t("manageProject.projectDetails")}
            </Text>

            <Field
              label={t("manageProject.projectName")}
              value={name}
              onChangeText={setName}
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.projectCode")}
              value={code}
              onChangeText={setCode}
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.location")}
              value={location}
              onChangeText={setLocation}
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.description")}
              value={description}
              onChangeText={setDescription}
              multiline
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.startDate")}
              value={startDate}
              onChangeText={setStartDate}
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.expectedEndDate")}
              value={expectedEndDate}
              onChangeText={setExpectedEndDate}
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.actualEndDate")}
              value={actualEndDate}
              onChangeText={setActualEndDate}
              isUrdu={isUrdu}
            />

            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("manageProject.status")}
            </Text>
            <View style={[styles.chips, isUrdu && styles.rtlRow]}>
              {statuses.map((value) => (
                <Chip
                  key={value}
                  label={t(`manageProject.status.${value.toLowerCase()}`)}
                  selected={status === value}
                  onPress={() => setStatus(value)}
                  isUrdu={isUrdu}
                />
              ))}
            </View>

            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("manageProject.assignClient")}
            </Text>
            <View style={[styles.chips, isUrdu && styles.rtlRow]}>
              <Chip
                label={t("manageProject.noClient")}
                selected={!clientId}
                onPress={() => void assignClient("")}
                isUrdu={isUrdu}
              />
              {visibleClients.map((client) => (
                <Chip
                  key={client.id}
                  label={client.name}
                  selected={clientId === client.id}
                  onPress={() => void assignClient(client.id)}
                  isUrdu={isUrdu}
                />
              ))}
            </View>
            {clients.length > 0 ? (
              <Pagination
                page={clientsPage}
                pages={clientsPages}
                isUrdu={isUrdu}
                onPrevious={() =>
                  setClientsPage((page) => Math.max(1, page - 1))
                }
                onNext={() =>
                  setClientsPage((page) => Math.min(clientsPages, page + 1))
                }
              />
            ) : null}

            <Action
              title={t("manageProject.saveProject")}
              onPress={() => void saveProject()}
              isUrdu={isUrdu}
            />
          </>
        ) : null}

        {canUpdate ? (
          <>
            <Text style={[styles.section, isUrdu && styles.rtlText]}>
              {t("manageProject.clients")}
            </Text>

            <Field
              label={t("manageProject.clientName")}
              value={clientName}
              onChangeText={setClientName}
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.contactName")}
              value={clientContact}
              onChangeText={setClientContact}
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.email")}
              value={clientEmail}
              onChangeText={setClientEmail}
              keyboardType="email-address"
              isUrdu={isUrdu}
            />
            <Field
              label={t("manageProject.phone")}
              value={clientPhone}
              onChangeText={setClientPhone}
              keyboardType="phone-pad"
              isUrdu={isUrdu}
            />

            <Action
              title={
                editingClientId
                  ? t("manageProject.saveClientChanges")
                  : t("manageProject.createClient")
              }
              onPress={() => void saveClient()}
              isUrdu={isUrdu}
            />

            {editingClientId ? (
              <Action
                title={t("manageProject.cancelClientEdit")}
                secondary
                onPress={clearClientForm}
                isUrdu={isUrdu}
              />
            ) : null}

            {visibleClients.map((client) => (
              <View key={client.id} style={styles.card}>
                <Text style={[styles.itemTitle, isUrdu && styles.rtlText]}>
                  {client.name}
                </Text>
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {client.contact_name || client.email || client.phone || ""}
                </Text>
                <View style={[styles.row, isUrdu && styles.rtlRow]}>
                  <Action
                    title={t("manageProject.edit")}
                    secondary
                    onPress={() => beginEditClient(client)}
                    isUrdu={isUrdu}
                  />
                  <Action
                    title={t("manageProject.delete")}
                    danger
                    onPress={() => confirmDeleteClient(client)}
                    isUrdu={isUrdu}
                  />
                </View>
              </View>
            ))}

            {clients.length === 0 ? (
              <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                {t("manageProject.noClients")}
              </Text>
            ) : (
              <Pagination
                page={clientsPage}
                pages={clientsPages}
                isUrdu={isUrdu}
                onPrevious={() =>
                  setClientsPage((page) => Math.max(1, page - 1))
                }
                onNext={() =>
                  setClientsPage((page) => Math.min(clientsPages, page + 1))
                }
              />
            )}
          </>
        ) : null}

        {canDelete ? (
          <>
            <Text style={[styles.section, isUrdu && styles.rtlText]}>
              {t("manageProject.dangerZone")}
            </Text>
            <Action
              title={t("manageProject.deleteProject")}
              danger
              onPress={confirmDeleteProject}
              isUrdu={isUrdu}
            />
          </>
        ) : null}

        {busy ? (
          <View style={styles.busy}>
            <ActivityIndicator color={COLORS.navy} />
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("manageProject.saving")}
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
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
      <Action
        title={t("manageProject.previous")}
        secondary
        disabled={props.page <= 1}
        onPress={props.onPrevious}
        isUrdu={props.isUrdu}
      />
      <Text style={[styles.pageText, props.isUrdu && styles.rtlText]}>
        {t("manageProject.pageOf", {
          page: props.page,
          pages: props.pages,
        })}
      </Text>
      <Action
        title={t("manageProject.next")}
        secondary
        disabled={props.page >= props.pages}
        onPress={props.onNext}
        isUrdu={props.isUrdu}
      />
    </View>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  multiline?: boolean;
  keyboardType?: "default" | "email-address" | "phone-pad";
  isUrdu: boolean;
}) {
  return (
    <>
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
        multiline={props.multiline}
        textAlignVertical={props.multiline ? "top" : "center"}
        textAlign={props.isUrdu ? "right" : "left"}
        keyboardType={props.keyboardType ?? "default"}
        autoCapitalize={
          props.keyboardType === "email-address" ? "none" : "sentences"
        }
      />
    </>
  );
}

function Chip(props: {
  label: string;
  selected: boolean;
  onPress: () => void;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[styles.chip, props.selected && styles.chipSelected]}
      onPress={props.onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: props.selected }}
    >
      <Text
        style={[
          styles.chipText,
          props.selected && styles.chipTextSelected,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.label}
      </Text>
    </Pressable>
  );
}

function Action(props: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  danger?: boolean;
  disabled?: boolean;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.action,
        props.secondary && styles.actionSecondary,
        props.danger && styles.actionDanger,
        props.disabled && styles.disabled,
      ]}
      onPress={props.onPress}
      disabled={props.disabled}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          props.secondary && styles.actionSecondaryText,
          props.danger && styles.actionDangerText,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.title}
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
};

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: COLORS.background },
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 38, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 6 },
  headerCopy: { flex: 1 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 26, fontWeight: "800", marginTop: 10, marginBottom: 8 },
  section: { color: COLORS.text, fontSize: 18, fontWeight: "800", marginTop: 22, marginBottom: 4 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 13, marginBottom: 6 },
  input: { minHeight: 46, backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: COLORS.text },
  multiline: { minHeight: 82, textAlignVertical: "top" },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 10 },
  itemTitle: { color: COLORS.text, fontSize: 15, fontWeight: "800" },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 6, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginVertical: 10, lineHeight: 19, fontSize: 13 },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 5 },
  chip: { borderWidth: 1, borderColor: COLORS.border, borderRadius: 99, backgroundColor: COLORS.surface, paddingHorizontal: 13, paddingVertical: 9, marginTop: 4 },
  chipSelected: { borderColor: COLORS.gold, backgroundColor: COLORS.surfaceMuted },
  chipText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700" },
  chipTextSelected: { color: COLORS.navy },
  action: { minHeight: 44, flexGrow: 1, backgroundColor: COLORS.navy, borderRadius: 10, borderWidth: 1, borderColor: COLORS.navy, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 11, marginTop: 10 },
  actionSecondary: { backgroundColor: COLORS.surface, borderColor: COLORS.border },
  actionDanger: { backgroundColor: COLORS.red, borderColor: COLORS.red },
  actionText: { color: COLORS.surface, fontSize: 13, fontWeight: "800", textAlign: "center" },
  actionSecondaryText: { color: COLORS.navy },
  actionDangerText: { color: COLORS.surface },
  disabled: { opacity: 0.5 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 8 },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", textAlign: "center" },
  busy: { alignItems: "center", padding: 18, gap: 8 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});