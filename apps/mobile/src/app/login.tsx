import { useEffect, useState } from "react";
import {ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { restoreSession, signIn } from "../api/client";

export default function LoginScreen() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function checkSession() {
    setCheckingSession(true);
    setError("");

    try {
      const user = await restoreSession();

      if (user) {
        router.replace("/projects");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not connect to Trace.",
      );
    } finally {
      setCheckingSession(false);
    }
  }

  useEffect(() => {
    void checkSession();
  }, []);

  async function handleSignIn() {
    if (busy || !email.trim() || !password) {
      return;
    }

    setBusy(true);
    setError("");

    try {
      await signIn(email.trim().toLowerCase(), password);
      setPassword("");
      router.replace("/projects");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  if (checkingSession) {
    return (
      <SafeAreaView style={styles.loading}>
        <StatusBar barStyle="dark-content" backgroundColor="#F3EEE4" />
        <ActivityIndicator size="large" color="#B98626" />
        <Text style={styles.loadingText}>Connecting to Trace…</Text>
      </SafeAreaView>
    );
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
            <View style={styles.brandRow}>
              <View style={styles.brandMark}>
                <Text style={styles.brandMarkText}>T</Text>
              </View>
              <Text style={styles.brand}>Trace</Text>
            </View>

            <Text style={styles.eyebrow}>WORKSPACE ACCESS</Text>
            <Text style={styles.title}>Welcome back.</Text>
            <Text style={styles.description}>
              Sign in to your Trace workspace to continue managing projects and
              site progress.
            </Text>

            {error ? (
              <View style={styles.errorNotice} accessibilityRole="alert">
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

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
              keyboardType="email-address"
              textContentType="emailAddress"
              returnKeyType="next"
              editable={!busy}
              accessibilityLabel="Work email"
            />

            <View style={styles.passwordHeading}>
              <Text style={styles.label}>Password</Text>
              <Link href="/forgot-password" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={styles.forgotLink}>Forgot password?</Text>
                </Pressable>
              </Link>
            </View>

            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="Enter your password"
              placeholderTextColor="#8C806E"
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="current-password"
              secureTextEntry
              textContentType="password"
              returnKeyType="go"
              onSubmitEditing={() => void handleSignIn()}
              editable={!busy}
              accessibilityLabel="Password"
            />

            <Pressable
              accessibilityRole="button"
              style={[
                styles.primaryButton,
                (busy || !email.trim() || !password) && styles.disabledButton,
              ]}
              onPress={() => void handleSignIn()}
              disabled={busy || !email.trim() || !password}
            >
              <Text style={styles.primaryButtonText}>
                {busy ? "Signing in…" : "Sign in to Trace"}
              </Text>
            </Pressable>

            {error ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => void checkSession()}
                disabled={checkingSession}
                style={styles.retryButton}
              >
                <Text style={styles.retryText}>Retry connection</Text>
              </Pressable>
            ) : null}

            <View style={styles.footer}>
              <Text style={styles.footerText}>New to Trace?</Text>
              <Link href="/register" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={styles.createLink}>Create an account</Text>
                </Pressable>
              </Link>
            </View>

            <Link href="/" asChild>
              <Pressable accessibilityRole="link" style={styles.backLink}>
                <Text style={styles.backLinkText}>Back to Trace</Text>
              </Pressable>
            </Link>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1, backgroundColor: "#F3EEE4",},
  keyboard: {flex: 1,},
  loading: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F3EEE4",},
  loadingText: {color: "#5C5347", fontSize: 14,},
  scrollContent: {flexGrow: 1, justifyContent: "center", paddingHorizontal: 22, paddingVertical: 28,},
  content: {width: "100%", maxWidth: 480, alignSelf: "center",},
  brandRow: {flexDirection: "row", alignItems: "center", gap: 11, marginBottom: 32,},
  brandMark: {width: 38, height: 38, alignItems: "center", justifyContent: "center", borderRadius: 10, backgroundColor: "#080D18",},
  brandMarkText: {color: "#D9A441", fontSize: 21, fontWeight: "900",},
  brand: {color: "#080D18", fontSize: 20, fontWeight: "800",},
  eyebrow: {marginBottom: 8, color: "#B98626", fontSize: 10, fontWeight: "800", letterSpacing: 1.3,},
  title: {color: "#191410", fontSize: 34, fontWeight: "800", letterSpacing: -0.5,},
  description: {marginTop: 9, marginBottom: 24, color: "#5C5347", fontSize: 14, lineHeight: 21,},
  errorNotice: {marginBottom: 12, borderWidth: 1, borderColor: "rgba(194, 74, 58, 0.25)", borderRadius: 8, backgroundColor: "#F9E5DF", paddingHorizontal: 13, paddingVertical: 11,},
  errorText: {color: "#C24A3A", fontSize: 13, lineHeight: 19,},
  label: {color: "#191410", fontSize: 13, fontWeight: "700",},
  passwordHeading: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 18, marginBottom: 8,},
  forgotLink: {color: "#B98626", fontSize: 12, fontWeight: "700",},
  input: {minHeight: 48, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, backgroundColor: "#FFFFFF", paddingHorizontal: 13, color: "#191410", fontSize: 15,},
  primaryButton: {minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 22, borderRadius: 8, backgroundColor: "#D9A441", paddingHorizontal: 16,},
  disabledButton: {opacity: 0.55,},
  primaryButtonText: {color: "#080D18", fontSize: 14, fontWeight: "800",},
  retryButton: {alignItems: "center", paddingVertical: 13,},
  retryText: {color: "#B98626", fontSize: 13, fontWeight: "700",},
  footer: {flexDirection: "row", justifyContent: "center", gap: 5, marginTop: 25,},
  footerText: {color: "#5C5347", fontSize: 12,},
  createLink: {color: "#B98626", fontSize: 12, fontWeight: "800",},
  backLink: {alignItems: "center", paddingVertical: 15,},
  backLinkText: {color: "#8C806E", fontSize: 12, fontWeight: "600",},
});