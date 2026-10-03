import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {addProjectMember, deleteProjectMember, getProject, listOrganizationMembers, listProjectMembers, updateProjectMember,
} from "../../../../api/projects";
import type {OrganizationMember, Project, ProjectMember, ProjectMemberRole,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";

const PAGE_SIZE = 5;

const roles: ProjectMemberRole[] = [
  "MANAGER",
  "ENGINEER",
  "SUPERVISOR",
  "SITE_MANAGER",
  "MEMBER",
];

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

export default function ProjectTeamScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const params = useLocalSearchParams<{ projectId?: string | string[] }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [organizationMembers, setOrganizationMembers] = useState<
    OrganizationMember[]
  >([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState<ProjectMemberRole>("MEMBER");
  const [availablePage, setAvailablePage] = useState(1);
  const [membersPage, setMembersPage] = useState(1);

  const canUpdate = permissions.includes("project.update");
  const canReadOrganization = permissions.includes("organization.read");

  const assignedIds = new Set(members.map((member) => member.user_id));
  const availableMembers = organizationMembers.filter(
    (member) => !assignedIds.has(member.id),
  );
  const availablePages = pageCount(availableMembers.length);
  const membersTotalPages = pageCount(members.length);
  const visibleAvailableMembers = paginate(availableMembers, availablePage);
  const visibleMembers = paginate(members, membersPage);

  const load = useCallback(async () => {
    if (!projectId) {
      setError(t("projectTeam.projectNotFound"));
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }

      const granted = user.role.permissions.map((permission) => permission.key);
      setPermissions(granted);
      setProject(await getProject(projectId));

      try {
        setMembers(await listProjectMembers(projectId));
        setMembersPage(1);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("projectTeam.loadMembersFailure"),
        );
      }

      if (granted.includes("organization.read")) {
        try {
          const organizationRows = await listOrganizationMembers();
          setOrganizationMembers(
            organizationRows.filter((member) => member.is_active),
          );
          setAvailablePage(1);
        } catch {
          setOrganizationMembers([]);
        }
      } else {
        setOrganizationMembers([]);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("projectTeam.loadProjectFailure"),
      );
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");

    try {
      await action();
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("projectTeam.actionFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function addMember() {
    if (!projectId || !memberUserId) {
      setError(t("projectTeam.chooseOrganizationMember"));
      return;
    }

    await run(() => addProjectMember(projectId, memberUserId, memberRole));
    setMemberUserId("");
  }

  async function changeMemberRole(userId: string, role: ProjectMemberRole) {
    if (!projectId) return;
    await run(() => updateProjectMember(projectId, userId, role));
  }

  function confirmRemoveMember(member: ProjectMember) {
    if (!projectId) return;

    const fullName =
      `${member.user.first_name} ${member.user.last_name}`.trim();

    Alert.alert(
      t("projectTeam.removeConfirmTitle"),
      t("projectTeam.removeConfirmMessage", { name: fullName }),
      [
        {
          text: t("projectTeam.cancel"),
          style: "cancel",
        },
        {
          text: t("projectTeam.remove"),
          style: "destructive",
          onPress: () =>
            void run(() =>
              deleteProjectMember(projectId, member.user_id),
            ),
        },
      ],
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("projectTeam.loading")}
        </Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, styles.headerTitle, isUrdu && styles.rtlText]}>
            {t("projectTeam.title")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error || t("projectTeam.projectNotFound")}
        </Text>
        <Pressable onPress={() => router.back()}>
          <Text style={[styles.link, isUrdu && styles.rtlText]}>
            {t("projectTeam.backToProject")}
          </Text>
        </Pressable>
      </View>
    );
  }

  if (!canUpdate) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("projectTeam.backToProjectName", {
                  name: project.name,
                })}
              </Text>
            </Pressable>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("projectTeam.title")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {t("projectTeam.accessDenied")}
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.page}
      keyboardShouldPersistTaps="handled"
    >
      <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
        <View style={styles.headerCopy}>
          <Pressable onPress={() => router.back()}>
            <Text style={[styles.link, isUrdu && styles.rtlText]}>
              {t("projectTeam.backToProjectName", { name: project.name })}
            </Text>
          </Pressable>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("projectTeam.title")}
          </Text>
        </View>
        <LanguageSwitcher />
      </View>

      {error ? (
        <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
      ) : null}

      {canReadOrganization ? (
        <>
          <View style={styles.sectionCard}>
            <Text style={[styles.section, isUrdu && styles.rtlText]}>
              {t("projectTeam.addMember")}
            </Text>
            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("projectTeam.chooseOrganizationMember")}
            </Text>

            {visibleAvailableMembers.map((member) => (
              <Chip
                key={member.id}
                label={`${member.first_name} ${member.last_name} · ${member.email}`}
                selected={memberUserId === member.id}
                onPress={() => setMemberUserId(member.id)}
                isUrdu={isUrdu}
              />
            ))}

            {availableMembers.length === 0 ? (
              <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                {t("projectTeam.noAvailableMembers")}
              </Text>
            ) : (
              <Pagination
                page={availablePage}
                pages={availablePages}
                isUrdu={isUrdu}
                onPrevious={() =>
                  setAvailablePage((page) => Math.max(1, page - 1))
                }
                onNext={() =>
                  setAvailablePage((page) =>
                    Math.min(availablePages, page + 1),
                  )
                }
              />
            )}

            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("projectTeam.projectRole")}
            </Text>
            <View style={[styles.chips, isUrdu && styles.rtlRow]}>
              {roles.map((role) => (
                <Chip
                  key={role}
                  label={t(`projectTeam.role.${role.toLowerCase()}`)}
                  selected={memberRole === role}
                  onPress={() => setMemberRole(role)}
                  isUrdu={isUrdu}
                />
              ))}
            </View>

            <Action
              title={t("projectTeam.addToProject")}
              onPress={() => void addMember()}
              isUrdu={isUrdu}
            />
          </View>
        </>
      ) : (
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("projectTeam.cannotReadOrganization")}
        </Text>
      )}

      <Text style={[styles.section, isUrdu && styles.rtlText]}>
        {t("projectTeam.currentMembers")}
      </Text>

      {members.length === 0 ? (
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("projectTeam.noMembers")}
        </Text>
      ) : (
        <>
          {visibleMembers.map((member) => (
            <View key={member.id} style={styles.card}>
              <Text style={[styles.itemTitle, isUrdu && styles.rtlText]}>
                {member.user.first_name} {member.user.last_name}
              </Text>
              <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                {member.user.email}
              </Text>
              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("projectTeam.memberRole", {
                  role: t(`projectTeam.role.${member.role.toLowerCase()}`),
                })}
              </Text>
              <View style={[styles.chips, isUrdu && styles.rtlRow]}>
                {roles.map((role) => (
                  <Chip
                    key={role}
                    label={t(`projectTeam.role.${role.toLowerCase()}`)}
                    selected={member.role === role}
                    onPress={() =>
                      void changeMemberRole(member.user_id, role)
                    }
                    isUrdu={isUrdu}
                  />
                ))}
              </View>
              <Action
                title={t("projectTeam.removeMember")}
                danger
                onPress={() => confirmRemoveMember(member)}
                isUrdu={isUrdu}
              />
            </View>
          ))}

          <Pagination
            page={membersPage}
            pages={membersTotalPages}
            isUrdu={isUrdu}
            onPrevious={() =>
              setMembersPage((page) => Math.max(1, page - 1))
            }
            onNext={() =>
              setMembersPage((page) =>
                Math.min(membersTotalPages, page + 1),
              )
            }
          />
        </>
      )}

      {busy ? (
        <View style={styles.busy}>
          <ActivityIndicator color={COLORS.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectTeam.saving")}
          </Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

function Pagination(props: {
  page: number;
  pages: number;
  isUrdu: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const { t } = useTranslation();

  return (
    <View style={[styles.pagination, props.isUrdu && styles.rtlRow]}>
      <Pressable
        style={[styles.pageButton, props.page <= 1 && styles.disabled]}
        onPress={props.onPrevious}
        disabled={props.page <= 1}
        accessibilityRole="button"
      >
        <Text style={[styles.pageButtonText, props.isUrdu && styles.rtlText]}>
          {t("projectTeam.previous")}
        </Text>
      </Pressable>
      <Text style={[styles.pageText, props.isUrdu && styles.rtlText]}>
        {t("projectTeam.pageOf", {
          page: props.page,
          pages: props.pages,
        })}
      </Text>
      <Pressable
        style={[
          styles.pageButton,
          props.page >= props.pages && styles.disabled,
        ]}
        onPress={props.onNext}
        disabled={props.page >= props.pages}
        accessibilityRole="button"
      >
        <Text style={[styles.pageButtonText, props.isUrdu && styles.rtlText]}>
          {t("projectTeam.next")}
        </Text>
      </Pressable>
    </View>
  );
}

function Chip(props: {
  label: string;
  selected: boolean;
  onPress: () => void;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[styles.chip, props.selected && styles.chipSelected]}
      onPress={props.onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: props.selected }}
    >
      <Text
        style={[
          styles.chipText,
          props.selected && styles.chipTextSelected,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.label}
      </Text>
    </Pressable>
  );
}

function Action(props: {
  title: string;
  onPress: () => void;
  danger?: boolean;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[styles.action, props.danger && styles.actionDanger]}
      onPress={props.onPress}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          props.danger && styles.actionDangerText,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.title}
      </Text>
    </Pressable>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#F7F3EC",
  navy: "#080D18",
  text: "#171C26",
  secondary: "#5C5347",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
  red: "#A63A32",
  redBackground: "#FBEAE7",
};

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 38, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8 },
  headerCopy: { flex: 1 },
  headerTitle: { flex: 1, marginBottom: 0 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 26, fontWeight: "800", marginTop: 10, marginBottom: 5 },
  sectionCard: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 10 },
  section: { color: COLORS.text, fontSize: 18, fontWeight: "800", marginTop: 18, marginBottom: 5 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 13, marginBottom: 5 },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 10 },
  itemTitle: { color: COLORS.text, fontSize: 15, fontWeight: "800" },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 6, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginVertical: 10, lineHeight: 19, fontSize: 13 },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 },
  chip: { borderWidth: 1, borderColor: COLORS.border, borderRadius: 99, backgroundColor: COLORS.surface, paddingHorizontal: 12, paddingVertical: 9, marginTop: 5 },
  chipSelected: { borderColor: COLORS.gold, backgroundColor: COLORS.surfaceMuted },
  chipText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700" },
  chipTextSelected: { color: COLORS.navy },
  action: { minHeight: 44, backgroundColor: COLORS.navy, borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 11, marginTop: 10 },
  actionDanger: { backgroundColor: COLORS.red },
  actionText: { color: COLORS.surface, fontSize: 13, fontWeight: "800", textAlign: "center" },
  actionDangerText: { color: COLORS.surface },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 10 },
  pageButton: { minHeight: 40, justifyContent: "center", paddingHorizontal: 12, borderRadius: 10, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  pageButtonText: { color: COLORS.navy, fontSize: 12, fontWeight: "800" },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", textAlign: "center" },
  disabled: { opacity: 0.5 },
  busy: { alignItems: "center", padding: 18, gap: 8 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});