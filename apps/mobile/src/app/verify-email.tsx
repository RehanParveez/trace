import { useEffect, useRef, useState } from "react";
import {KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link, useLocalSearchParams } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { resendVerification, verifyEmail } from "../api/client";

export default function VerifyEmailScreen() {
  const params = useLocalSearchParams<{
    token?: string | string[];
    email?: string | string[];
  }>();

  const routeToken = Array.isArray(params.token)
    ? params.token[0] ?? ""
    : params.token ?? "";
  const routeEmail = Array.isArray(params.email)
    ? params.email[0] ?? ""
    : params.email ?? "";

  const [token, setToken] = useState(routeToken);
  const [email, setEmail] = useState(routeEmail);
  const [action, setAction] = useState<"verify" | "resend" | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [verified, setVerified] = useState(false);
  const automaticAttemptMade = useRef(false);

  useEffect(() => {
    if (routeToken) {
      setToken(routeToken);
    }
    if (routeEmail) {
      setEmail(routeEmail);
    }
  }, [routeToken, routeEmail]);

  async function handleVerify(tokenValue = token) {
    const normalizedToken = tokenValue.trim();

    if (!normalizedToken || action) {
      return;
    }

    setAction("verify");
    setError("");
    setMessage("");

    try {
      const result = await verifyEmail(normalizedToken);
      setMessage(result.message || "Your email has been verified.");
      setVerified(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Email verification failed. Check the link and try again.",
      );
    } finally {
      setAction(null);
    }
  }

  useEffect(() => {
    if (!routeToken || automaticAttemptMade.current) {
      return;
    }

    automaticAttemptMade.current = true;
    void handleVerify(routeToken);
  }, [routeToken]);

  async function handleResend() {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || action) {
      return;
    }

    setAction("resend");
    setError("");
    setMessage("");

    try {
      const result = await resendVerification(normalizedEmail);
      setMessage(
        result.message || "A new verification email has been sent.",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not resend the verification email.",
      );
    } finally {
      setAction(null);
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
            <Text style={styles.eyebrow}>EMAIL VERIFICATION</Text>
            <Text style={styles.title}>
              {verified ? "Email verified." : "Verify your email."}
            </Text>
            <Text style={styles.description}>
              {verified
                ? "Your email is confirmed. You can now sign in to Trace."
                : "Open the verification link from your email, or paste its token below."}
            </Text>

            {error ? (
              <View style={styles.errorNotice} accessibilityRole="alert">
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            {message ? (
              <View
                style={[
                  styles.messageNotice,
                  verified && styles.successNotice,
                ]}
                accessibilityRole="alert"
              >
                <Text style={[styles.messageText, verified && styles.successText]}>
                  {message}
                </Text>
              </View>
            ) : null}

            {!verified ? (
              <>
                <Text style={styles.label}>Verification token</Text>
                <TextInput
                  style={styles.input}
                  value={token}
                  onChangeText={setToken}
                  autoCapitalize="none"
                  autoCorrect={false}
                  multiline
                  placeholder="Paste the token from your email"
                  placeholderTextColor="#8C806E"
                  editable={action === null}
                  accessibilityLabel="Verification token"
                />

                <Pressable
                  accessibilityRole="button"
                  style={[
                    styles.primaryButton,
                    (!token.trim() || action !== null) && styles.disabledButton,
                  ]}
                  onPress={() => void handleVerify()}
                  disabled={!token.trim() || action !== null}
                >
                  <Text style={styles.primaryButtonText}>
                    {action === "verify" ? "Verifying…" : "Verify email"}
                  </Text>
                </Pressable>

                <Text style={[styles.label, styles.resendHeading]}>
                  Need another verification email?
                </Text>
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
                  editable={action === null}
                  accessibilityLabel="Email address for verification resend"
                />

                <Pressable
                  accessibilityRole="button"
                  style={[
                    styles.secondaryButton,
                    (!email.trim() || action !== null) && styles.disabledButton,
                  ]}
                  onPress={() => void handleResend()}
                  disabled={!email.trim() || action !== null}
                >
                  <Text style={styles.secondaryButtonText}>
                    {action === "resend" ? "Sending…" : "Resend verification email"}
                  </Text>
                </Pressable>
              </>
            ) : (
              <Link href="/login" asChild>
                <Pressable style={styles.primaryButton} accessibilityRole="button">
                  <Text style={styles.primaryButtonText}>Continue to sign in</Text>
                </Pressable>
              </Link>
            )}

            <Link href="/login" asChild>
              <Pressable style={styles.backButton} accessibilityRole="link">
                <Text style={styles.backText}>Back to sign in</Text>
              </Pressable>
            </Link>
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
  description: { marginTop: 9, marginBottom: 20, color: "#5C5347", fontSize: 14, lineHeight: 21 },
  label: { marginBottom: 7, color: "#191410", fontSize: 13, fontWeight: "700" },
  input: {minHeight: 48, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, backgroundColor: "#FFFFFF", paddingHorizontal: 13, paddingVertical: 12,color: "#191410", fontSize: 14,},
  primaryButton: { minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 16, borderRadius: 8, backgroundColor: "#D9A441", paddingHorizontal: 14 },
  primaryButtonText: { color: "#080D18", fontSize: 14, fontWeight: "800", textAlign: "center" },
  secondaryButton: { minHeight: 48, alignItems: "center", justifyContent: "center", marginTop: 11, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, backgroundColor: "#FFFFFF", paddingHorizontal: 14 },
  secondaryButtonText: { color: "#191410", fontSize: 13, fontWeight: "700", textAlign: "center" },
  disabledButton: { opacity: 0.5 },
  resendHeading: { marginTop: 24 },
  errorNotice: { marginBottom: 12, borderRadius: 8, backgroundColor: "#F9E5DF", padding: 12 },
  errorText: { color: "#C24A3A", fontSize: 13, lineHeight: 19 },
  messageNotice: { marginBottom: 12, borderRadius: 8, backgroundColor: "#E7F0FA", padding: 12 },
  messageText: { color: "#3B7DC4", fontSize: 13, lineHeight: 19 },
  successNotice: { backgroundColor: "#E4F5EC" },
  successText: { color: "#1E9D63" },
  backButton: { alignItems: "center", paddingVertical: 16 },
  backText: { color: "#8C806E", fontSize: 12, fontWeight: "700" },
});