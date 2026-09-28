import { useState } from "react";
import {Pressable, ScrollView, StyleSheet, Text, TextInput,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { register } from "../api/client";
import type { RegisterPayload } from "../api/types";

function isStrongPassword(password: string): boolean {
  const common = new Set([
    "password", "password123", "password123!", "admin123",
    "admin123!", "qwerty123", "12345678", "123456789", "1234567890",
  ]);

  return (
    password.length >= 12 &&
    password.length <= 128 &&
    /[A-Z]/.test(password) &&
    /[a-z]/.test(password) &&
    /\d/.test(password) &&
    /[^\w\s]/.test(password) &&
    !common.has(password.toLowerCase())
  );
}

export default function RegisterScreen() {
  const params = useLocalSearchParams<{ token?: string }>();
  const invitationToken = typeof params.token === "string" ? params.token : "";

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleRegister() {
    setError("");
    setSuccess("");

    if (!isStrongPassword(password)) {
      setError("Use 12–128 characters with uppercase, lowercase, a number, and a symbol.");
      return;
    }
    if (password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }

    const payload: RegisterPayload = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      email: email.trim().toLowerCase(),
      password,
      password_confirmation: confirmation,
      ...(invitationToken
        ? { invitation_token: invitationToken }
        : { organization_name: organizationName.trim() }),
    };

    setBusy(true);
    try {
      const result = await register(payload);
      setSuccess(result.message || "Account created. Check your email to verify it.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  if (success) {
    return (
      <ScrollView contentContainerStyle={styles.page}>
        <Text style={styles.title}>Check your email</Text>
        <Text style={styles.message}>{success}</Text>
        <Pressable
          style={styles.button}
          onPress={() =>
            router.push({
              pathname: "/verify-email",
              params: { email: email.trim().toLowerCase() },
            })
          }
        >
          <Text style={styles.buttonText}>Continue to email verification</Text>
        </Pressable>
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>Create your Trace account</Text>

      <Text style={styles.label}>First name</Text>
      <TextInput style={styles.input} value={firstName} onChangeText={setFirstName} />

      <Text style={styles.label}>Last name</Text>
      <TextInput style={styles.input} value={lastName} onChangeText={setLastName} />

      <Text style={styles.label}>Email</Text>
      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        autoComplete="email"
      />

      {!invitationToken ? (
        <>
          <Text style={styles.label}>Company name</Text>
          <TextInput
            style={styles.input}
            value={organizationName}
            onChangeText={setOrganizationName}
          />
        </>
      ) : (
        <Text style={styles.message}>You are registering with an invitation.</Text>
      )}

      <Text style={styles.label}>Password</Text>
      <TextInput
        style={styles.input}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete="new-password"
      />

      <Text style={styles.label}>Confirm password</Text>
      <TextInput
        style={styles.input}
        value={confirmation}
        onChangeText={setConfirmation}
        secureTextEntry
        autoComplete="new-password"
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Pressable
        style={styles.button}
        onPress={handleRegister}
        disabled={
          busy ||
          !firstName.trim() ||
          !lastName.trim() ||
          !email.trim() ||
          (!invitationToken && !organizationName.trim()) ||
          !password ||
          !confirmation
        }
      >
        <Text style={styles.buttonText}>{busy ? "Creating account…" : "Register"}</Text>
      </Pressable>

      <Pressable onPress={() => router.replace("/")}>
        <Text style={styles.link}>Back to sign in</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, justifyContent: "center", padding: 24, backgroundColor: "#F4F6F8" },
  title: { fontSize: 26, fontWeight: "700", color: "#183153", marginBottom: 18 },
  label: { fontWeight: "600", marginTop: 12, marginBottom: 6, color: "#344054" },
  input: { backgroundColor: "white", borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, padding: 14, fontSize: 16 },
  message: { color: "#344054", marginVertical: 12 },
  error: { color: "#B42318", marginTop: 12 },
  button: { backgroundColor: "#183153", padding: 15, borderRadius: 10, alignItems: "center", marginTop: 20 },
  buttonText: { color: "white", fontWeight: "700" },
  link: { color: "#183153", textAlign: "center", marginTop: 18 },
});