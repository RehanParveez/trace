import { useEffect, useState } from "react";
import {ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, type TextInputProps, View,
} from "react-native";
import { Link, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { previewInvitation, register } from "../api/client";
import type { InvitationPreview } from "../api/types";
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

export default function RegisterScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const params = useLocalSearchParams<{ token?: string | string[] }>();
  const invitationToken = Array.isArray(params.token)
    ? params.token[0] ?? ""
    : params.token ?? "";

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");

  const [busy, setBusy] = useState(false);
  const [invitationLoading, setInvitationLoading] = useState(false);
  const [invitation, setInvitation] = useState<InvitationPreview | null>(null);
  const [invitationError, setInvitationError] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [verificationRequired, setVerificationRequired] = useState(true);
  const [registeredEmail, setRegisteredEmail] = useState("");

  useEffect(() => {
    if (!invitationToken) {
      setInvitation(null);
      setInvitationError("");
      setInvitationLoading(false);
      return;
    }

    let active = true;

    setInvitationLoading(true);
    setInvitationError("");
    setInvitation(null);

    previewInvitation(invitationToken)
      .then((result) => {
        if (!active) return;
        setInvitation(result);
        setEmail(result.email);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setInvitationError(
          err instanceof Error
            ? err.message
            : t("register.invitationFailure"),
        );
      })
      .finally(() => {
        if (active) setInvitationLoading(false);
      });

    return () => {
      active = false;
    };
  }, [invitationToken, t]);

  const passwordsMatch = password === confirmation;
  const strongPassword = passwordIsStrong(password);

  const canSubmit =
    !busy &&
    !invitationLoading &&
    (!invitationToken || Boolean(invitation)) &&
    Boolean(firstName.trim()) &&
    Boolean(lastName.trim()) &&
    Boolean(email.trim()) &&
    (Boolean(invitationToken) || Boolean(organizationName.trim())) &&
    strongPassword &&
    passwordsMatch;

  async function handleRegister() {
    if (!canSubmit) return;

    setBusy(true);
    setError("");

    const normalizedEmail = email.trim().toLowerCase();

    try {
      const result = await register({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: normalizedEmail,
        password,
        password_confirmation: confirmation,
        ...(invitationToken
          ? { invitation_token: invitationToken }
          : { organization_name: organizationName.trim() }),
      });

      setRegisteredEmail(normalizedEmail);
      setVerificationRequired(result.verification_required);
      setSuccessMessage(
        result.message || t("register.accountCreatedMessage"),
      );
      setPassword("");
      setConfirmation("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("register.failure"),
      );
    } finally {
      setBusy(false);
    }
  }

  if (successMessage) {
    return (
      <SafeAreaView style={styles.screen} edges={["top", "bottom"]}>
        <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
        <ScrollView
          contentContainerStyle={styles.successScroll}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.successContent}>
            <View style={[styles.successTopRow, isUrdu && styles.rtlRow]}>
              <View style={styles.brandMark}>
                <Text style={styles.brandMarkText}>T</Text>
              </View>
              <LanguageSwitcher />
            </View>

            <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
              {t("register.accountCreatedEyebrow")}
            </Text>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {verificationRequired
                ? t("register.checkEmailTitle")
                : t("register.allSetTitle")}
            </Text>
            <Text style={[styles.description, isUrdu && styles.rtlText]}>
              {successMessage}
            </Text>
            <Text
              style={[
                styles.emailNotice,
                isUrdu && styles.rtlText,
              ]}
            >
              {registeredEmail}
            </Text>

            {verificationRequired ? (
              <Link
                href={{
                  pathname: "/verify-email",
                  params: { email: registeredEmail },
                }}
                asChild
              >
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
                    {t("register.continueToVerification")}
                  </Text>
                </Pressable>
              </Link>
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
                    {t("register.continueToSignIn")}
                  </Text>
                </Pressable>
              </Link>
            )}
          </View>
        </ScrollView>
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
                  {t("register.brand")}
                </Text>
              </View>
              <LanguageSwitcher />
            </View>

            <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
              {t(
                invitationToken
                  ? "register.acceptInvitation"
                  : "register.createWorkspace",
              )}
            </Text>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("register.title")}
            </Text>
            <Text style={[styles.description, isUrdu && styles.rtlText]}>
              {t("register.description")}
            </Text>

            {invitationLoading ? (
              <View style={[styles.infoNotice, isUrdu && styles.rtlRow]}>
                <ActivityIndicator size="small" color={COLORS.info} />
                <Text style={[styles.infoText, isUrdu && styles.rtlText]}>
                  {t("register.checkingInvitation")}
                </Text>
              </View>
            ) : null}

            {invitation ? (
              <View style={styles.infoNotice}>
                <Text style={[styles.infoText, isUrdu && styles.rtlText]}>
                  {t("register.joiningOrganization", {
                    organization: invitation.organization_name,
                    role: invitation.role_name
                      ? t("register.asRole", {
                          role: invitation.role_name,
                        })
                      : "",
                  })}
                </Text>
              </View>
            ) : null}

            {invitationError ? (
              <View style={styles.errorNotice} accessibilityLiveRegion="polite">
                <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
                  {invitationError}
                </Text>
              </View>
            ) : null}

            {error ? (
              <View style={styles.errorNotice} accessibilityLiveRegion="polite">
                <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
                  {error}
                </Text>
              </View>
            ) : null}

            <Field
              label={t("register.firstName")}
              value={firstName}
              onChangeText={setFirstName}
              placeholder={t("register.firstNamePlaceholder")}
              autoComplete="given-name"
              textContentType="givenName"
              editable={!busy}
              returnKeyType="next"
              isUrdu={isUrdu}
            />

            <Field
              label={t("register.lastName")}
              value={lastName}
              onChangeText={setLastName}
              placeholder={t("register.lastNamePlaceholder")}
              autoComplete="family-name"
              textContentType="familyName"
              editable={!busy}
              returnKeyType="next"
              isUrdu={isUrdu}
            />

            <Field
              label={t("register.workEmail")}
              value={email}
              onChangeText={setEmail}
              placeholder={t("register.emailPlaceholder")}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              textContentType="emailAddress"
              keyboardType="email-address"
              editable={!busy && !invitationToken}
              returnKeyType="next"
              isUrdu={isUrdu}
            />

            {!invitationToken ? (
              <Field
                label={t("register.organizationName")}
                value={organizationName}
                onChangeText={setOrganizationName}
                placeholder={t("register.organizationPlaceholder")}
                editable={!busy}
                returnKeyType="next"
                isUrdu={isUrdu}
              />
            ) : null}

            <Field
              label={t("register.password")}
              value={password}
              onChangeText={setPassword}
              placeholder={t("register.passwordPlaceholder")}
              secureTextEntry
              autoComplete="new-password"
              textContentType="newPassword"
              editable={!busy}
              returnKeyType="next"
              isUrdu={isUrdu}
            />

            {password ? (
              <View style={styles.passwordCard}>
                <Text style={[styles.passwordTitle, isUrdu && styles.rtlText]}>
                  {t("register.passwordRequirements")}
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
                      {t(`register.passwordRule.${rule.key}`)}
                    </Text>
                  );
                })}
              </View>
            ) : null}

            <Field
              label={t("register.confirmPassword")}
              value={confirmation}
              onChangeText={setConfirmation}
              placeholder={t("register.confirmPasswordPlaceholder")}
              secureTextEntry
              autoComplete="new-password"
              textContentType="newPassword"
              editable={!busy}
              returnKeyType="go"
              onSubmitEditing={() => void handleRegister()}
              isUrdu={isUrdu}
              inputError={Boolean(confirmation && !passwordsMatch)}
            />

            {confirmation && !passwordsMatch ? (
              <Text style={[styles.fieldError, isUrdu && styles.rtlText]}>
                {t("register.passwordMismatch")}
              </Text>
            ) : null}

            <Pressable
              accessibilityRole="button"
              style={[
                styles.primaryButton,
                !canSubmit && styles.disabledButton,
              ]}
              onPress={() => void handleRegister()}
              disabled={!canSubmit}
            >
              <Text
                style={[
                  styles.primaryButtonText,
                  isUrdu && styles.rtlText,
                ]}
              >
                {busy
                  ? t("register.creating")
                  : t("register.createAccount")}
              </Text>
            </Pressable>

            <View style={[styles.footer, isUrdu && styles.rtlRow]}>
              <Text style={[styles.footerText, isUrdu && styles.rtlText]}>
                {t("register.alreadyHaveAccount")}
              </Text>
              <Link href="/login" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={[styles.link, isUrdu && styles.rtlText]}>
                    {t("register.signIn")}
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

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  autoCorrect?: boolean;
  autoComplete?: TextInputProps["autoComplete"];
  textContentType?: TextInputProps["textContentType"];
  keyboardType?: "default" | "email-address";
  secureTextEntry?: boolean;
  editable?: boolean;
  returnKeyType?: "next" | "go";
  onSubmitEditing?: () => void;
  inputError?: boolean;
  isUrdu: boolean;
}) {
  return (
    <>
      <Text style={[styles.label, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <TextInput
        style={[
          styles.input,
          props.inputError && styles.inputError,
          props.isUrdu && styles.rtlText,
        ]}
        value={props.value}
        onChangeText={props.onChangeText}
        placeholder={props.placeholder}
        placeholderTextColor={COLORS.muted}
        autoCapitalize={props.autoCapitalize ?? "sentences"}
        autoCorrect={props.autoCorrect}
        autoComplete={props.autoComplete}
        textContentType={props.textContentType as never}
        keyboardType={props.keyboardType ?? "default"}
        secureTextEntry={props.secureTextEntry}
        editable={props.editable}
        returnKeyType={props.returnKeyType}
        onSubmitEditing={props.onSubmitEditing}
        textAlign={props.isUrdu ? "right" : "left"}
      />
    </>
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
  red: "#C24A3A",
  redBackground: "#F9E5DF",
  info: "#3B7DC4",
  infoBackground: "#E7F0FA",
  infoBorder: "rgba(59,125,196,0.25)",
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background },
  keyboard: { flex: 1 },
  scrollContent: { flexGrow: 1, justifyContent: "center", padding: 22 },
  content: { width: "100%", maxWidth: 480, alignSelf: "center" },
  successScroll: { flexGrow: 1 },
  successContent: { flex: 1, justifyContent: "center", padding: 24 },
  topRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 25 },
  successTopRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 25 },
  rtlRow: { flexDirection: "row-reverse" },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  brandMark: { width: 38, height: 38, alignItems: "center", justifyContent: "center", borderRadius: 10, backgroundColor: COLORS.navy },
  brandMarkText: { color: COLORS.goldButton, fontSize: 21, fontWeight: "900" },
  brand: { color: COLORS.navy, fontSize: 20, fontWeight: "800" },
  eyebrow: { marginBottom: 7, color: COLORS.gold, fontSize: 10, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: COLORS.text, fontSize: 29, fontWeight: "800", lineHeight: 37 },
  description: { marginTop: 8, marginBottom: 19, color: COLORS.secondary, fontSize: 14, lineHeight: 21 },
  label: { marginTop: 13, marginBottom: 7, color: COLORS.text, fontSize: 13, fontWeight: "700" },
  input: { minHeight: 48, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 13, color: COLORS.text, fontSize: 15 },
  inputError: { borderColor: COLORS.red },
  fieldError: { marginTop: 5, color: COLORS.red, fontSize: 12 },
  passwordCard: { marginTop: 9, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surfaceMuted, padding: 12 },
  passwordTitle: { marginBottom: 5, color: COLORS.secondary, fontSize: 10, fontWeight: "800", letterSpacing: 0.8 },
  passwordRule: { marginTop: 4, color: COLORS.muted, fontSize: 12 },
  passwordRulePassed: { color: COLORS.green, fontWeight: "700" },
  infoNotice: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10, borderWidth: 1, borderColor: COLORS.infoBorder, borderRadius: 10, backgroundColor: COLORS.infoBackground, padding: 12 },
  infoText: { flex: 1, color: COLORS.info, fontSize: 13, lineHeight: 19 },
  errorNotice: { marginBottom: 10, borderWidth: 1, borderColor: "rgba(194,74,58,0.25)", borderRadius: 10, backgroundColor: COLORS.redBackground, padding: 12 },
  errorText: { color: COLORS.red, fontSize: 13, lineHeight: 19 },
  primaryButton: { minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 21, borderRadius: 10, backgroundColor: COLORS.goldButton, paddingHorizontal: 16 },
  disabledButton: { opacity: 0.5 },
  primaryButtonText: { color: COLORS.navy, fontSize: 14, fontWeight: "800", textAlign: "center" },
  emailNotice: { marginTop: 5, borderRadius: 10, backgroundColor: COLORS.surface, padding: 13, color: COLORS.text, fontSize: 14 },
  footer: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", gap: 5, marginTop: 22 },
  footerText: { color: COLORS.secondary, fontSize: 12 },
  link: { color: COLORS.gold, fontSize: 12, fontWeight: "800" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});