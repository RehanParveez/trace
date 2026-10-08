import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listReviewIssues, resolveReviewIssue } from "../../../../api/boqEngine";
import type { ReviewIssue, ReviewIssueStatus } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

const STATUSES: ReviewIssueStatus[] = ["OPEN", "RESOLVED", "WAIVED"];

export default function ReviewIssuesScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; versionId?: string }>();
  const projectId = first(params.projectId);
  const versionId = first(params.versionId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [status, setStatus] = useState<ReviewIssueStatus>("OPEN");
  const [issues, setIssues] = useState<ReviewIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [activeId, setActiveId] = useState("");
  const [note, setNote] = useState("");

  const canResolve = hasPerm(permissions, PERM.REVIEW_RESOLVE);

  const load = useCallback(
    async (silent = false) => {
      if (!projectId) {
        setError(tx("issues.projectMissing", "Project not found."));
        setLoading(false);
        return;
      }
      if (!silent) setLoading(true);
      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }
        setPermissions(user.role.permissions.map((p) => p.key));
        setIssues(
          await listReviewIssues(projectId, {
            status,
            boq_version_id: versionId,
          }),
        );
      } catch (err) {
        setError(describeError(err, tx("issues.loadFailure", "Could not load review issues.")));
      } finally {
        setLoading(false);
      }
    },
    [projectId, versionId, status],
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(issue: ReviewIssue, next: "RESOLVED" | "WAIVED") {
    if (next === "WAIVED" && !note.trim()) {
      setError(tx("issues.waiveNote", "Enter a note to waive an issue."));
      return;
    }
    setBusy(true);
    setError("");
    try {
      await resolveReviewIssue(issue.id, next, note);
      setActiveId("");
      setNote("");
      await load(true);
    } catch (err) {
      setError(describeError(err, tx("issues.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>
                {tx("issues.back", "Back")}
              </Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>
              {tx("issues.title", "Review issues")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {STATUSES.map((value) => (
            <Action
              key={value}
              title={tx(`issues.status.${value.toLowerCase()}`, value)}
              secondary={status !== value}
              isUrdu={isUrdu}
              onPress={() => {
                setStatus(value);
                setActiveId("");
              }}
            />
          ))}
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {issues.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("issues.none", "No issues in this state.")}
          </Text>
        ) : null}

        {issues.map((issue) => (
          <View key={issue.id} style={ui.card}>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Badge
                label={issue.severity}
                tone={issue.severity === "error" ? "bad" : issue.severity === "warning" ? "warn" : "neutral"}
              />
              {issue.blocks !== "NONE" ? (
                <Badge
                  label={tx("issues.blocks", "Blocks {{what}}", { what: issue.blocks.toLowerCase() })}
                  tone="bad"
                />
              ) : null}
            </View>
            <Text style={[ui.itemTitle, { marginTop: 8 }, isUrdu && ui.rtlText]}>{issue.code}</Text>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>{issue.message}</Text>
            {issue.suggested_fix ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("issues.fix", "Suggested fix: {{fix}}", { fix: issue.suggested_fix })}
              </Text>
            ) : null}
            {issue.resolution_note ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>{issue.resolution_note}</Text>
            ) : null}

            {issue.status === "OPEN" && canResolve ? (
              activeId === issue.id ? (
                <>
                  <Field
                    label={tx("issues.note", "Note (required to waive)")}
                    value={note}
                    onChangeText={setNote}
                    isUrdu={isUrdu}
                  />
                  <View style={[ui.row, isUrdu && ui.rtlRow]}>
                    <Action
                      title={tx("issues.resolve", "Resolve")}
                      disabled={busy}
                      isUrdu={isUrdu}
                      onPress={() => void submit(issue, "RESOLVED")}
                    />
                    <Action
                      title={tx("issues.waive", "Waive")}
                      secondary
                      disabled={busy}
                      isUrdu={isUrdu}
                      onPress={() => void submit(issue, "WAIVED")}
                    />
                    <Action
                      title={tx("drawingsBoq.cancel", "Cancel")}
                      secondary
                      isUrdu={isUrdu}
                      onPress={() => {
                        setActiveId("");
                        setNote("");
                      }}
                    />
                  </View>
                </>
              ) : (
                <Action
                  title={tx("issues.act", "Resolve or waive")}
                  secondary
                  isUrdu={isUrdu}
                  onPress={() => {
                    setActiveId(issue.id);
                    setNote("");
                  }}
                />
              )
            ) : null}
          </View>
        ))}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}