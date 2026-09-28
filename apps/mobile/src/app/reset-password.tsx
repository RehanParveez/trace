import { useState } from "react";
import {Pressable, ScrollView, StyleSheet, Text, TextInput,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { resetPassword } from "../api/client";

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

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ token?: string }>();

  const [token, setToken] = useState(
    typeof params.token === "string" ? params.token : "",
  );
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit() {
    setError("");
    setMessage("");

    if (!token.trim()) {
      setError("Enter the reset token from your email.");
      return;
    }
    if (!isStrongPassword(password)) {
      setError("Use 12–128 characters with uppercase, lowercase, a number, and a symbol.");
      return;
    }
    if (password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      const result = await resetPassword(token.trim(), password, confirmation);
      setMessage(result.message || "Password reset successfully.");
      setPassword("");
      setConfirmation("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password reset failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>Choose a new password</Text>
      <Text style={styles.message}>
        Paste the reset token from your email, then enter your new password.
      </Text>

      <Text style={styles.label}>Reset token</Text>
      <TextInput
        style={styles.input}
        value={token}
        onChangeText={setToken}
        autoCapitalize="none"
        multiline
      />

      <Text style={styles.label}>New password</Text>
      <TextInput
        style={styles.input}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete="new-password"
      />

      <Text style={styles.label}>Confirm new password</Text>
      <TextInput
        style={styles.input}
        value={confirmation}
        onChangeText={setConfirmation}
        secureTextEntry
        autoComplete="new-password"
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {message ? <Text style={styles.message}>{message}</Text> : null}

      {message ? (
        <Pressable style={styles.button} onPress={() => router.replace("/")}>
          <Text style={styles.buttonText}>Return to sign in</Text>
        </Pressable>
      ) : (
        <Pressable
          style={styles.button}
          onPress={handleSubmit}
          disabled={busy || !token.trim() || !password || !confirmation}
        >
          <Text style={styles.buttonText}>
            {busy ? "Resetting…" : "Reset password"}
          </Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, justifyContent: "center", padding: 24, backgroundColor: "#F4F6F8" },
  title: { fontSize: 26, fontWeight: "700", color: "#183153", marginBottom: 12 },
  label: { fontWeight: "600", marginTop: 16, marginBottom: 6, color: "#344054" },
  input: { backgroundColor: "white", borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, padding: 14, fontSize: 16 },
  message: { color: "#344054", marginVertical: 12 },
  error: { color: "#B42318", marginTop: 12 },
  button: { backgroundColor: "#183153", padding: 15, borderRadius: 10, alignItems: "center", marginTop: 20 },
  buttonText: { color: "white", fontWeight: "700" },
});