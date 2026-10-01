import { useCallback, useEffect, useState } from "react";
import { router } from "expo-router";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { restoreSession } from "../api/client";

export default function LandingScreen() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [sessionError, setSessionError] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  const checkSession = useCallback(async () => {
    setCheckingSession(true);
    setSessionError("");

    try {
      const user = await restoreSession();

      if (user) {
        router.replace("/projects");
      }
    } catch (error) {
      setSessionError(
        error instanceof Error
          ? error.message
          : "We couldn’t check your account right now.",
      );
    } finally {
      setCheckingSession(false);
    }
  }, []);

  useEffect(() => {
    void checkSession();
  }, [checkSession]);

  return (
    <View style={styles.page}>
      <StatusBar barStyle="light-content" backgroundColor="#0D1723" />

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.brandBlock}>
          <Text style={styles.brand}>TRACE</Text>
          <Text style={styles.brandCaption}>CONSTRUCTION WORKSPACE</Text>
        </View>

        <View style={styles.hero}>
          <Text style={styles.headline}>
            Keep the work moving.
            {"\n"}
            <Text style={styles.headlineAccent}>Keep the record clear.</Text>
          </Text>

          <Text style={styles.description}>
            Bring projects, drawings, site updates, and approvals together in
            one workspace for your construction team.
          </Text>
        </View>

        <View style={styles.actions}>
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push("/login")}
            android_ripple={{ color: "#9AD8EE" }}
            style={styles.primaryButton}
          >
            <Text style={styles.primaryButtonText}>Sign in</Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            onPress={() => router.push("/register")}
            android_ripple={{ color: "#293D55" }}
            style={styles.secondaryButton}
          >
            <Text style={styles.secondaryButtonText}>Create an account</Text>
          </Pressable>
        </View>

        {checkingSession ? (
          <View style={styles.sessionStatus}>
            <ActivityIndicator size="small" color="#78C5E4" />
            <Text style={styles.sessionStatusText}>
              Checking your account…
            </Text>
          </View>
        ) : null}

        {sessionError ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{sessionError}</Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => void checkSession()}
              style={styles.retryButton}
            >
              <Text style={styles.retryText}>Try again</Text>
            </Pressable>
          </View>
        ) : null}

        <View style={styles.detailsCard}>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ expanded: showDetails }}
            onPress={() => setShowDetails((current) => !current)}
            style={styles.detailsToggle}
          >
            <View style={styles.detailsHeading}>
              <Text style={styles.detailsEyebrow}>TRACE AT A GLANCE</Text>
              <Text style={styles.detailsTitle}>How Trace helps</Text>
            </View>
            <Text style={styles.toggleIcon}>
              {showDetails ? "−" : "+"}
            </Text>
          </Pressable>

          {showDetails ? (
            <View style={styles.detailsList}>
              <DetailRow
                title="Keep project records together"
                description="Projects, teams, drawings, and progress in one place."
              />
              <DetailRow
                title="Follow work on site"
                description="Connect site updates and photos to the right project."
              />
              <DetailRow
                title="Make approvals traceable"
                description="Authorized people review changes before they become official."
                last
              />
            </View>
          ) : null}
        </View>

        <Text style={styles.footer}>
          AI assists. Deterministic systems calculate. People approve.
        </Text>
      </ScrollView>
    </View>
  );
}

function DetailRow({
  title,
  description,
  last = false,
}: {
  title: string;
  description: string;
  last?: boolean;
}) {
  return (
    <View style={[styles.detailRow, last && styles.lastDetailRow]}>
      <View style={styles.detailMark} />
      <View style={styles.detailCopy}>
        <Text style={styles.detailTitle}>{title}</Text>
        <Text style={styles.detailDescription}>{description}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: "#0D1723",
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 30,
    paddingBottom: 24,
  },
  brandBlock: {
    marginBottom: 48,
  },
  brand: {
    color: "#F3EEDF",
    fontSize: 21,
    fontWeight: "900",
    letterSpacing: 2.4,
  },
  brandCaption: {
    color: "#8292A6",
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 1.5,
    marginTop: 5,
  },
  hero: {
    marginBottom: 28,
  },
  headline: {
    color: "#F3EEDF",
    fontSize: 34,
    fontWeight: "800",
    letterSpacing: -0.8,
    lineHeight: 41,
  },
  headlineAccent: {
    color: "#78C5E4",
  },
  description: {
    color: "#A9B6C5",
    fontSize: 16,
    lineHeight: 24,
    marginTop: 16,
  },
  actions: {
    gap: 12,
  },
  primaryButton: {
    minHeight: 64,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    backgroundColor: "#78C5E4",
    borderRadius: 13,
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: "#0D1723",
    fontSize: 17,
    fontWeight: "800",
  },
  secondaryButton: {
    minHeight: 64,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    backgroundColor: "#16283F",
    borderColor: "#34475D",
    borderWidth: 1,
    borderRadius: 13,
    paddingHorizontal: 18,
  },
  secondaryButtonText: {
    color: "#F3EEDF",
    fontSize: 16,
    fontWeight: "700",
  },
  sessionStatus: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 12,
  },
  sessionStatusText: {
    color: "#A9B6C5",
    fontSize: 12,
  },
  errorBox: {
    backgroundColor: "#2B2028",
    borderColor: "#6D3940",
    borderWidth: 1,
    borderRadius: 12,
    padding: 13,
    marginTop: 12,
  },
  errorText: {
    color: "#F2B8B5",
    fontSize: 13,
    lineHeight: 19,
  },
  retryButton: {
    alignSelf: "flex-start",
    paddingTop: 9,
  },
  retryText: {
    color: "#78C5E4",
    fontSize: 13,
    fontWeight: "700",
  },
  detailsCard: {
    backgroundColor: "#14253A",
    borderColor: "#2B4057",
    borderWidth: 1,
    borderRadius: 15,
    marginTop: 26,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  detailsToggle: {
    minHeight: 46,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  detailsHeading: {
    flex: 1,
  },
  detailsEyebrow: {
    color: "#78C5E4",
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  detailsTitle: {
    color: "#F3EEDF",
    fontSize: 16,
    fontWeight: "700",
    marginTop: 4,
  },
  toggleIcon: {
    color: "#78C5E4",
    fontSize: 25,
    paddingLeft: 12,
  },
  detailsList: {
    marginTop: 8,
  },
  detailRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    borderBottomColor: "#2B4057",
    borderBottomWidth: 1,
    gap: 11,
    paddingVertical: 12,
  },
  lastDetailRow: {
    borderBottomWidth: 0,
    paddingBottom: 2,
  },
  detailMark: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#78C5E4",
    marginTop: 5,
  },
  detailCopy: {
    flex: 1,
  },
  detailTitle: {
    color: "#F3EEDF",
    fontSize: 13,
    fontWeight: "700",
  },
  detailDescription: {
    color: "#A9B6C5",
    fontSize: 12,
    lineHeight: 18,
    marginTop: 3,
  },
  footer: {
    color: "#8292A6",
    fontSize: 11,
    lineHeight: 17,
    textAlign: "center",
    marginTop: 22,
  },
});