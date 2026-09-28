import { useEffect, useState } from "react";
import {ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Link, router } from "expo-router";
import { restoreSession, signIn, signOut } from "../api/client";
import type { AuthUser } from "../api/types";

export default function SignInScreen() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function checkSession() {
    setCheckingSession(true);
    setError("");

    try {
      const restoredUser = await restoreSession();
      setUser(restoredUser);

      if (restoredUser) {
       router.replace("/projects");
}
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not connect to Trace.");
    } finally {
      setCheckingSession(false);
    }
  }

  useEffect(() => {
    void checkSession();
  }, []);

  async function handleSignIn() {
    setBusy(true);
    setError("");

    try {
      const signedInUser = await signIn(email.trim().toLowerCase(), password);
      setUser(signedInUser);
      setPassword("");
      router.replace("/projects");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignOut() {
    setBusy(true);
    setError("");

    try {
      await signOut();
      setUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-out failed.");
    } finally {
      setBusy(false);
    }
  }

  if (checkingSession) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Connecting to Trace…</Text>
      </View>
    );
  }

  if (user) {
    return (
      <View style={styles.page}>
        <StatusBar barStyle="dark-content" />
        <Text style={styles.brand}>Trace</Text>
        <Text style={styles.heading}>You’re signed in</Text>
        <Text style={styles.body}>
          {user.first_name} {user.last_name}
        </Text>
        <Text style={styles.body}>{user.organization.name}</Text>
        <Text style={styles.muted}>Role: {user.role.name}</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          accessibilityRole="button"
          style={[styles.button, busy && styles.disabled]}
          onPress={handleSignOut}
          disabled={busy}
        >
          <Text style={styles.buttonText}>
            {busy ? "Signing out…" : "Sign out"}
          </Text>
        </Pressable>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.page}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <StatusBar barStyle="dark-content" />
      <ScrollView contentContainerStyle={styles.form}>
        <Text style={styles.brand}>Trace</Text>
        <Text style={styles.heading}>Sign in</Text>
        <Text style={styles.muted}>Use your existing Trace account.</Text>

        <Text style={styles.label}>Email</Text>
        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          placeholder="you@company.com"
        />

        <Text style={styles.label}>Password</Text>
        <TextInput
          autoCapitalize="none"
          autoComplete="current-password"
          secureTextEntry
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="Your password"
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          accessibilityRole="button"
          style={[styles.button, busy && styles.disabled]}
          onPress={handleSignIn}
          disabled={busy || !email.trim() || !password}
        >
          <Text style={styles.buttonText}>
            {busy ? "Signing in…" : "Sign in"}
          </Text>
        </Pressable>

        {error ? (
          <Pressable onPress={() => void checkSession()} style={styles.retry}>
            <Text style={styles.retryText}>Retry connection</Text>
          </Pressable>
        ) : null}

        <Link href="/forgot-password" asChild>
          <Pressable style={styles.linkButton}>
            <Text style={styles.linkText}>Forgot password?</Text>
          </Pressable>
        </Link>

        <Link href="/register" asChild>
          <Pressable style={styles.linkButton}>
            <Text style={styles.linkText}>Create an account</Text>
          </Pressable>
        </Link>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: "#F4F6F8",
    justifyContent: "center",
    padding: 24,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    backgroundColor: "#F4F6F8",
  },
  form: {
    flexGrow: 1,
    justifyContent: "center",
  },
  brand: {
    color: "#183153",
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 24,
  },
  heading: {
    color: "#17212F",
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 8,
  },
  body: {
    color: "#17212F",
    fontSize: 16,
    marginBottom: 8,
  },
  muted: {
    color: "#667085",
    fontSize: 14,
    marginBottom: 20,
  },
  label: {
    color: "#344054",
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 8,
    marginTop: 12,
  },
  input: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D0D5DD",
    borderRadius: 10,
    borderWidth: 1,
    fontSize: 16,
    padding: 14,
  },
  button: {
    alignItems: "center",
    backgroundColor: "#183153",
    borderRadius: 10,
    marginTop: 20,
    padding: 15,
  },
  disabled: {
    opacity: 0.55,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  error: {
    color: "#B42318",
    marginTop: 14,
  },
  retry: {
    alignItems: "center",
    padding: 14,
  },
  retryText: {
    color: "#183153",
    fontWeight: "600",
  },
  linkButton: {
    alignItems: "center",
    padding: 12,
  },
  linkText: {
    color: "#183153",
    fontWeight: "600",
  },
});