import { useEffect, useState } from "react";
import {ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link, useLocalSearchParams } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { previewInvitation, register } from "../api/client";
import type { InvitationPreview } from "../api/types";

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
    label: "12–128 characters",
    test: (value: string) => value.length >= 12 && value.length <= 128,
  },
  {
    label: "An uppercase letter",
    test: (value: string) => /[A-Z]/.test(value),
  },
  {
    label: "A lowercase letter",
    test: (value: string) => /[a-z]/.test(value),
  },
  {
    label: "A number",
    test: (value: string) => /\d/.test(value),
  },
  {
    label: "A symbol",
    test: (value: string) => /[^\w\s]/.test(value),
  },
  {
    label: "Not a common password",
    test: (value: string) =>
      value.length > 0 && !commonPasswords.has(value.toLowerCase()),
  },
];

function passwordIsStrong(value: string) {
  return passwordRules.every((rule) => rule.test(value));
}

export default function RegisterScreen() {
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
            : "This invitation link is invalid or has expired.",
        );
      })
      .finally(() => {
        if (active) setInvitationLoading(false);
      });

    return () => {
      active = false;
    };
  }, [invitationToken]);

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
        result.message || "Your Trace account has been created.",
      );
      setPassword("");
      setConfirmation("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  if (successMessage) {
    return (
      <SafeAreaView style={styles.screen} edges={["top", "bottom"]}>
        <StatusBar barStyle="dark-content" backgroundColor="#F3EEE4" />
        <View style={styles.successContent}>
          <View style={styles.brandMark}>
            <Text style={styles.brandMarkText}>T</Text>
          </View>

          <Text style={styles.eyebrow}>ACCOUNT CREATED</Text>
          <Text style={styles.title}>
            {verificationRequired ? "Check your email." : "You’re all set."}
          </Text>
          <Text style={styles.description}>{successMessage}</Text>
          <Text style={styles.emailNotice}>{registeredEmail}</Text>

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
                <Text style={styles.primaryButtonText}>
                  Continue to email verification
                </Text>
              </Pressable>
            </Link>
          ) : (
            <Link href="/login" asChild>
              <Pressable
                style={styles.primaryButton}
                accessibilityRole="button"
              >
                <Text style={styles.primaryButtonText}>
                  Continue to sign in
                </Text>
              </Pressable>
            </Link>
          )}
        </View>
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

            <Text style={styles.eyebrow}>
              {invitationToken ? "ACCEPT INVITATION" : "CREATE WORKSPACE"}
            </Text>
            <Text style={styles.title}>Start with a clear record.</Text>
            <Text style={styles.description}>
              Create your Trace account and bring your project information into
              one workspace.
            </Text>

            {invitationLoading ? (
              <View style={styles.infoNotice}>
                <ActivityIndicator size="small" color="#3B7DC4" />
                <Text style={styles.infoText}>Checking invitation…</Text>
              </View>
            ) : null}

            {invitation ? (
              <View style={styles.infoNotice}>
                <Text style={styles.infoText}>
                  You’re joining {invitation.organization_name}
                  {invitation.role_name ? ` as ${invitation.role_name}` : ""}.
                </Text>
              </View>
            ) : null}

            {invitationError ? (
              <View style={styles.errorNotice} accessibilityLiveRegion="polite">
                <Text style={styles.errorText}>{invitationError}</Text>
              </View>
            ) : null}

            {error ? (
              <View style={styles.errorNotice} accessibilityLiveRegion="polite">
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            <Text style={styles.label}>First name</Text>
            <TextInput
              style={styles.input}
              value={firstName}
              onChangeText={setFirstName}
              autoComplete="given-name"
              textContentType="givenName"
              placeholder="First name"
              placeholderTextColor="#8C806E"
              editable={!busy}
              returnKeyType="next"
            />

            <Text style={styles.label}>Last name</Text>
            <TextInput
              style={styles.input}
              value={lastName}
              onChangeText={setLastName}
              autoComplete="family-name"
              textContentType="familyName"
              placeholder="Last name"
              placeholderTextColor="#8C806E"
              editable={!busy}
              returnKeyType="next"
            />

            <Text style={styles.label}>Work email</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              textContentType="emailAddress"
              keyboardType="email-address"
              placeholder="you@company.com"
              placeholderTextColor="#8C806E"
              editable={!busy && !invitationToken}
              returnKeyType="next"
            />

            {!invitationToken ? (
              <>
                <Text style={styles.label}>Organization name</Text>
                <TextInput
                  style={styles.input}
                  value={organizationName}
                  onChangeText={setOrganizationName}
                  placeholder="Your construction company"
                  placeholderTextColor="#8C806E"
                  editable={!busy}
                  returnKeyType="next"
                />
              </>
            ) : null}

            <Text style={styles.label}>Password</Text>
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

            <Text style={styles.label}>Confirm password</Text>
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
              placeholder="Repeat your password"
              placeholderTextColor="#8C806E"
              editable={!busy}
              returnKeyType="go"
              onSubmitEditing={() => void handleRegister()}
            />

            {confirmation && !passwordsMatch ? (
              <Text style={styles.fieldError}>Passwords do not match.</Text>
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
              <Text style={styles.primaryButtonText}>
                {busy ? "Creating account…" : "Create Trace account"}
              </Text>
            </Pressable>

            <View style={styles.footer}>
              <Text style={styles.footerText}>Already have an account?</Text>
              <Link href="/login" asChild>
                <Pressable accessibilityRole="link">
                  <Text style={styles.link}>Sign in</Text>
                </Pressable>
              </Link>
            </View>
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
  successContent: { flex: 1, justifyContent: "center", padding: 24 },
  brandRow: {flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 25,},
  brandMark: {width: 38, height: 38, alignItems: "center", justifyContent: "center", borderRadius: 10, backgroundColor: "#080D18",},
  brandMarkText: { color: "#D9A441", fontSize: 21, fontWeight: "900" },
  brand: { color: "#080D18", fontSize: 20, fontWeight: "800" },
  eyebrow: {marginBottom: 7, color: "#B98626", fontSize: 10, fontWeight: "800", letterSpacing: 1.2,},
  title: { color: "#191410", fontSize: 30, fontWeight: "800", lineHeight: 37 },
  description: {marginTop: 8, marginBottom: 19, color: "#5C5347", fontSize: 14, lineHeight: 21, },
  label: { marginTop: 13, marginBottom: 7, color: "#191410", fontSize: 13, fontWeight: "700",},
  input: {minHeight: 48, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 8, backgroundColor: "#FFFFFF", paddingHorizontal: 13, color: "#191410", fontSize: 15,},
  inputError: { borderColor: "#C24A3A" },
  fieldError: { marginTop: 5, color: "#C24A3A", fontSize: 12 },
  passwordCard: {marginTop: 9, borderWidth: 1, borderColor: "#E4D9C4", borderRadius: 9, backgroundColor: "#FBF8F2", padding: 12,},
  passwordTitle: {marginBottom: 5, color: "#5C5347", fontSize: 10, fontWeight: "800", letterSpacing: 0.8,},
  passwordRule: { marginTop: 4, color: "#8C806E", fontSize: 12 },
  passwordRulePassed: { color: "#1E9D63", fontWeight: "700" },
  infoNotice: {flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10, borderWidth: 1, borderColor: "rgba(59,125,196,0.25)", borderRadius: 8, backgroundColor: "#E7F0FA", padding: 12,},
  infoText: { flex: 1, color: "#3B7DC4", fontSize: 13, lineHeight: 19 },
  errorNotice: {marginBottom: 10, borderWidth: 1, borderColor: "rgba(194,74,58,0.25)", borderRadius: 8, backgroundColor: "#F9E5DF", padding: 12,},
  errorText: { color: "#C24A3A", fontSize: 13, lineHeight: 19 },
  primaryButton: {minHeight: 50, alignItems: "center", justifyContent: "center", marginTop: 21, borderRadius: 8, backgroundColor: "#D9A441", paddingHorizontal: 16,},
  disabledButton: { opacity: 0.5 },
  primaryButtonText: {color: "#080D18", fontSize: 14, fontWeight: "800", textAlign: "center",},
  emailNotice: {marginTop: 5, borderRadius: 8, backgroundColor: "#FFFFFF", padding: 13, color: "#191410", fontSize: 14,},
  footer: {flexDirection: "row", justifyContent: "center", gap: 5, marginTop: 22,},
  footerText: { color: "#5C5347", fontSize: 12 },
  link: { color: "#B98626", fontSize: 12, fontWeight: "800" },
});