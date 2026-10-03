import { useEffect, useState } from "react";
import {ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router, Stack } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../api/client";
import { createProject, listClients } from "../../../api/projects";
import type { Client } from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

const PAGE_SIZE = 5;

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

export default function NewProjectScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [checkingAccess, setCheckingAccess] = useState(true);
  const [canCreate, setCanCreate] = useState(false);
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState("");
  const [showClients, setShowClients] = useState(false);
  const [clientPage, setClientPage] = useState(1);

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [startDate, setStartDate] = useState("");
  const [expectedEndDate, setExpectedEndDate] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function checkAccessAndLoadClients() {
      try {
        const user = await restoreSession();

        if (!user) {
          router.replace("/");
          return;
        }

        const allowed = user.role.permissions.some(
          (permission) => permission.key === "project.create",
        );

        if (active) setCanCreate(allowed);

        if (allowed) {
          try {
            const result = await listClients();
            if (active) {
              setClients(result);
              setClientPage(1);
            }
          } catch {
            // Creating a project without an optional client remains possible.
          }
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : t("newProject.accessCheckFailure"),
          );
        }
      } finally {
        if (active) setCheckingAccess(false);
      }
    }

    void checkAccessAndLoadClients();

    return () => {
      active = false;
    };
  }, [t]);

  async function handleCreate() {
    setError("");

    if (!name.trim()) {
      setError(t("newProject.validation.name"));
      return;
    }

    if (startDate && !/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
      setError(t("newProject.validation.startDate"));
      return;
    }

    if (expectedEndDate && !/^\d{4}-\d{2}-\d{2}$/.test(expectedEndDate)) {
      setError(t("newProject.validation.expectedEndDate"));
      return;
    }

    setBusy(true);

    try {
      const project = await createProject({
        name: name.trim(),
        code: code.trim() || null,
        description: description.trim() || null,
        location: location.trim() || null,
        client_id: clientId || null,
        start_date: startDate || null,
        expected_end_date: expectedEndDate || null,
      });

      router.replace({
        pathname: "/projects/[projectId]",
        params: { projectId: project.id },
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("newProject.createFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  if (checkingAccess) {
    return (
      <>
        <Stack.Screen options={{ title: t("newProject.title") }} />
        <View style={styles.center}>
          <View style={styles.switcherRow}>
            <LanguageSwitcher />
          </View>
          <ActivityIndicator size="large" color={COLORS.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("newProject.checkingAccess")}
          </Text>
        </View>
      </>
    );
  }

  if (!canCreate) {
    return (
      <>
        <Stack.Screen options={{ title: t("newProject.title") }} />
        <View style={styles.page}>
          <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("newProject.projects")}
              </Text>
            </Pressable>
            <LanguageSwitcher />
          </View>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("newProject.title")}
          </Text>
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {error || t("newProject.accessDenied")}
          </Text>
        </View>
      </>
    );
  }

  const selectedClient = clients.find((client) => client.id === clientId);
  const clientPages = pageCount(clients.length);
  const visibleClients = paginate(clients, clientPage);

  return (
    <>
      <Stack.Screen options={{ title: t("newProject.title") }} />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.page}
          keyboardShouldPersistTaps="handled"
        >
          <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("newProject.projects")}
              </Text>
            </Pressable>
            <LanguageSwitcher />
          </View>

          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("newProject.title")}
          </Text>
          <Text style={[styles.subtitle, isUrdu && styles.rtlText]}>
            {t("newProject.subtitle")}
          </Text>

          {error ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
          ) : null}

          <View style={styles.card}>
            <Field
              label={t("newProject.projectNameRequired")}
              value={name}
              onChangeText={setName}
              placeholder={t("newProject.projectNamePlaceholder")}
              maxLength={200}
              isUrdu={isUrdu}
            />

            <Field
              label={t("newProject.projectCode")}
              value={code}
              onChangeText={setCode}
              placeholder={t("newProject.projectCodePlaceholder")}
              maxLength={100}
              autoCapitalize="characters"
              isUrdu={isUrdu}
            />

            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("newProject.client")}
            </Text>
            <Pressable
              style={[styles.selectButton, isUrdu && styles.rtlRow]}
              onPress={() => setShowClients((visible) => !visible)}
              accessibilityRole="button"
              accessibilityState={{ expanded: showClients }}
            >
              <Text
                style={[
                  selectedClient ? styles.inputText : styles.placeholder,
                  isUrdu && styles.rtlText,
                ]}
              >
                {selectedClient?.name || t("newProject.noClientSelected")}
              </Text>
              <Text style={styles.chevron}>{showClients ? "⌃" : "⌄"}</Text>
            </Pressable>

            {showClients ? (
              <View style={styles.options}>
                <Pressable
                  style={styles.option}
                  onPress={() => {
                    setClientId("");
                    setShowClients(false);
                  }}
                >
                  <Text style={[styles.optionText, isUrdu && styles.rtlText]}>
                    {t("newProject.noClient")}
                  </Text>
                </Pressable>

                {visibleClients.map((client) => (
                  <Pressable
                    key={client.id}
                    style={styles.option}
                    onPress={() => {
                      setClientId(client.id);
                      setShowClients(false);
                    }}
                  >
                    <Text style={[styles.optionText, isUrdu && styles.rtlText]}>
                      {client.name}
                    </Text>
                  </Pressable>
                ))}

                {clients.length === 0 ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("newProject.noClientsAvailable")}
                  </Text>
                ) : null}

                {clients.length > PAGE_SIZE ? (
                  <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
                    <Pressable
                      style={[
                        styles.pageButton,
                        clientPage <= 1 && styles.disabled,
                      ]}
                      onPress={() =>
                        setClientPage((page) => Math.max(1, page - 1))
                      }
                      disabled={clientPage <= 1}
                    >
                      <Text
                        style={[
                          styles.pageButtonText,
                          isUrdu && styles.rtlText,
                        ]}
                      >
                        {t("newProject.previous")}
                      </Text>
                    </Pressable>
                    <Text style={[styles.pageText, isUrdu && styles.rtlText]}>
                      {t("newProject.pageOf", {
                        page: clientPage,
                        pages: clientPages,
                      })}
                    </Text>
                    <Pressable
                      style={[
                        styles.pageButton,
                        clientPage >= clientPages && styles.disabled,
                      ]}
                      onPress={() =>
                        setClientPage((page) =>
                          Math.min(clientPages, page + 1),
                        )
                      }
                      disabled={clientPage >= clientPages}
                    >
                      <Text
                        style={[
                          styles.pageButtonText,
                          isUrdu && styles.rtlText,
                        ]}
                      >
                        {t("newProject.next")}
                      </Text>
                    </Pressable>
                  </View>
                ) : null}
              </View>
            ) : null}

            <Field
              label={t("newProject.location")}
              value={location}
              onChangeText={setLocation}
              placeholder={t("newProject.locationPlaceholder")}
              maxLength={500}
              isUrdu={isUrdu}
            />

            <Field
              label={t("newProject.description")}
              value={description}
              onChangeText={setDescription}
              placeholder={t("newProject.descriptionPlaceholder")}
              multiline
              isUrdu={isUrdu}
            />

            <Field
              label={t("newProject.startDate")}
              value={startDate}
              onChangeText={setStartDate}
              placeholder="YYYY-MM-DD"
              autoCapitalize="none"
              isUrdu={isUrdu}
            />

            <Field
              label={t("newProject.expectedEndDate")}
              value={expectedEndDate}
              onChangeText={setExpectedEndDate}
              placeholder="YYYY-MM-DD"
              autoCapitalize="none"
              isUrdu={isUrdu}
            />
          </View>

          <Pressable
            style={[
              styles.primaryButton,
              (busy || !name.trim()) && styles.disabled,
            ]}
            onPress={() => void handleCreate()}
            disabled={busy || !name.trim()}
            accessibilityRole="button"
          >
            <Text style={[styles.primaryButtonText, isUrdu && styles.rtlText]}>
              {busy
                ? t("newProject.creating")
                : t("newProject.createProject")}
            </Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
  multiline?: boolean;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
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
        placeholder={props.placeholder}
        placeholderTextColor={COLORS.muted}
        maxLength={props.maxLength}
        multiline={props.multiline}
        textAlignVertical={props.multiline ? "top" : "center"}
        textAlign={props.isUrdu ? "right" : "left"}
        autoCapitalize={props.autoCapitalize ?? "sentences"}
      />
    </>
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
  page: { flexGrow: 1, padding: 20, paddingTop: 22, paddingBottom: 38, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 26, fontWeight: "800", marginTop: 14 },
  subtitle: { color: COLORS.secondary, fontSize: 13, marginTop: 7, marginBottom: 14, lineHeight: 20 },
  card: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 13, marginBottom: 6 },
  input: { minHeight: 46, backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: COLORS.text },
  multiline: { minHeight: 88, textAlignVertical: "top" },
  selectButton: { minHeight: 46, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 12, paddingVertical: 10 },
  inputText: { flex: 1, color: COLORS.text, fontSize: 14 },
  placeholder: { flex: 1, color: COLORS.muted, fontSize: 14 },
  chevron: { color: COLORS.secondary, fontSize: 17, fontWeight: "800", marginLeft: 10 },
  options: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 11, marginTop: 6, paddingHorizontal: 12, paddingBottom: 8 },
  option: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#F0EADF" },
  optionText: { color: COLORS.text, fontSize: 13, fontWeight: "700" },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 6, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginTop: 12, lineHeight: 19, fontSize: 13 },
  primaryButton: { minHeight: 48, alignItems: "center", justifyContent: "center", backgroundColor: COLORS.navy, borderRadius: 11, marginTop: 16, paddingHorizontal: 15, paddingVertical: 13 },
  primaryButtonText: { color: COLORS.surface, fontSize: 14, fontWeight: "800", textAlign: "center" },
  disabled: { opacity: 0.55 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, paddingVertical: 8 },
  pageButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  pageButtonText: { color: COLORS.navy, fontSize: 11, fontWeight: "800" },
  pageText: { color: COLORS.secondary, fontSize: 11, fontWeight: "700" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});