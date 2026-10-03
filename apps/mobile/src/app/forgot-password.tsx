import { useState } from "react";
import {KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link } from "expo-router";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { forgotPassword } from "../api/client";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function ForgotPasswordScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit() {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || busy) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      await forgotPassword(normalizedEmail);
      setMessage(t("forgotPassword.success"));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("forgotPassword.requestFailure"),
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
        >
          <View style={styles.content}>
            <View style={[styles.topRow, isUrdu && styles.rtlRow]}>
              <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
                {t("forgotPassword.eyebrow")}
              </Text>
              <LanguageSwitcher />
            </View>

            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("forgotPassword.title")}
            </Text>
            <Text style={[styles.description, isUrdu && styles.rtlText]}>
              {t("forgotPassword.description")}
            </Text>

            {error ? (
              <View style={styles.errorNotice} accessibilityRole="alert">
                <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
                  {error}
                </Text>
              </View>
            ) : null}

            {message ? (
              <View style={styles.successNotice} accessibilityRole="alert">
                <Text style={[styles.successText, isUrdu && styles.rtlText]}>
                  {message}
                </Text>
              </View>
            ) : null}

            {!message ? (
              <>
                <Text style={[styles.label, isUrdu && styles.rtlText]}>
                  {t("forgotPassword.emailLabel")}
                </Text>
                <TextInput
                  style={[styles.input, isUrdu && styles.rtlText]}
                  value={email}
                  onChangeText={setEmail}
                  placeholder={t("forgotPassword.emailPlaceholder")}
                  placeholderTextColor={COLORS.muted}
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="email"
                  textContentType="emailAddress"
                  keyboardType="email-address"
                  returnKeyType="send"
                  onSubmitEditing={() => void handleSubmit()}
                  editable={!busy}
                  accessibilityLabel={t("forgotPassword.emailLabel")}
                  textAlign={isUrdu ? "right" : "left"}
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
                  <Text
                    style={[
                      styles.primaryButtonText,
                      isUrdu && styles.rtlText,
                    ]}
                  >
                    {busy
                      ? t("forgotPassword.sending")
                      : t("forgotPassword.sendInstructions")}
                  </Text>
                </Pressable>
              </>
            ) : null}

            <View style={[styles.footer, isUrdu && styles.rtlRow]}>
              <Text style={[styles.footerText, isUrdu && styles.rtlText]}>
                {t("forgotPassword.rememberPassword")}
              </Text>
              <Link href="/login" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={[styles.link, isUrdu && styles.rtlText]}>
                    {t("forgotPassword.returnToSignIn")}
                  </Text>
                </Pressable>
              </Link>
            </View>
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
  green: "#1E8055",
  greenBackground: "#E4F5EC",
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background },
  keyboard: { flex: 1 },
  scrollContent: { flexGrow: 1, justifyContent: "center", padding: 22 },
  content: { width: "100%", maxWidth: 460, alignSelf: "center" },
  topRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 8 },
  rtlRow: { flexDirection: "row-reverse" },
  eyebrow: { color: COLORS.gold, fontSize: 10, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: COLORS.text, fontSize: 29, fontWeight: "800" },
  description: { marginTop: 9, marginBottom: 22, color: COLORS.secondary, fontSize: 14, lineHeight: 21 },
  label: { marginBottom: 7, color: COLORS.text, fontSize: 13, fontWeight: "700" },
  input: { minHeight: 48, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 13, color: COLORS.text, fontSize: 15 },
  primaryButton: { minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 18, borderRadius: 10, backgroundColor: COLORS.goldButton, paddingHorizontal: 16 },
  disabledButton: { opacity: 0.5 },
  primaryButtonText: { color: COLORS.navy, fontSize: 14, fontWeight: "800", textAlign: "center" },
  errorNotice: { marginBottom: 14, borderWidth: 1, borderColor: "#E9B8AC", borderRadius: 10, backgroundColor: COLORS.redBackground, padding: 12 },
  errorText: { color: COLORS.red, fontSize: 13, lineHeight: 19 },
  successNotice: { borderWidth: 1, borderColor: "#B7DDC7", borderRadius: 10, backgroundColor: COLORS.greenBackground, padding: 13 },
  successText: { color: COLORS.green, fontSize: 13, lineHeight: 19 },
  footer: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", gap: 5, marginTop: 24 },
  footerText: { color: COLORS.secondary, fontSize: 12 },
  link: { color: COLORS.gold, fontSize: 12, fontWeight: "800" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});