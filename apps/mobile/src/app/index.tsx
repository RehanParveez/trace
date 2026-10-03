import { useCallback, useEffect, useState } from "react";
import { router } from "expo-router";
import {ActivityIndicator, Pressable, ScrollView, StatusBar, StyleSheet, Text, View,
} from "react-native";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../api/client";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function LandingScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

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
          : t("landing.sessionCheckFailure"),
      );
    } finally {
      setCheckingSession(false);
    }
  }, [t]);

  useEffect(() => {
    void checkSession();
  }, [checkSession]);

  return (
    <View style={styles.page}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.background} />

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={[styles.brandHeader, isUrdu && styles.rtlRow]}>
          <View style={styles.brandBlock}>
            <Text style={[styles.brand, isUrdu && styles.rtlText]}>
              {t("landing.brand")}
            </Text>
            <Text style={[styles.brandCaption, isUrdu && styles.rtlText]}>
              {t("landing.brandCaption")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={styles.hero}>
          <Text style={[styles.headline, isUrdu && styles.rtlText]}>
            {t("landing.headlineFirst")}
            {"\n"}
            <Text style={styles.headlineAccent}>
              {t("landing.headlineSecond")}
            </Text>
          </Text>

          <Text style={[styles.description, isUrdu && styles.rtlText]}>
            {t("landing.description")}
          </Text>
        </View>

        <View style={styles.actions}>
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push("/login")}
            android_ripple={{ color: "#9AD8EE" }}
            style={styles.primaryButton}
          >
            <Text style={[styles.primaryButtonText, isUrdu && styles.rtlText]}>
              {t("landing.signIn")}
            </Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            onPress={() => router.push("/register")}
            android_ripple={{ color: "#293D55" }}
            style={styles.secondaryButton}
          >
            <Text
              style={[styles.secondaryButtonText, isUrdu && styles.rtlText]}
            >
              {t("landing.createAccount")}
            </Text>
          </Pressable>
        </View>

        {checkingSession ? (
          <View style={[styles.sessionStatus, isUrdu && styles.rtlRow]}>
            <ActivityIndicator size="small" color={COLORS.accent} />
            <Text style={[styles.sessionStatusText, isUrdu && styles.rtlText]}>
              {t("landing.checkingAccount")}
            </Text>
          </View>
        ) : null}

        {sessionError ? (
          <View style={styles.errorBox}>
            <Text style={[styles.errorText, isUrdu && styles.rtlText]}>
              {sessionError}
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => void checkSession()}
              style={styles.retryButton}
            >
              <Text style={[styles.retryText, isUrdu && styles.rtlText]}>
                {t("landing.tryAgain")}
              </Text>
            </Pressable>
          </View>
        ) : null}

        <View style={styles.detailsCard}>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ expanded: showDetails }}
            accessibilityLabel={t("landing.detailsToggle")}
            onPress={() => setShowDetails((current) => !current)}
            style={[styles.detailsToggle, isUrdu && styles.rtlRow]}
          >
            <View style={styles.detailsHeading}>
              <Text style={[styles.detailsEyebrow, isUrdu && styles.rtlText]}>
                {t("landing.detailsEyebrow")}
              </Text>
              <Text style={[styles.detailsTitle, isUrdu && styles.rtlText]}>
                {t("landing.detailsTitle")}
              </Text>
            </View>
            <Text style={styles.toggleIcon}>
              {showDetails ? "−" : "+"}
            </Text>
          </Pressable>

          {showDetails ? (
            <View style={styles.detailsList}>
              <DetailRow
                title={t("landing.detailRecordsTitle")}
                description={t("landing.detailRecordsDescription")}
                isUrdu={isUrdu}
              />
              <DetailRow
                title={t("landing.detailSiteTitle")}
                description={t("landing.detailSiteDescription")}
                isUrdu={isUrdu}
              />
              <DetailRow
                title={t("landing.detailApprovalsTitle")}
                description={t("landing.detailApprovalsDescription")}
                last
                isUrdu={isUrdu}
              />
            </View>
          ) : null}
        </View>

        <Text style={[styles.footer, isUrdu && styles.rtlText]}>
          {t("landing.footer")}
        </Text>
      </ScrollView>
    </View>
  );
}

