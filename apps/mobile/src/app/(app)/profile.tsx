import { useEffect, useState } from "react";
import {ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import {changePassword, restoreSession, signOut, signOutAll,
} from "../../api/client";
import type { AuthUser } from "../../api/types";
import LanguageSwitcher from "../../components/LanguageSwitcher";

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

function passwordIsStrong(value: string) {
  return (
    value.length >= 12 &&
    value.length <= 128 &&
    /[A-Z]/.test(value) &&
    /[a-z]/.test(value) &&
    /\d/.test(value) &&
    /[^\w\s]/.test(value) &&
    !commonPasswords.has(value.toLowerCase())
  );
}

export default function ProfileScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [sessionEnded, setSessionEnded] = useState(false);

  useEffect(() => {
    let active = true;

    restoreSession()
      .then((restoredUser) => {
        if (!active) return;

        if (!restoredUser) {
          router.replace("/login");
          return;
        }

        setUser(restoredUser);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : t("profile.loadFailure"),
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [t]);

  async function handleChangePassword() {
    setError("");
    setSuccess("");

    if (!currentPassword) {
      setError(t("profile.validation.currentPassword"));
      return;
    }

    if (!passwordIsStrong(newPassword)) {
      setError(t("profile.validation.passwordStrength"));
      return;
    }

    if (newPassword !== confirmation) {
      setError(t("profile.validation.passwordMismatch"));
      return;
    }

    setBusy(true);

    try {
      const result = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirmation: confirmation,
      });

      setSuccess(result.message || t("profile.passwordChanged"));
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      setSessionEnded(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("profile.changePasswordFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  function showSignOutErrorAndReturn(errorMessage: string) {
    Alert.alert(t("profile.signOutTitle"), errorMessage, [
      {
        text: t("profile.continue"),
        onPress: () => router.replace("/login"),
      },
    ]);
  }

  async function handleSignOut() {
    setError("");
    setBusy(true);

    try {
      await signOut();
      router.replace("/login");
    } catch (err) {
      showSignOutErrorAndReturn(
        err instanceof Error ? err.message : t("profile.signOutFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSignOutAll() {
    setError("");
    setBusy(true);

    try {
      await signOutAll();
      router.replace("/login");
    } catch (err) {
      showSignOutErrorAndReturn(
        err instanceof Error
          ? err.message
          : t("profile.revokeSessionsFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.gold} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("profile.loading")}
        </Text>
      </View>
    );
  }

  if (!user && !error) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("profile.returningToSignIn")}
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      <View style={[styles.topRow, isUrdu && styles.rtlRow]}>
        <View style={styles.headingCopy}>
          <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
            {t("profile.identity")}
          </Text>
          <Text style={[styles.heading, isUrdu && styles.rtlText]}>
            {t("profile.title")}
          </Text>
          <Text style={[styles.intro, isUrdu && styles.rtlText]}>
            {t("profile.intro")}
          </Text>
        </View>
        <LanguageSwitcher />
      </View>

      {error ? (
        <View style={styles.errorNotice}>
          <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
            {error}
          </Text>
        </View>
      ) : null}

      {success ? (
        <View style={styles.successNotice}>
          <Text style={[styles.successText, isUrdu && styles.rtlText]}>
            {success}
          </Text>
        </View>
      ) : null}

      {user ? (
        <View style={styles.card}>
          <View style={[styles.identityHeader, isUrdu && styles.rtlRow]}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {user.first_name.charAt(0)}
                {user.last_name.charAt(0)}
              </Text>
            </View>

            <View style={styles.identityCopy}>
              <Text style={[styles.name, isUrdu && styles.rtlText]}>
                {user.first_name} {user.last_name}
              </Text>
              <Text style={[styles.role, isUrdu && styles.rtlText]}>
                {user.role.name}
              </Text>
            </View>
          </View>

          <ProfileRow
            label={t("profile.email")}
            value={user.email}
            isUrdu={isUrdu}
          />
          <ProfileRow
            label={t("profile.organization")}
            value={user.organization.name}
            isUrdu={isUrdu}
          />
          <ProfileRow
            label={t("profile.workspace")}
            value={user.organization.slug}
            isUrdu={isUrdu}
          />
          <ProfileRow
            label={t("profile.role")}
            value={user.role.name}
            isUrdu={isUrdu}
          />
          <ProfileRow
            label={t("profile.emailStatus")}
            value={
              user.is_verified
                ? t("profile.verified")
                : t("profile.unverified")
            }
            positive={user.is_verified}
            isUrdu={isUrdu}
          />
          <ProfileRow
            label={t("profile.accountStatus")}
            value={
              user.is_active
                ? t("profile.active")
                : t("profile.inactive")
            }
            positive={user.is_active}
            isUrdu={isUrdu}
          />
        </View>
      ) : null}

      <View style={styles.card}>
        <Text style={[styles.sectionEyebrow, isUrdu && styles.rtlText]}>
          {t("profile.security")}
        </Text>
        <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
          {t("profile.changePassword")}
        </Text>

        {sessionEnded ? (
          <Pressable
            accessibilityRole="button"
            style={styles.primaryButton}
            onPress={() => router.replace("/login")}
          >
            <Text style={[styles.primaryButtonText, isUrdu && styles.rtlText]}>
              {t("profile.signInWithNewPassword")}
            </Text>
          </Pressable>
        ) : (
          <>
            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("profile.currentPassword")}
            </Text>
            <TextInput
              style={[styles.input, isUrdu && styles.rtlText]}
              value={currentPassword}
              onChangeText={setCurrentPassword}
              secureTextEntry
              autoComplete="current-password"
              textContentType="password"
              editable={!busy}
              textAlign={isUrdu ? "right" : "left"}
            />

            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("profile.newPassword")}
            </Text>
            <TextInput
              style={[styles.input, isUrdu && styles.rtlText]}
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
              autoComplete="new-password"
              textContentType="newPassword"
              editable={!busy}
              textAlign={isUrdu ? "right" : "left"}
            />

            {newPassword ? (
              <Text
                style={[
                  styles.passwordHint,
                  passwordIsStrong(newPassword) &&
                    styles.passwordHintSuccess,
                  isUrdu && styles.rtlText,
                ]}
              >
                {passwordIsStrong(newPassword)
                  ? t("profile.passwordMeetsRequirements")
                  : t("profile.validation.passwordStrength")}
              </Text>
            ) : null}

            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("profile.confirmNewPassword")}
            </Text>
            <TextInput
              style={[
                styles.input,
                confirmation &&
                  confirmation !== newPassword &&
                  styles.inputError,
                isUrdu && styles.rtlText,
              ]}
              value={confirmation}
              onChangeText={setConfirmation}
              secureTextEntry
              autoComplete="new-password"
              textContentType="newPassword"
              editable={!busy}
              textAlign={isUrdu ? "right" : "left"}
            />

            {confirmation && confirmation !== newPassword ? (
              <Text style={[styles.fieldError, isUrdu && styles.rtlText]}>
                {t("profile.validation.passwordMismatch")}
              </Text>
            ) : null}

            <Pressable
              accessibilityRole="button"
              style={[
                styles.primaryButton,
                busy && styles.disabledButton,
              ]}
              onPress={() => void handleChangePassword()}
              disabled={busy}
            >
              <Text style={[styles.primaryButtonText, isUrdu && styles.rtlText]}>
                {busy
                  ? t("profile.updatingPassword")
                  : t("profile.updatePassword")}
              </Text>
            </Pressable>
          </>
        )}
      </View>

      <View style={styles.card}>
        <Text style={[styles.sectionEyebrow, isUrdu && styles.rtlText]}>
          {t("profile.sessions")}
        </Text>
        <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
          {t("profile.secureWorkspace")}
        </Text>
        <Text style={[styles.sessionDescription, isUrdu && styles.rtlText]}>
          {t("profile.sessionsDescription")}
        </Text>

        <Pressable
          accessibilityRole="button"
          style={[styles.secondaryButton, busy && styles.disabledButton]}
          onPress={() => void handleSignOut()}
          disabled={busy}
        >
          <Text style={[styles.secondaryButtonText, isUrdu && styles.rtlText]}>
            {busy ? t("profile.signingOut") : t("profile.signOut")}
          </Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          style={[styles.dangerButton, busy && styles.disabledButton]}
          onPress={() => void handleSignOutAll()}
          disabled={busy}
        >
          <Text style={[styles.dangerButtonText, isUrdu && styles.rtlText]}>
            {busy
              ? t("profile.revokingSessions")
              : t("profile.revokeAllSessions")}
          </Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

function ProfileRow(props: {
  label: string;
  value: string;
  positive?: boolean;
  isUrdu: boolean;
}) {
  return (
    <View style={[styles.profileRow, props.isUrdu && styles.rtlRow]}>
      <Text style={[styles.rowLabel, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <Text
        style={[
          styles.rowValue,
          props.positive && styles.positiveValue,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.value}
      </Text>
    </View>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  text: "#191410",
  secondary: "#5C5347",
  muted: "#8C806E",
  border: "#E4D9C4",
  gold: "#D9A441",
  navy: "#080D18",
  green: "#1E8055",
  red: "#A33328",
  redBackground: "#F9E5DF",
  greenBackground: "#E5F4EC",
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 20, paddingBottom: 36, gap: 16 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: COLORS.background, padding: 24 },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  topRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12 },
  rtlRow: { flexDirection: "row-reverse" },
  headingCopy: { flex: 1 },
  eyebrow: { color: COLORS.gold, fontSize: 10, fontWeight: "800", letterSpacing: 1.4 },
  heading: { color: COLORS.text, fontSize: 28, fontWeight: "800", marginTop: 4 },
  intro: { color: COLORS.secondary, fontSize: 14, lineHeight: 21, marginTop: 5 },
  muted: { color: COLORS.secondary, fontSize: 14, textAlign: "center" },
  card: { borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, borderRadius: 14, backgroundColor: COLORS.surface, padding: 16 },
  identityHeader: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 8 },
  avatar: { width: 48, height: 48, alignItems: "center", justifyContent: "center", borderRadius: 13, backgroundColor: COLORS.navy },
  avatarText: { color: COLORS.gold, fontSize: 16, fontWeight: "800" },
  identityCopy: { flex: 1 },
  name: { color: COLORS.text, fontSize: 17, fontWeight: "800" },
  role: { color: COLORS.muted, fontSize: 12, fontWeight: "700", marginTop: 3 },
  profileRow: { minHeight: 46, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: "#F0EADF" },
  rowLabel: { color: COLORS.muted, fontSize: 12 },
  rowValue: { flex: 1, color: COLORS.text, fontSize: 13, fontWeight: "600", textAlign: "right" },
  positiveValue: { color: COLORS.green },
  sectionEyebrow: { color: COLORS.gold, fontSize: 10, fontWeight: "800", letterSpacing: 1.2 },
  sectionTitle: { color: COLORS.text, fontSize: 18, fontWeight: "800", marginTop: 5, marginBottom: 6 },
  label: { color: COLORS.text, fontSize: 12, fontWeight: "700", marginTop: 13, marginBottom: 6 },
  input: { minHeight: 46, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, backgroundColor: COLORS.surface, paddingHorizontal: 13, color: COLORS.text, fontSize: 14 },
  inputError: { borderColor: "#C24A3A" },
  passwordHint: { color: COLORS.muted, fontSize: 12, lineHeight: 18, marginTop: 7 },
  passwordHintSuccess: { color: COLORS.green },
  fieldError: { color: "#C24A3A", fontSize: 12, marginTop: 5 },
  primaryButton: { minHeight: 48, alignItems: "center", justifyContent: "center", backgroundColor: COLORS.gold, borderRadius: 10, paddingHorizontal: 14, marginTop: 16 },
  primaryButtonText: { color: COLORS.navy, fontSize: 13, fontWeight: "800", textAlign: "center" },
  secondaryButton: { minHeight: 46, alignItems: "center", justifyContent: "center", backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, paddingHorizontal: 14, marginTop: 13 },
  secondaryButtonText: { color: COLORS.text, fontSize: 13, fontWeight: "800", textAlign: "center" },
  dangerButton: { minHeight: 46, alignItems: "center", justifyContent: "center", backgroundColor: "#A63A32", borderRadius: 10, paddingHorizontal: 14, marginTop: 9 },
  dangerButtonText: { color: COLORS.surface, fontSize: 13, fontWeight: "800", textAlign: "center" },
  disabledButton: { opacity: 0.55 },
  sessionDescription: { color: COLORS.secondary, fontSize: 13, lineHeight: 19 },
  errorNotice: { backgroundColor: COLORS.redBackground, borderColor: "#E9B8AC", borderWidth: 1, borderRadius: 10, padding: 12 },
  errorText: { color: COLORS.red, fontSize: 13, lineHeight: 19 },
  successNotice: { backgroundColor: COLORS.greenBackground, borderColor: "#B7DDC7", borderWidth: 1, borderRadius: 10, padding: 12 },
  successText: { color: COLORS.green, fontSize: 13, lineHeight: 19 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});