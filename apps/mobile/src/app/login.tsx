import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Link, router } from "expo-router";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { restoreSession, signIn } from "../api/client";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function LoginScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [checkingSession, setCheckingSession] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const checkSession = useCallback(async () => {
    setCheckingSession(true);
    setError("");

    try {
      const user = await restoreSession();

      if (user) {
        router.replace("/projects");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("login.connectionFailure"),
      );
    } finally {
      setCheckingSession(false);
    }
  }, [t]);

  useEffect(() => {
    void checkSession();
  }, [checkSession]);

  async function handleSignIn() {
    if (busy || !email.trim() || !password) return;

    setBusy(true);
    setError("");

    try {
      await signIn(email.trim().toLowerCase(), password);
      setPassword("");
      router.replace("/projects");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("login.signInFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  if (checkingSession) {
    return (
      <SafeAreaView style={styles.loading} edges={["top", "bottom"]}>
        <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
        <View style={styles.loadingSwitcher}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.gold} />
        <Text style={[styles.loadingText, isUrdu && styles.rtlText]}>
          {t("login.connecting")}
        </Text>
      </SafeAreaView>
    );
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
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.content}>
            <View style={[styles.topRow, isUrdu && styles.rtlRow]}>
              <View style={[styles.brandRow, isUrdu && styles.rtlRow]}>
                <View style={styles.brandMark}>
                  <Text style={styles.brandMarkText}>T</Text>
                </View>
                <Text style={[styles.brand, isUrdu && styles.rtlText]}>
                  {t("login.brand")}
                </Text>
              </View>
              <LanguageSwitcher />
            </View>

            <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
              {t("login.eyebrow")}
            </Text>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("login.title")}
            </Text>
            <Text style={[styles.description, isUrdu && styles.rtlText]}>
              {t("login.description")}
            </Text>

            {error ? (
              <View style={styles.errorNotice} accessibilityRole="alert">
                <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
                  {error}
                </Text>
              </View>
            ) : null}

            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("login.email")}
            </Text>
            <TextInput
              style={[styles.input, isUrdu && styles.rtlText]}
              value={email}
              onChangeText={setEmail}
              placeholder={t("login.emailPlaceholder")}
              placeholderTextColor={COLORS.muted}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              keyboardType="email-address"
              textContentType="emailAddress"
              returnKeyType="next"
              editable={!busy}
              accessibilityLabel={t("login.email")}
              textAlign={isUrdu ? "right" : "left"}
            />

            <View style={[styles.passwordHeading, isUrdu && styles.rtlRow]}>
              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("login.password")}
              </Text>
              <Link href="/forgot-password" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={[styles.forgotLink, isUrdu && styles.rtlText]}>
                    {t("login.forgotPassword")}
                  </Text>
                </Pressable>
              </Link>
            </View>

            <TextInput
              style={[styles.input, isUrdu && styles.rtlText]}
              value={password}
              onChangeText={setPassword}
              placeholder={t("login.passwordPlaceholder")}
              placeholderTextColor={COLORS.muted}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="current-password"
              secureTextEntry
              textContentType="password"
              returnKeyType="go"
              onSubmitEditing={() => void handleSignIn()}
              editable={!busy}
              accessibilityLabel={t("login.password")}
              textAlign={isUrdu ? "right" : "left"}
            />

            <Pressable
              accessibilityRole="button"
              style={[
                styles.primaryButton,
                (busy || !email.trim() || !password) &&
                  styles.disabledButton,
              ]}
              onPress={() => void handleSignIn()}
              disabled={busy || !email.trim() || !password}
            >
              <Text
                style={[
                  styles.primaryButtonText,
                  isUrdu && styles.rtlText,
                ]}
              >
                {busy ? t("login.signingIn") : t("login.signIn")}
              </Text>
            </Pressable>

            {error ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => void checkSession()}
                disabled={checkingSession}
                style={styles.retryButton}
              >
                <Text style={[styles.retryText, isUrdu && styles.rtlText]}>
                  {t("login.retryConnection")}
                </Text>
              </Pressable>
            ) : null}

            <View style={[styles.footer, isUrdu && styles.rtlRow]}>
              <Text style={[styles.footerText, isUrdu && styles.rtlText]}>
                {t("login.newToTrace")}
              </Text>
              <Link href="/register" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={[styles.createLink, isUrdu && styles.rtlText]}>
                    {t("login.createAccount")}
                  </Text>
                </Pressable>
              </Link>
            </View>

            <Link href="/" asChild>
              <Pressable accessibilityRole="link" style={styles.backLink}>
                <Text style={[styles.backLinkText, isUrdu && styles.rtlText]}>
                  {t("login.backToTrace")}
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
  red: "#C24A3A",
  redBackground: "#F9E5DF",
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background },
  keyboard: { flex: 1 },
  loading: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: COLORS.background, padding: 22 },
  loadingSwitcher: { position: "absolute", top: 14, right: 20 },
  loadingText: { color: COLORS.secondary, fontSize: 14 },
  scrollContent: { flexGrow: 1, justifyContent: "center", paddingHorizontal: 22, paddingVertical: 28 },
  content: { width: "100%", maxWidth: 480, alignSelf: "center" },
  topRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 32 },
  rtlRow: { flexDirection: "row-reverse" },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 11 },
  brandMark: { width: 38, height: 38, alignItems: "center", justifyContent: "center", borderRadius: 10, backgroundColor: COLORS.navy },
  brandMarkText: { color: COLORS.goldButton, fontSize: 21, fontWeight: "900" },
  brand: { color: COLORS.navy, fontSize: 20, fontWeight: "800" },
  eyebrow: { marginBottom: 8, color: COLORS.gold, fontSize: 10, fontWeight: "800", letterSpacing: 1.3 },
  title: { color: COLORS.text, fontSize: 33, fontWeight: "800", letterSpacing: -0.5 },
  description: { marginTop: 9, marginBottom: 24, color: COLORS.secondary, fontSize: 14, lineHeight: 21 },
  errorNotice: { marginBottom: 12, borderWidth: 1, borderColor: "rgba(194, 74, 58, 0.25)", borderRadius: 10, backgroundColor: COLORS.redBackground, paddingHorizontal: 13, paddingVertical: 11 },
  errorText: { color: COLORS.red, fontSize: 13, lineHeight: 19 },
  label: { color: COLORS.text, fontSize: 13, fontWeight: "700" },
  passwordHeading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, marginTop: 18, marginBottom: 8 },
  forgotLink: { color: COLORS.gold, fontSize: 12, fontWeight: "700" },
  input: { minHeight: 48, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 13, color: COLORS.text, fontSize: 15 },
  primaryButton: { minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 22, borderRadius: 10, backgroundColor: COLORS.goldButton, paddingHorizontal: 16 },
  disabledButton: { opacity: 0.55 },
  primaryButtonText: { color: COLORS.navy, fontSize: 14, fontWeight: "800", textAlign: "center" },
  retryButton: { alignItems: "center", paddingVertical: 13 },
  retryText: { color: COLORS.gold, fontSize: 13, fontWeight: "700" },
  footer: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", gap: 5, marginTop: 25 },
  footerText: { color: COLORS.secondary, fontSize: 12 },
  createLink: { color: COLORS.gold, fontSize: 12, fontWeight: "800" },
  backLink: { alignItems: "center", paddingVertical: 15 },
  backLinkText: { color: COLORS.muted, fontSize: 12, fontWeight: "600" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});