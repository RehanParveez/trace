import { useEffect, useState } from "react";
import {ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router } from "expo-router";
import { restoreSession } from "../../api/client";
import { createProject, listClients } from "../../api/projects";
import type { Client } from "../../api/types";

export default function NewProjectScreen() {
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [canCreate, setCanCreate] = useState(false);
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState("");
  const [showClients, setShowClients] = useState(false);

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
            if (active) setClients(result);
          } catch {

          }
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Could not check your access.",
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
  }, []);

  async function handleCreate() {
    setError("");

    if (!name.trim()) {
      setError("Enter a project name.");
      return;
    }

    if (startDate && !/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
     setError("Use YYYY-MM-DD for the start date.");
     return;
    }

    if (expectedEndDate && !/^\d{4}-\d{2}-\d{2}$/.test(expectedEndDate)) {
      setError("Use YYYY-MM-DD for the expected end date.");
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
        err instanceof Error ? err.message : "Could not create the project.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (checkingAccess) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Checking access…</Text>
      </View>
    );
  }

  if (!canCreate) {
    return (
      <View style={styles.page}>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  Projects</Text>
        </Pressable>
        <Text style={styles.title}>Create project</Text>
        <Text style={styles.error}>
          {error || "Your organization role does not allow project creation."}
        </Text>
      </View>
    );
  }

  const selectedClient = clients.find((client) => client.id === clientId);

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  Projects</Text>
        </Pressable>

        <Text style={styles.title}>Create project</Text>
        <Text style={styles.subtitle}>
          Add the project details. The project will belong to your active
          organization.
        </Text>

        <Text style={styles.label}>Project name *</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
          placeholder="e.g. Riverside Apartments"
          maxLength={200}
        />

        <Text style={styles.label}>Project code</Text>
        <TextInput
          style={styles.input}
          value={code}
          onChangeText={setCode}
          placeholder="e.g. RA-01"
          maxLength={100}
          autoCapitalize="characters"
        />

        <Text style={styles.label}>Client</Text>
        <Pressable
          style={styles.input}
          onPress={() => setShowClients((visible) => !visible)}
          accessibilityRole="button"
        >
          <Text style={selectedClient ? styles.inputText : styles.placeholder}>
            {selectedClient?.name || "No client selected"}
          </Text>
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
              <Text style={styles.optionText}>No client</Text>
            </Pressable>
            {clients.map((client) => (
              <Pressable
                key={client.id}
                style={styles.option}
                onPress={() => {
                  setClientId(client.id);
                  setShowClients(false);
                }}
              >
                <Text style={styles.optionText}>{client.name}</Text>
              </Pressable>
            ))}
            {clients.length === 0 ? (
              <Text style={styles.muted}>
                No clients are available. You can continue without one.
              </Text>
            ) : null}
          </View>
        ) : null}

        <Text style={styles.label}>Location</Text>
        <TextInput
          style={styles.input}
          value={location}
          onChangeText={setLocation}
          placeholder="Site address or area"
          maxLength={500}
        />

        <Text style={styles.label}>Description</Text>
        <TextInput
          style={[styles.input, styles.multiline]}
          value={description}
          onChangeText={setDescription}
          placeholder="What is being built?"
          multiline
          textAlignVertical="top"
        />

        <Text style={styles.label}>Start date</Text>
        <TextInput
          style={styles.input}
          value={startDate}
          onChangeText={setStartDate}
          placeholder="YYYY-MM-DD"
          autoCapitalize="none"
        />

        <Text style={styles.label}>Expected end date</Text>
        <TextInput
          style={styles.input}
          value={expectedEndDate}
          onChangeText={setExpectedEndDate}
          placeholder="YYYY-MM-DD"
          autoCapitalize="none"
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          style={[styles.primaryButton, busy && styles.disabled]}
          onPress={() => void handleCreate()}
          disabled={busy || !name.trim()}
          accessibilityRole="button"
        >
          <Text style={styles.primaryButtonText}>
            {busy ? "Creating project…" : "Create project"}
          </Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#F4F6F8" },
  page: {
    flexGrow: 1,
    padding: 24,
    paddingTop: 54,
    backgroundColor: "#F4F6F8",
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    backgroundColor: "#F4F6F8",
  },
  title: { color: "#17212F", fontSize: 28, fontWeight: "700", marginTop: 20 },
  subtitle: { color: "#667085", marginTop: 8, marginBottom: 18, lineHeight: 21 },
  label: {
    color: "#344054",
    fontSize: 14,
    fontWeight: "600",
    marginTop: 14,
    marginBottom: 7,
  },
  input: {
    backgroundColor: "white",
    borderColor: "#D0D5DD",
    borderWidth: 1,
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: "#17212F",
  },
  inputText: { color: "#17212F" },
  placeholder: { color: "#667085" },
  options: {
    backgroundColor: "white",
    borderWidth: 1,
    borderColor: "#E4E7EC",
    borderRadius: 10,
    marginTop: 6,
    paddingHorizontal: 12,
  },
  option: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#F0F2F5" },
  optionText: { color: "#17212F", fontWeight: "600" },
  multiline: { minHeight: 96 },
  link: { color: "#183153", fontWeight: "600", fontSize: 15 },
  muted: { color: "#667085", marginTop: 6, lineHeight: 20 },
  error: { color: "#B42318", marginTop: 14, lineHeight: 20 },
  primaryButton: {
    alignItems: "center",
    backgroundColor: "#183153",
    borderRadius: 10,
    marginTop: 22,
    padding: 15,
  },
  primaryButtonText: { color: "white", fontSize: 16, fontWeight: "700" },
  disabled: { opacity: 0.55 },
});