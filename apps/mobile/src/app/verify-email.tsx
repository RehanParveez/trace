import { useEffect, useRef, useState } from "react";
import {KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { resendVerification, verifyEmail } from "../api/client";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function VerifyEmailScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

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
    if (routeToken) setToken(routeToken);
    if (routeEmail) setEmail(routeEmail);
  }, [routeToken, routeEmail]);

  async function handleVerify(tokenValue = token) {
    const normalizedToken = tokenValue.trim();

    if (!normalizedToken || action) return;

    setAction("verify");
    setError("");
    setMessage("");

    try {
      const result = await verifyEmail(normalizedToken);
      setMessage(result.message || t("verifyEmail.success"));
      setVerified(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("verifyEmail.failure"),
      );
    } finally {
      setAction(null);
    }
  }

  useEffect(() => {
    if (!routeToken || automaticAttemptMade.current) return;

    automaticAttemptMade.current = true;
    void handleVerify(routeToken);
  }, [routeToken]);

  async function handleResend() {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || action) return;

    setAction("resend");
    setError("");
    setMessage("");

    try {
      const result = await resendVerification(normalizedEmail);
      setMessage(result.message || t("verifyEmail.resendSuccess"));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("verifyEmail.resendFailure"),
      );
    } finally {
      setAction(null);
    }
  }

  return (
    <SafeAreaView style={styles.screen} edges={["top", "bottom"]}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      <KeyboardAvoidingView
        style={styles.keyboard}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.content}>
            <View style={[styles.topRow, isUrdu && styles.rtlRow]}>
              <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
                {t("verifyEmail.eyebrow")}
              </Text>
              <LanguageSwitcher />
            </View>

            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {verified
                ? t("verifyEmail.verifiedTitle")
                : t("verifyEmail.title")}
            </Text>
            <Text style={[styles.description, isUrdu && styles.rtlText]}>
              {verified
                ? t("verifyEmail.verifiedDescription")
                : t("verifyEmail.description")}
            </Text>

            {error ? (
              <View style={styles.errorNotice} accessibilityRole="alert">
                <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
                  {error}
                </Text>
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
                <Text
                  style={[
                    styles.messageText,
                    verified && styles.successText,
                    isUrdu && styles.rtlText,
                  ]}
                >
                  {message}
                </Text>
              </View>
            ) : null}

            {!verified ? (
              <>
                <Text style={[styles.label, isUrdu && styles.rtlText]}>
                  {t("verifyEmail.tokenLabel")}
                </Text>
                <TextInput
                  style={[styles.input, isUrdu && styles.rtlText]}
                  value={token}
                  onChangeText={setToken}
                  autoCapitalize="none"
                  autoCorrect={false}
                  multiline
                  placeholder={t("verifyEmail.tokenPlaceholder")}
                  placeholderTextColor={COLORS.muted}
                  editable={action === null}
                  accessibilityLabel={t("verifyEmail.tokenLabel")}
                  textAlign={isUrdu ? "right" : "left"}
                />

                <Pressable
                  accessibilityRole="button"
                  style={[
                    styles.primaryButton,
                    (!token.trim() || action !== null) &&
                      styles.disabledButton,
                  ]}
                  onPress={() => void handleVerify()}
                  disabled={!token.trim() || action !== null}
                >
                  <Text
                    style={[
                      styles.primaryButtonText,
                      isUrdu && styles.rtlText,
                    ]}
                  >
                    {action === "verify"
                      ? t("verifyEmail.verifying")
                      : t("verifyEmail.verify")}
                  </Text>
                </Pressable>

                <Text
                  style={[
                    styles.label,
                    styles.resendHeading,
                    isUrdu && styles.rtlText,
                  ]}
                >
                  {t("verifyEmail.needAnotherEmail")}
                </Text>
                <TextInput
                  style={[styles.input, isUrdu && styles.rtlText]}
                  value={email}
                  onChangeText={setEmail}
                  placeholder={t("verifyEmail.emailPlaceholder")}
                  placeholderTextColor={COLORS.muted}
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="email"
                  textContentType="emailAddress"
                  keyboardType="email-address"
                  editable={action === null}
                  accessibilityLabel={t("verifyEmail.resendEmailLabel")}
                  textAlign={isUrdu ? "right" : "left"}
                />

                <Pressable
                  accessibilityRole="button"
                  style={[
                    styles.secondaryButton,
                    (!email.trim() || action !== null) &&
                      styles.disabledButton,
                  ]}
                  onPress={() => void handleResend()}
                  disabled={!email.trim() || action !== null}
                >
                  <Text
                    style={[
                      styles.secondaryButtonText,
                      isUrdu && styles.rtlText,
                    ]}
                  >
                    {action === "resend"
                      ? t("verifyEmail.sending")
                      : t("verifyEmail.resend")}
                  </Text>
                </Pressable>
              </>
            ) : (
              <Link href="/login" asChild>
                <Pressable
                  style={styles.primaryButton}
                  accessibilityRole="button"
                >
                  <Text
                    style={[
                      styles.primaryButtonText,
                      isUrdu && styles.rtlText,
                    ]}
                  >
                    {t("verifyEmail.continueToSignIn")}
                  </Text>
                </Pressable>
              </Link>
            )}

            <Link href="/login" asChild>
              <Pressable style={styles.backButton} accessibilityRole="link">
                <Text style={[styles.backText, isUrdu && styles.rtlText]}>
                  {t("verifyEmail.backToSignIn")}
                </Text>
              </Pressable>
            </Link>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  text: "#191410",
  secondary: "#5C5347",
  muted: "#8C806E",
  border: "#E4D9C4",
  gold: "#B98626",
  goldButton: "#D9A441",
  navy: "#080D18",
  blue: "#3B7DC4",
  blueBackground: "#E7F0FA",
  red: "#C24A3A",
  redBackground: "#F9E5DF",
  green: "#1E8055",
  greenBackground: "#E4F5EC",
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background },
  keyboard: { flex: 1 },
  scrollContent: { flexGrow: 1, justifyContent: "center", padding: 22 },
  content: { width: "100%", maxWidth: 480, alignSelf: "center" },
  topRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 12 },
  rtlRow: { flexDirection: "row-reverse" },
  eyebrow: { marginBottom: 8, color: COLORS.gold, fontSize: 10, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: COLORS.text, fontSize: 29, fontWeight: "800" },
  description: { marginTop: 9, marginBottom: 20, color: COLORS.secondary, fontSize: 14, lineHeight: 21 },
  label: { marginBottom: 7, color: COLORS.text, fontSize: 13, fontWeight: "700" },
  input: { minHeight: 48, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 13, paddingVertical: 12, color: COLORS.text, fontSize: 14 },
  primaryButton: { minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 16, borderRadius: 10, backgroundColor: COLORS.goldButton, paddingHorizontal: 14 },
  primaryButtonText: { color: COLORS.navy, fontSize: 14, fontWeight: "800", textAlign: "center" },
  secondaryButton: { minHeight: 48, alignItems: "center", justifyContent: "center", marginTop: 11, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 14 },
  secondaryButtonText: { color: COLORS.text, fontSize: 13, fontWeight: "700", textAlign: "center" },
  disabledButton: { opacity: 0.5 },
  resendHeading: { marginTop: 24 },
  errorNotice: { marginBottom: 12, borderWidth: 1, borderColor: "rgba(194,74,58,0.25)", borderRadius: 10, backgroundColor: COLORS.redBackground, padding: 12 },
  errorText: { color: COLORS.red, fontSize: 13, lineHeight: 19 },
  messageNotice: { marginBottom: 12, borderWidth: 1, borderColor: "rgba(59,125,196,0.25)", borderRadius: 10, backgroundColor: COLORS.blueBackground, padding: 12 },
  messageText: { color: COLORS.blue, fontSize: 13, lineHeight: 19 },
  successNotice: { borderColor: "#B7DDC7", backgroundColor: COLORS.greenBackground },
  successText: { color: COLORS.green },
  backButton: { alignItems: "center", paddingVertical: 16 },
  backText: { color: COLORS.muted, fontSize: 12, fontWeight: "700" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});