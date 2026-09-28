import { useState } from "react";
import {Pressable, ScrollView, StyleSheet, Text, TextInput,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { resendVerification, verifyEmail } from "../api/client";

export default function VerifyEmailScreen() {
  const params = useLocalSearchParams<{ token?: string; email?: string }>();

  const [token, setToken] = useState(
    typeof params.token === "string" ? params.token : "",
  );
  const [email, setEmail] = useState(
    typeof params.email === "string" ? params.email : "",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleVerify() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await verifyEmail(token.trim());
      setMessage(result.message || "Email verified successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Email verification failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await resendVerification(email);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend verification email.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>Verify your email</Text>
      <Text style={styles.message}>
        Open the verification link from your email, or paste its token below.
      </Text>

      <Text style={styles.label}>Verification token</Text>
      <TextInput
        style={styles.input}
        value={token}
        onChangeText={setToken}
        autoCapitalize="none"
        multiline
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {message ? <Text style={styles.message}>{message}</Text> : null}

      <Pressable
        style={styles.button}
        onPress={handleVerify}
        disabled={busy || !token.trim()}
      >
        <Text style={styles.buttonText}>{busy ? "Verifying…" : "Verify email"}</Text>
      </Pressable>

      <Text style={styles.label}>Need another verification email?</Text>
      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        placeholder="you@company.com"
        autoCapitalize="none"
        keyboardType="email-address"
        autoComplete="email"
      />
      <Pressable
        style={styles.button}
        onPress={handleResend}
        disabled={busy || !email.trim()}
      >
        <Text style={styles.buttonText}>{busy ? "Sending…" : "Resend email"}</Text>
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
  button: { backgroundColor: "#183153", padding: 15, borderRadius: 10, alignItems: "center", marginTop: 16 },
  buttonText: { color: "white", fontWeight: "700" },
  link: { color: "#183153", textAlign: "center", marginTop: 18 },
});