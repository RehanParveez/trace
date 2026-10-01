import { useState } from "react";
import {KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { forgotPassword } from "../api/client";

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit() {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || busy) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const result = await forgotPassword(normalizedEmail);
      setMessage(
        result.message ||
          "If an account exists for that email, reset instructions have been sent.",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not request a password reset. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.screen} edges={["top", "bottom"]}>
      <StatusBar barStyle="dark-content" backgroundColor="#F3EEE4" />
      <KeyboardAvoidingView
        style={styles.keyboard}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.content}>
            <Text style={styles.eyebrow}>ACCOUNT RECOVERY</Text>
            <Text style={styles.title}>Reset your password.</Text>
            <Text style={styles.description}>
              Enter your account email. If an account exists, Trace will send
              password reset instructions.
            </Text>

            {error ? (
              <View style={styles.errorNotice} accessibilityRole="alert">
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            {message ? (
              <View style={styles.successNotice} accessibilityRole="alert">
                <Text style={styles.successText}>{message}</Text>
              </View>
            ) : null}

            {!message ? (
              <>
                <Text style={styles.label}>Work email</Text>
                <TextInput
                  style={styles.input}
                  value={email}
                  onChangeText={setEmail}
                  placeholder="you@company.com"
                  placeholderTextColor="#8C806E"
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="email"
                  textContentType="emailAddress"
                  keyboardType="email-address"
                  returnKeyType="send"
                  onSubmitEditing={() => void handleSubmit()}
                  editable={!busy}
                  accessibilityLabel="Work email"
                />

                <Pressable
                  accessibilityRole="button"
                  style={[
                    styles.primaryButton,
                    (!email.trim() || busy) && styles.disabledButton,
                  ]}
                  onPress={() => void handleSubmit()}
                  disabled={busy || !email.trim()}
                >
                  <Text style={styles.primaryButtonText}>
                    {busy ? "Sending…" : "Send reset instructions"}
                  </Text>
                </Pressable>
              </>
            ) : null}

            <View style={styles.footer}>
              <Text style={styles.footerText}>Remember your password?</Text>
              <Link href="/login" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={styles.link}>Return to sign in</Text>
                </Pressable>
              </Link>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F3EEE4" },
  keyboard: { flex: 1 },
  scrollContent: { flexGrow: 1, justifyContent: "center", padding: 22 },
  content: { width: "100%", maxWidth: 460, alignSelf: "center" },
  eyebrow: { marginBottom: 8, color: "#B98626", fontSize: 10, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: "#191410", fontSize: 31, fontWeight: "800" },
  description: { marginTop: 9, marginBottom: 22, color: "#5C5347", fontSize: 14, lineHeight: 21 },
  label: { marginBottom: 7, color: "#191410", fontSize: 13, fontWeight: "700" },
  input: {minHeight: 48, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, backgroundColor: "#FFFFFF", paddingHorizontal: 13, color: "#191410", fontSize: 15,},
  primaryButton: {minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 18, borderRadius: 8, backgroundColor: "#D9A441", paddingHorizontal: 16,},
  disabledButton: { opacity: 0.5 },
  primaryButtonText: { color: "#080D18", fontSize: 14, fontWeight: "800" },
  errorNotice: { marginBottom: 14, borderRadius: 8, backgroundColor: "#F9E5DF", padding: 12 },
  errorText: { color: "#C24A3A", fontSize: 13, lineHeight: 19 },
  successNotice: { borderRadius: 8, backgroundColor: "#E4F5EC", padding: 13 },
  successText: { color: "#1E9D63", fontSize: 13, lineHeight: 19 },
  footer: { flexDirection: "row", justifyContent: "center", gap: 5, marginTop: 24 },
  footerText: { color: "#5C5347", fontSize: 12 },
  link: { color: "#B98626", fontSize: 12, fontWeight: "800" },
});