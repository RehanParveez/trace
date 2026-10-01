import { useEffect, useState } from "react";
import {KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link, useLocalSearchParams } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { resetPassword } from "../api/client";

const passwordRules = [
  { label: "12–128 characters", test: (value: string) => value.length >= 12 && value.length <= 128 },
  { label: "An uppercase letter", test: (value: string) => /[A-Z]/.test(value) },
  { label: "A lowercase letter", test: (value: string) => /[a-z]/.test(value) },
  { label: "A number", test: (value: string) => /\d/.test(value) },
  { label: "A symbol", test: (value: string) => /[^\w\s]/.test(value) },
  {
    label: "Not a common password",
    test: (value: string) =>
      !new Set([
        "password",
        "password123",
        "password123!",
        "admin123",
        "admin123!",
        "qwerty123",
        "12345678",
        "123456789",
        "1234567890",
      ]).has(value.toLowerCase()),
  },
];

function passwordIsStrong(value: string) {
  return passwordRules.every((rule) => rule.test(value));
}

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ token?: string | string[] }>();
  const routeToken = Array.isArray(params.token)
    ? params.token[0] ?? ""
    : params.token ?? "";

  const [token, setToken] = useState(routeToken);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (routeToken) {
      setToken(routeToken);
    }
  }, [routeToken]);

  const passwordsMatch = password === confirmation;
  const strongPassword = passwordIsStrong(password);

  async function handleSubmit() {
    if (busy) {
      return;
    }

    setError("");
    setSuccessMessage("");

    if (!token.trim()) {
      setError("The reset link is missing its token. Request a new link.");
      return;
    }
    if (!strongPassword) {
      setError("Meet all password requirements before continuing.");
      return;
    }
    if (!passwordsMatch) {
      setError("The passwords do not match.");
      return;
    }

    setBusy(true);

    try {
      const result = await resetPassword(
        token.trim(),
        password,
        confirmation,
      );
      setSuccessMessage(result.message || "Your password has been reset.");
      setPassword("");
      setConfirmation("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Password reset failed. Try again.",
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
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.content}>
            <Text style={styles.eyebrow}>ACCOUNT SECURITY</Text>
            <Text style={styles.title}>
              {successMessage ? "Password updated." : "Choose a new password."}
            </Text>

            {successMessage ? (
              <View style={styles.successNotice} accessibilityRole="alert">
                <Text style={styles.successText}>{successMessage}</Text>
              </View>
            ) : (
              <>
                <Text style={styles.description}>
                  Use the reset link from your email, then create a new password
                  for your Trace account.
                </Text>

                {!routeToken ? (
                  <>
                    <Text style={styles.label}>Reset token</Text>
                    <TextInput
                      style={styles.input}
                      value={token}
                      onChangeText={setToken}
                      autoCapitalize="none"
                      autoCorrect={false}
                      placeholder="Paste the token from your email"
                      placeholderTextColor="#8C806E"
                      editable={!busy}
                      accessibilityLabel="Password reset token"
                    />
                  </>
                ) : null}

                {error ? (
                  <View style={styles.errorNotice} accessibilityRole="alert">
                    <Text style={styles.errorText}>{error}</Text>
                  </View>
                ) : null}

                <Text style={styles.label}>New password</Text>
                <TextInput
                  style={styles.input}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  autoComplete="new-password"
                  textContentType="newPassword"
                  placeholder="Create a strong password"
                  placeholderTextColor="#8C806E"
                  editable={!busy}
                  returnKeyType="next"
                />

                {password ? (
                  <View style={styles.passwordCard}>
                    <Text style={styles.passwordTitle}>PASSWORD REQUIREMENTS</Text>
                    {passwordRules.map((rule) => {
                      const passed = rule.test(password);
                      return (
                        <Text
                          key={rule.label}
                          style={[
                            styles.passwordRule,
                            passed && styles.passwordRulePassed,
                          ]}
                        >
                          {passed ? "✓" : "○"} {rule.label}
                        </Text>
                      );
                    })}
                  </View>
                ) : null}

                <Text style={styles.label}>Confirm new password</Text>
                <TextInput
                  style={[
                    styles.input,
                    confirmation && !passwordsMatch && styles.inputError,
                  ]}
                  value={confirmation}
                  onChangeText={setConfirmation}
                  secureTextEntry
                  autoComplete="new-password"
                  textContentType="newPassword"
                  placeholder="Repeat your new password"
                  placeholderTextColor="#8C806E"
                  editable={!busy}
                  returnKeyType="go"
                  onSubmitEditing={() => void handleSubmit()}
                />

                {confirmation && !passwordsMatch ? (
                  <Text style={styles.fieldError}>
                    Passwords do not match.
                  </Text>
                ) : null}

                <Pressable
                  accessibilityRole="button"
                  style={[
                    styles.primaryButton,
                    (busy ||
                      !token.trim() ||
                      !strongPassword ||
                      !passwordsMatch) &&
                      styles.disabledButton,
                  ]}
                  onPress={() => void handleSubmit()}
                  disabled={
                    busy ||
                    !token.trim() ||
                    !strongPassword ||
                    !passwordsMatch
                  }
                >
                  <Text style={styles.primaryButtonText}>
                    {busy ? "Updating password…" : "Reset password"}
                  </Text>
                </Pressable>

                <View style={styles.footer}>
                  <Text style={styles.footerText}>Need a new reset link?</Text>
                  <Link href="/forgot-password" asChild>
                    <Pressable accessibilityRole="link">
                      <Text style={styles.link}>Request one</Text>
                    </Pressable>
                  </Link>
                </View>
              </>
            )}

            {successMessage ? (
              <Link href="/login" asChild>
                <Pressable style={styles.primaryButton} accessibilityRole="button">
                  <Text style={styles.primaryButtonText}>Return to sign in</Text>
                </Pressable>
              </Link>
            ) : (
              <Link href="/login" asChild>
                <Pressable style={styles.backButton} accessibilityRole="link">
                  <Text style={styles.backText}>Back to sign in</Text>
                </Pressable>
              </Link>
            )}
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
  content: { width: "100%", maxWidth: 480, alignSelf: "center" },
  eyebrow: { marginBottom: 8, color: "#B98626", fontSize: 10, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: "#191410", fontSize: 30, fontWeight: "800" },
  description: { marginTop: 9, marginBottom: 18, color: "#5C5347", fontSize: 14, lineHeight: 21 },
  label: { marginTop: 14, marginBottom: 7, color: "#191410", fontSize: 13, fontWeight: "700" },
  input: {minHeight: 48, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, backgroundColor: "#FFFFFF", paddingHorizontal: 13, color: "#191410", fontSize: 15,},
  inputError: { borderColor: "#C24A3A" },
  fieldError: { marginTop: 5, color: "#C24A3A", fontSize: 12 },
  passwordCard: { marginTop: 9, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 9, backgroundColor: "#FBF8F2", padding: 12 },
  passwordTitle: { marginBottom: 5, color: "#5C5347", fontSize: 10, fontWeight: "800", letterSpacing: 0.8 },
  passwordRule: { marginTop: 4, color: "#8C806E", fontSize: 12 },
  passwordRulePassed: { color: "#1E9D63", fontWeight: "700" },
  errorNotice: { marginTop: 12, borderRadius: 8, backgroundColor: "#F9E5DF", padding: 12 },
  errorText: { color: "#C24A3A", fontSize: 13, lineHeight: 19 },
  successNotice: { marginTop: 15, borderRadius: 8, backgroundColor: "#E4F5EC", padding: 13 },
  successText: { color: "#1E9D63", fontSize: 13, lineHeight: 19 },
  primaryButton: { minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 20, borderRadius: 8, backgroundColor: "#D9A441", paddingHorizontal: 16 },
  disabledButton: { opacity: 0.5 },
  primaryButtonText: { color: "#080D18", fontSize: 14, fontWeight: "800" },
  footer: { flexDirection: "row", justifyContent: "center", gap: 5, marginTop: 22 },
  footerText: { color: "#5C5347", fontSize: 12 },
  link: { color: "#B98626", fontSize: 12, fontWeight: "800" },
  backButton: { alignItems: "center", paddingVertical: 16 },
  backText: { color: "#8C806E", fontSize: 12, fontWeight: "700" },
});