import { useState } from "react";
import {Pressable, ScrollView, StyleSheet, Text, TextInput,
} from "react-native";
import { router } from "expo-router";
import { forgotPassword } from "../api/client";

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await forgotPassword(email);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request a reset email.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>Reset your password</Text>
      <Text style={styles.message}>
        Enter your account email. If an account exists, Trace will send reset instructions.
      </Text>

      <Text style={styles.label}>Email</Text>
      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        placeholder="you@company.com"
        autoCapitalize="none"
        keyboardType="email-address"
        autoComplete="email"
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {message ? <Text style={styles.message}>{message}</Text> : null}

      <Pressable
        style={styles.button}
        onPress={handleSubmit}
        disabled={busy || !email.trim()}
      >
        <Text style={styles.buttonText}>
          {busy ? "Sending…" : "Send reset instructions"}
        </Text>
      </Pressable>

      <Pressable onPress={() => router.replace("/")}>
        <Text style={styles.link}>Back to sign in</Text>
      </Pressable>
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
  link: { color: "#183153", textAlign: "center", marginTop: 18 },
});