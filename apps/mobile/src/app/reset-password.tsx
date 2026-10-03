import { useEffect, useState } from "react";
import {KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { resetPassword } from "../api/client";
import LanguageSwitcher from "../components/LanguageSwitcher";

const commonPasswords = new Set([
  "password",
  "password123",
  "password123!",
  "admin123",
  "admin123!",
  "qwerty123",
  "12345678",
  "123456789",
  "1234567890",
]);

const passwordRules = [
  {
    key: "length",
    test: (value: string) => value.length >= 12 && value.length <= 128,
  },
  {
    key: "uppercase",
    test: (value: string) => /[A-Z]/.test(value),
  },
  {
    key: "lowercase",
    test: (value: string) => /[a-z]/.test(value),
  },
  {
    key: "number",
    test: (value: string) => /\d/.test(value),
  },
  {
    key: "symbol",
    test: (value: string) => /[^\w\s]/.test(value),
  },
  {
    key: "notCommon",
    test: (value: string) =>
      value.length > 0 && !commonPasswords.has(value.toLowerCase()),
  },
];

function passwordIsStrong(value: string) {
  return passwordRules.every((rule) => rule.test(value));
}

export default function ResetPasswordScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

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
    if (routeToken) setToken(routeToken);
  }, [routeToken]);

  const passwordsMatch = password === confirmation;
  const strongPassword = passwordIsStrong(password);

  async function handleSubmit() {
    if (busy) return;

    setError("");
    setSuccessMessage("");

    if (!token.trim()) {
      setError(t("resetPassword.tokenMissing"));
      return;
    }
    if (!strongPassword) {
      setError(t("resetPassword.requirementsError"));
      return;
    }
    if (!passwordsMatch) {
      setError(t("resetPassword.passwordMismatch"));
      return;
    }

    setBusy(true);

    try {
      const result = await resetPassword(
        token.trim(),
        password,
        confirmation,
      );
      setSuccessMessage(
        result.message || t("resetPassword.success"),
      );
      setPassword("");
      setConfirmation("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("resetPassword.failure"),
      );
    } finally {
      setBusy(false);
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
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.content}>
            <View style={[styles.topRow, isUrdu && styles.rtlRow]}>
              <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
                {t("resetPassword.eyebrow")}
              </Text>
              <LanguageSwitcher />
            </View>

            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {successMessage
                ? t("resetPassword.updatedTitle")
                : t("resetPassword.title")}
            </Text>

            {successMessage ? (
              <View style={styles.successNotice} accessibilityRole="alert">
                <Text style={[styles.successText, isUrdu && styles.rtlText]}>
                  {successMessage}
                </Text>
              </View>
            ) : (
              <>
                <Text style={[styles.description, isUrdu && styles.rtlText]}>
                  {t("resetPassword.description")}
                </Text>

                {!routeToken ? (
                  <>
                    <Text style={[styles.label, isUrdu && styles.rtlText]}>
                      {t("resetPassword.tokenLabel")}
                    </Text>
                    <TextInput
                      style={[styles.input, isUrdu && styles.rtlText]}
                      value={token}
                      onChangeText={setToken}
                      autoCapitalize="none"
                      autoCorrect={false}
                      placeholder={t("resetPassword.tokenPlaceholder")}
                      placeholderTextColor={COLORS.muted}
                      editable={!busy}
                      accessibilityLabel={t("resetPassword.tokenLabel")}
                      textAlign={isUrdu ? "right" : "left"}
                    />
                  </>
                ) : null}

                {error ? (
                  <View style={styles.errorNotice} accessibilityRole="alert">
                    <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
                      {error}
                    </Text>
                  </View>
                ) : null}

                <Text style={[styles.label, isUrdu && styles.rtlText]}>
                  {t("resetPassword.newPassword")}
                </Text>
                <TextInput
                  style={[styles.input, isUrdu && styles.rtlText]}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  autoComplete="new-password"
                  textContentType="newPassword"
                  placeholder={t("resetPassword.passwordPlaceholder")}
                  placeholderTextColor={COLORS.muted}
                  editable={!busy}
                  returnKeyType="next"
                  textAlign={isUrdu ? "right" : "left"}
                />

                {password ? (
                  <View style={styles.passwordCard}>
                    <Text
                      style={[styles.passwordTitle, isUrdu && styles.rtlText]}
                    >
                      {t("resetPassword.passwordRequirements")}
                    </Text>
                    {passwordRules.map((rule) => {
                      const passed = rule.test(password);

                      return (
                        <Text
                          key={rule.key}
                          style={[
                            styles.passwordRule,
                            passed && styles.passwordRulePassed,
                            isUrdu && styles.rtlText,
                          ]}
                        >
                          {passed ? "✓" : "○"}{" "}
                          {t(`resetPassword.rule.${rule.key}`)}
                        </Text>
                      );
                    })}
                  </View>
                ) : null}

                <Text style={[styles.label, isUrdu && styles.rtlText]}>
                  {t("resetPassword.confirmPassword")}
                </Text>
                <TextInput
                  style={[
                    styles.input,
                    confirmation && !passwordsMatch && styles.inputError,
                    isUrdu && styles.rtlText,
                  ]}
                  value={confirmation}
                  onChangeText={setConfirmation}
                  secureTextEntry
                  autoComplete="new-password"
                  textContentType="newPassword"
                  placeholder={t("resetPassword.confirmPlaceholder")}
                  placeholderTextColor={COLORS.muted}
                  editable={!busy}
                  returnKeyType="go"
                  onSubmitEditing={() => void handleSubmit()}
                  textAlign={isUrdu ? "right" : "left"}
                />

                {confirmation && !passwordsMatch ? (
                  <Text style={[styles.fieldError, isUrdu && styles.rtlText]}>
                    {t("resetPassword.passwordMismatch")}
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
                  <Text
                    style={[
                      styles.primaryButtonText,
                      isUrdu && styles.rtlText,
                    ]}
                  >
                    {busy
                      ? t("resetPassword.updating")
                      : t("resetPassword.submit")}
                  </Text>
                </Pressable>

                <View style={[styles.footer, isUrdu && styles.rtlRow]}>
                  <Text style={[styles.footerText, isUrdu && styles.rtlText]}>
                    {t("resetPassword.needNewLink")}
                  </Text>
                  <Link href="/forgot-password" asChild>
                    <Pressable accessibilityRole="link">
                      <Text style={[styles.link, isUrdu && styles.rtlText]}>
                        {t("resetPassword.requestLink")}
                      </Text>
                    </Pressable>
                  </Link>
                </View>
              </>
            )}

            {successMessage ? (
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
                    {t("resetPassword.returnToSignIn")}
                  </Text>
                </Pressable>
              </Link>
            ) : (
              <Link href="/login" asChild>
                <Pressable accessibilityRole="link" style={styles.backButton}>
                  <Text style={[styles.backText, isUrdu && styles.rtlText]}>
                    {t("resetPassword.backToSignIn")}
                  </Text>
                </Pressable>
              </Link>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#FBF8F2",
  text: "#191410",
  secondary: "#5C5347",
  muted: "#8C806E",
  border: "#E4D9C4",
  gold: "#B98626",
  goldButton: "#D9A441",
  navy: "#080D18",
  green: "#1E8055",
  greenBackground: "#E4F5EC",
  red: "#C24A3A",
  redBackground: "#F9E5DF",
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
  description: { marginTop: 9, marginBottom: 18, color: COLORS.secondary, fontSize: 14, lineHeight: 21 },
  label: { marginTop: 14, marginBottom: 7, color: COLORS.text, fontSize: 13, fontWeight: "700" },
  input: { minHeight: 48, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 13, color: COLORS.text, fontSize: 15 },
  inputError: { borderColor: COLORS.red },
  fieldError: { marginTop: 5, color: COLORS.red, fontSize: 12 },
  passwordCard: { marginTop: 9, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surfaceMuted, padding: 12 },
  passwordTitle: { marginBottom: 5, color: COLORS.secondary, fontSize: 10, fontWeight: "800", letterSpacing: 0.8 },
  passwordRule: { marginTop: 4, color: COLORS.muted, fontSize: 12 },
  passwordRulePassed: { color: COLORS.green, fontWeight: "700" },
  errorNotice: { marginTop: 12, borderWidth: 1, borderColor: "rgba(194,74,58,0.25)", borderRadius: 10, backgroundColor: COLORS.redBackground, padding: 12 },
  errorText: { color: COLORS.red, fontSize: 13, lineHeight: 19 },
  successNotice: { marginTop: 15, borderWidth: 1, borderColor: "#B7DDC7", borderRadius: 10, backgroundColor: COLORS.greenBackground, padding: 13 },
  successText: { color: COLORS.green, fontSize: 13, lineHeight: 19 },
  primaryButton: { minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 20, borderRadius: 10, backgroundColor: COLORS.goldButton, paddingHorizontal: 16 },
  disabledButton: { opacity: 0.5 },
  primaryButtonText: { color: COLORS.navy, fontSize: 14, fontWeight: "800", textAlign: "center" },
  footer: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", gap: 5, marginTop: 22 },
  footerText: { color: COLORS.secondary, fontSize: 12 },
  link: { color: COLORS.gold, fontSize: 12, fontWeight: "800" },
  backButton: { alignItems: "center", paddingVertical: 16 },
  backText: { color: COLORS.muted, fontSize: 12, fontWeight: "700" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});