function DetailRow(props: {
  title: string;
  description: string;
  last?: boolean;
  isUrdu: boolean;
}) {
  return (
    <View
      style={[
        styles.detailRow,
        props.last && styles.lastDetailRow,
        props.isUrdu && styles.rtlRow,
      ]}
    >
      <View style={styles.detailMark} />
      <View style={styles.detailCopy}>
        <Text style={[styles.detailTitle, props.isUrdu && styles.rtlText]}>
          {props.title}
        </Text>
        <Text
          style={[
            styles.detailDescription,
            props.isUrdu && styles.rtlText,
          ]}
        >
          {props.description}
        </Text>
      </View>
    </View>
  );
}

const COLORS = {
  background: "#0D1723",
  surface: "#14253A",
  surfaceLight: "#16283F",
  text: "#F3EEDF",
  secondary: "#A9B6C5",
  muted: "#8292A6",
  border: "#2B4057",
  accent: "#78C5E4",
  gold: "#D9A441",
  errorBackground: "#2B2028",
  errorBorder: "#6D3940",
  errorText: "#F2B8B5",
};

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: COLORS.background },
  content: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 30, paddingBottom: 24 },
  brandHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 42 },
  brandBlock: { flex: 1 },
  rtlRow: { flexDirection: "row-reverse" },
  brand: { color: COLORS.text, fontSize: 21, fontWeight: "900", letterSpacing: 2.4 },
  brandCaption: { color: COLORS.muted, fontSize: 10, fontWeight: "700", letterSpacing: 1.5, marginTop: 5 },
  hero: { marginBottom: 28 },
  headline: { color: COLORS.text, fontSize: 34, fontWeight: "800", letterSpacing: -0.8, lineHeight: 41 },
  headlineAccent: { color: COLORS.accent },
  description: { color: COLORS.secondary, fontSize: 15, lineHeight: 24, marginTop: 16 },
  actions: { gap: 12 },
  primaryButton: { minHeight: 58, alignItems: "center", justifyContent: "center", overflow: "hidden", backgroundColor: COLORS.accent, borderRadius: 13, paddingHorizontal: 18 },
  primaryButtonText: { color: COLORS.background, fontSize: 16, fontWeight: "800", textAlign: "center" },
  secondaryButton: { minHeight: 58, alignItems: "center", justifyContent: "center", overflow: "hidden", backgroundColor: COLORS.surfaceLight, borderColor: "#34475D", borderWidth: 1, borderRadius: 13, paddingHorizontal: 18 },
  secondaryButtonText: { color: COLORS.text, fontSize: 15, fontWeight: "700", textAlign: "center" },
  sessionStatus: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 12 },
  sessionStatusText: { color: COLORS.secondary, fontSize: 12 },
  errorBox: { backgroundColor: COLORS.errorBackground, borderColor: COLORS.errorBorder, borderWidth: 1, borderRadius: 12, padding: 13, marginTop: 12 },
  errorText: { color: COLORS.errorText, fontSize: 13, lineHeight: 19 },
  retryButton: { alignSelf: "flex-start", paddingTop: 9 },
  retryText: { color: COLORS.accent, fontSize: 13, fontWeight: "700" },
  detailsCard: { backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, borderRadius: 15, marginTop: 26, paddingHorizontal: 16, paddingVertical: 14 },
  detailsToggle: { minHeight: 46, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  detailsHeading: { flex: 1 },
  detailsEyebrow: { color: COLORS.accent, fontSize: 9, fontWeight: "800", letterSpacing: 1.5 },
  detailsTitle: { color: COLORS.text, fontSize: 16, fontWeight: "700", marginTop: 4 },
  toggleIcon: { color: COLORS.accent, fontSize: 25, paddingLeft: 12 },
  detailsList: { marginTop: 8 },
  detailRow: { flexDirection: "row", alignItems: "flex-start", borderBottomColor: COLORS.border, borderBottomWidth: 1, gap: 11, paddingVertical: 12 },
  lastDetailRow: { borderBottomWidth: 0, paddingBottom: 2 },
  detailMark: { width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.accent, marginTop: 5 },
  detailCopy: { flex: 1 },
  detailTitle: { color: COLORS.text, fontSize: 13, fontWeight: "700" },
  detailDescription: { color: COLORS.secondary, fontSize: 12, lineHeight: 18, marginTop: 3 },
  footer: { color: COLORS.muted, fontSize: 11, lineHeight: 17, textAlign: "center", marginTop: 22 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});