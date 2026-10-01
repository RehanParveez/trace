import { useEffect, useState } from "react";
import {ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router } from "expo-router";
import {changePassword, restoreSession, signOut, signOutAll,
} from "../../api/client";
import type { AuthUser } from "../../api/types";

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
              : "Could not load your account.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleChangePassword() {
    setError("");
    setSuccess("");

    if (!currentPassword) {
      setError("Enter your current password.");
      return;
    }

    if (!passwordIsStrong(newPassword)) {
      setError(
        "Use 12–128 characters with uppercase, lowercase, a number, and a symbol. Avoid common passwords.",
      );
      return;
    }

    if (newPassword !== confirmation) {
      setError("The new passwords do not match.");
      return;
    }

    setBusy(true);

    try {
      const result = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirmation: confirmation,
      });

      setSuccess(result.message || "Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      setSessionEnded(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not change your password.",
      );
    } finally {
      setBusy(false);
    }
  }

  function showSignOutErrorAndReturn(errorMessage: string) {
    Alert.alert("Sign out", errorMessage, [
      {
        text: "Continue",
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
        err instanceof Error ? err.message : "Could not sign out.",
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
          : "Could not revoke the other sessions.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#B98626" />
        <Text style={styles.muted}>Loading your profile…</Text>
      </View>
    );
  }

  if (!user && !error) {
    return (
      <View style={styles.center}>
        <Text style={styles.muted}>Returning to sign in…</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.eyebrow}>IDENTITY</Text>
      <Text style={styles.heading}>My profile</Text>
      <Text style={styles.intro}>
        Manage your account details and security.
      </Text>

      {error ? (
        <View style={styles.errorNotice}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {success ? (
        <View style={styles.successNotice}>
          <Text style={styles.successText}>{success}</Text>
        </View>
      ) : null}

      {user ? (
        <View style={styles.card}>
          <View style={styles.identityHeader}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {user.first_name.charAt(0)}
                {user.last_name.charAt(0)}
              </Text>
            </View>

            <View style={styles.identityCopy}>
              <Text style={styles.name}>
                {user.first_name} {user.last_name}
              </Text>
              <Text style={styles.role}>{user.role.name}</Text>
            </View>
          </View>

          <ProfileRow label="Email" value={user.email} />
          <ProfileRow label="Organization" value={user.organization.name} />
          <ProfileRow label="Workspace" value={user.organization.slug} />
          <ProfileRow label="Role" value={user.role.name} />
          <ProfileRow
            label="Email status"
            value={user.is_verified ? "Verified" : "Unverified"}
            positive={user.is_verified}
          />
          <ProfileRow
            label="Account status"
            value={user.is_active ? "Active" : "Inactive"}
            positive={user.is_active}
          />
        </View>
      ) : null}

      <View style={styles.card}>
        <Text style={styles.sectionEyebrow}>SECURITY</Text>
        <Text style={styles.sectionTitle}>Change password</Text>

        {sessionEnded ? (
          <Pressable
            accessibilityRole="button"
            style={styles.primaryButton}
            onPress={() => router.replace("/login")}
          >
            <Text style={styles.primaryButtonText}>
              Sign in with your new password
            </Text>
          </Pressable>
        ) : (
          <>
            <Text style={styles.label}>Current password</Text>
            <TextInput
              style={styles.input}
              value={currentPassword}
              onChangeText={setCurrentPassword}
              secureTextEntry
              autoComplete="current-password"
              textContentType="password"
              editable={!busy}
            />

            <Text style={styles.label}>New password</Text>
            <TextInput
              style={styles.input}
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
              autoComplete="new-password"
              textContentType="newPassword"
              editable={!busy}
            />

            {newPassword ? (
              <Text
                style={[
                  styles.passwordHint,
                  passwordIsStrong(newPassword) && styles.passwordHintSuccess,
                ]}
              >
                {passwordIsStrong(newPassword)
                  ? "Password meets the requirements."
                  : "Use 12–128 characters with uppercase, lowercase, a number, and a symbol. Avoid common passwords."}
              </Text>
            ) : null}

            <Text style={styles.label}>Confirm new password</Text>
            <TextInput
              style={[
                styles.input,
                confirmation &&
                  confirmation !== newPassword &&
                  styles.inputError,
              ]}
              value={confirmation}
              onChangeText={setConfirmation}
              secureTextEntry
              autoComplete="new-password"
              textContentType="newPassword"
              editable={!busy}
            />

            {confirmation && confirmation !== newPassword ? (
              <Text style={styles.fieldError}>Passwords do not match.</Text>
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
              <Text style={styles.primaryButtonText}>
                {busy ? "Updating password…" : "Update password"}
              </Text>
            </Pressable>
          </>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionEyebrow}>SESSIONS</Text>
        <Text style={styles.sectionTitle}>Secure your workspace</Text>
        <Text style={styles.sessionDescription}>
          Sign out on this device or revoke every active session for your
          account.
        </Text>

        <Pressable
          accessibilityRole="button"
          style={[styles.secondaryButton, busy && styles.disabledButton]}
          onPress={() => void handleSignOut()}
          disabled={busy}
        >
          <Text style={styles.secondaryButtonText}>
            {busy ? "Signing out…" : "Sign out"}
          </Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          style={[styles.dangerButton, busy && styles.disabledButton]}
          onPress={() => void handleSignOutAll()}
          disabled={busy}
        >
          <Text style={styles.dangerButtonText}>
            {busy ? "Revoking sessions…" : "Revoke all sessions"}
          </Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

function ProfileRow({
  label,
  value,
  positive = false,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <View style={styles.profileRow}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, positive && styles.positiveValue]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F3EEE4" },
  content: { padding: 20, paddingBottom: 36, gap: 16 },
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F3EEE4", padding: 24,},
  eyebrow: {color: "#B98626", fontSize: 10, fontWeight: "800", letterSpacing: 1.4,},
  heading: { color: "#191410", fontSize: 30, fontWeight: "800" },
  intro: { color: "#5C5347", fontSize: 14, lineHeight: 21, marginTop: -10 },
  muted: { color: "#5C5347", fontSize: 14 },
  card: {borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 12, backgroundColor: "#FFFFFF", padding: 16,},
  identityHeader: {flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 8,},
  avatar: {width: 48, height: 48, alignItems: "center", justifyContent: "center", borderRadius: 12, backgroundColor: "#080D18",},
  avatarText: { color: "#D9A441", fontSize: 16, fontWeight: "800" },
  identityCopy: { flex: 1 },
  name: { color: "#191410", fontSize: 18, fontWeight: "700" },
  role: {color: "#8C806E", fontSize: 11,  fontWeight: "700", marginTop: 3,},
  profileRow: {minHeight: 46, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: "#F0EADF",},
  rowLabel: { color: "#8C806E", fontSize: 12 },
  rowValue: {flex: 1, color: "#191410", fontSize: 13, fontWeight: "600", textAlign: "right",},
  positiveValue: { color: "#1E8055" },
  sectionEyebrow: {color: "#B98626", fontSize: 10, fontWeight: "800", letterSpacing: 1.2,},
  sectionTitle: {color: "#191410", fontSize: 19, fontWeight: "700", marginTop: 5, marginBottom: 6,},
  label: {color: "#191410", fontSize: 13, fontWeight: "700", marginTop: 13, marginBottom: 6,},
  input: {minHeight: 48, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, backgroundColor: "#FFFFFF", paddingHorizontal: 13, color: "#191410", fontSize: 15,},
  inputError: { borderColor: "#C24A3A" },
  passwordHint: { color: "#8C806E", fontSize: 12, lineHeight: 18, marginTop: 7 },
  passwordHintSuccess: { color: "#1E8055" },
  fieldError: { color: "#C24A3A", fontSize: 12, marginTop: 5 },
  primaryButton: {minHeight: 50, alignItems: "center", justifyContent: "center", backgroundColor: "#D9A441", borderRadius: 8, paddingHorizontal: 14, marginTop: 18,},
  primaryButtonText: { color: "#080D18", fontSize: 14, fontWeight: "800" },
  secondaryButton: {minHeight: 48, alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, paddingHorizontal: 14, marginTop: 14,},
  secondaryButtonText: { color: "#191410", fontSize: 14, fontWeight: "700" },
  dangerButton: {minHeight: 48, alignItems: "center", justifyContent: "center", backgroundColor: "#B42318", borderRadius: 8, paddingHorizontal: 14, marginTop: 10,},
  dangerButtonText: { color: "#FFFFFF", fontSize: 14, fontWeight: "700" },
  disabledButton: { opacity: 0.55 },
  sessionDescription: { color: "#5C5347", fontSize: 13, lineHeight: 19 },
  errorNotice: {backgroundColor: "#F9E5DF", borderColor: "#E9B8AC", borderWidth: 1, borderRadius: 8, padding: 12,},
  errorText: { color: "#A33328", fontSize: 13, lineHeight: 19 },
  successNotice: {backgroundColor: "#E5F4EC", borderColor: "#B7DDC7", borderWidth: 1, borderRadius: 8, padding: 12,},
  successText: { color: "#1E8055", fontSize: 13, lineHeight: 19 },
});