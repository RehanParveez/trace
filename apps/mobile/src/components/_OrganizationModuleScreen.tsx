import { useCallback, useEffect, useMemo, useState } from "react";
import {ActivityIndicator, Alert, KeyboardAvoidingView, Modal, Platform, Pressable, RefreshControl, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from "react-native";
import { Link, router } from "expo-router";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "../components/LanguageSwitcher";
import i18n from "../i18n";
import { restoreSession } from "../api/client";
import {createInvitation, createRole, deleteRole, getAISettings, getOrganization, listInvitations, listMembers, listPermissions, listRoles, revokeInvitation, updateAISettings, updateMemberRole, updateMemberStatus,
  updateOrganization, updateRole,
} from "../api/organizations";
import type {AuthPermission, Organization, OrganizationInvitation, OrganizationMember, OrganizationRole, RolePayload,
} from "../api/types";

const ORGANIZATION_READ = "organization.read";
const ORGANIZATION_MANAGE = "organization.manage";
const MEMBERS_MANAGE = "organization.members.manage";

type OrganizationSection =
  | "overview"
  | "settings"
  | "members"
  | "roles"
  | "invitations";

type EditorMode = "invite" | "role" | null;

type InvitationState =
  | "accepted"
  | "revoked"
  | "expired"
  | "pending";

export function OrganizationModuleScreen({
  section,
}: {
  section: OrganizationSection;
}) {
  const { t, i18n: activeI18n } = useTranslation();
  const isUrdu = activeI18n.resolvedLanguage === "ur";

  const [organization, setOrganization] =
    useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [roles, setRoles] = useState<OrganizationRole[]>([]);
  const [permissions, setPermissions] = useState<AuthPermission[]>([]);
  const [invitations, setInvitations] = useState<
    OrganizationInvitation[]
  >([]);

  const [canManageOrganization, setCanManageOrganization] =
    useState(false);
  const [canManageMembers, setCanManageMembers] = useState(false);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [search, setSearch] = useState("");
  const [memberFilter, setMemberFilter] = useState<
    "all" | "active" | "inactive"
  >("all");
  const [invitationFilter, setInvitationFilter] = useState<
    "pending" | "all"
  >("pending");

  const [editorMode, setEditorMode] =
    useState<EditorMode>(null);
  const [selectedMember, setSelectedMember] =
    useState<OrganizationMember | null>(null);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRoleId, setInviteRoleId] = useState("");

  const [editingRole, setEditingRole] =
    useState<OrganizationRole | null>(null);
  const [roleName, setRoleName] = useState("");
  const [roleDescription, setRoleDescription] = useState("");
  const [selectedPermissionIds, setSelectedPermissionIds] =
    useState<string[]>([]);
  const [expandedPermissionGroups, setExpandedPermissionGroups] =
    useState<string[]>([]);

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [currency, setCurrency] = useState("");

  const load = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");
      setNotice("");

      try {
        const user = await restoreSession();

        if (!user) {
          router.replace("/login");
          return;
        }

        const permissionKeys =
          user.role?.permissions?.map(
            (permission) => permission.key,
          ) ?? [];

        const mayManageOrganization = permissionKeys.includes(
          ORGANIZATION_MANAGE,
        );
        const mayManageMembers =
          permissionKeys.includes(MEMBERS_MANAGE);

        setCanManageOrganization(mayManageOrganization);
        setCanManageMembers(mayManageMembers);

        if (!permissionKeys.includes(ORGANIZATION_READ)) {
          setError(t("organization.accessDenied"));
          return;
        }

        if (section === "overview") {
          const [org, memberRows, roleRows] =
            await Promise.all([
              getOrganization(),
              listMembers(0, 100),
              listRoles(),
            ]);

          setOrganization(org);
          setMembers(memberRows);
          setRoles(roleRows);
          return;
        }

        if (section === "settings") {
          const [org, aiSettings] = await Promise.all([
            getOrganization(),
            getAISettings(),
          ]);

          const updatedOrganization = {
            ...org,
            ai_enabled: aiSettings.ai_enabled,
          };

          setOrganization(updatedOrganization);
          setName(updatedOrganization.name);
          setSlug(updatedOrganization.slug);
          setCurrency(updatedOrganization.currency);
          return;
        }

        if (section === "members") {
          const [memberRows, roleRows] = await Promise.all([
            listMembers(0, 100),
            listRoles(),
          ]);

          setMembers(memberRows);
          setRoles(roleRows);
          return;
        }

        if (section === "roles") {
          const roleRows = await listRoles();
          setRoles(roleRows);

          if (mayManageOrganization) {
            setPermissions(await listPermissions());
          } else {
            setPermissions([]);
          }

          return;
        }

        if (section === "invitations") {
          if (!mayManageMembers) {
            setInvitations([]);
            setError(
              t("organization.invitationsAccessDenied"),
            );
            return;
          }

          const [invitationRows, roleRows] =
            await Promise.all([
              listInvitations(0, 100),
              listRoles(),
            ]);

          setInvitations(invitationRows);
          setRoles(roleRows);
        }
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : t("organization.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [section],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const perform = useCallback(
    async (
      action: () => Promise<unknown>,
      successMessage: string,
    ) => {
      setBusy(true);
      setError("");
      setNotice("");

      try {
        await action();
        setNotice(successMessage);
        await load(true);
        return true;
      } catch (actionError) {
        setError(
          actionError instanceof Error
            ? actionError.message
            : t("organization.actionFailure"),
        );
        return false;
      } finally {
        setBusy(false);
      }
    },
    [load, t],
  );

  const saveOrganization = async () => {
    const cleanName = name.trim();
    const cleanSlug = slug.trim().toLowerCase();
    const cleanCurrency = currency.trim().toUpperCase();

    if (!cleanName || !cleanSlug || !cleanCurrency) {
      setError(t("organization.enterOrganizationFields"));
      return;
    }

    await perform(
      () =>
        updateOrganization({
          name: cleanName,
          slug: cleanSlug,
          currency: cleanCurrency,
        }),
      t("organization.detailsSaved"),
    );
  };

  const changeAISetting = async (enabled: boolean) => {
    const succeeded = await perform(
      () => updateAISettings(enabled),
      t("organization.aiSettingUpdated"),
    );

    if (succeeded) {
      setOrganization((current) =>
        current
          ? { ...current, ai_enabled: enabled }
          : current,
      );
    }
  };

  const visibleMembers = useMemo(() => {
    const query = search.trim().toLowerCase();

    return members.filter((member) => {
      const matchesQuery =
        !query ||
        `${member.first_name} ${member.last_name} ${member.email}`
          .toLowerCase()
          .includes(query);

      const matchesStatus =
        memberFilter === "all" ||
        (memberFilter === "active" && member.is_active) ||
        (memberFilter === "inactive" && !member.is_active);

      return matchesQuery && matchesStatus;
    });
  }, [members, memberFilter, search]);

  const submitMemberRole = async (roleId: string) => {
    if (!selectedMember) {
      return;
    }

    const succeeded = await perform(
      () => updateMemberRole(selectedMember.id, roleId),
      t("organization.memberRoleUpdated"),
    );

    if (succeeded) {
      setSelectedMember(null);
    }
  };

  const toggleMemberStatus = (member: OrganizationMember) => {
    const nextActive = !member.is_active;
    const fullName =
      `${member.first_name} ${member.last_name}`.trim() ||
      member.email;

    Alert.alert(
      nextActive
        ? t("organization.activateMemberTitle")
        : t("organization.deactivateMemberTitle"),
      t("organization.memberAccessWillChange", {
        name: fullName,
        access: nextActive
          ? t("organization.accessEnabled")
          : t("organization.accessDisabled"),
      }),
      [
        {
          text: t("organization.keepCurrentStatus"),
          style: "cancel",
        },
        {
          text: nextActive
            ? t("organization.activate")
            : t("organization.deactivate"),
          style: nextActive ? "default" : "destructive",
          onPress: () => {
            void perform(
              () =>
                updateMemberStatus(member.id, nextActive),
              nextActive
                ? t("organization.memberActivated")
                : t("organization.memberDeactivated"),
            );
          },
        },
      ],
    );
  };

  const openRoleEditor = (role?: OrganizationRole) => {
    setEditingRole(role ?? null);
    setRoleName(role?.name ?? "");
    setRoleDescription(role?.description ?? "");
    setSelectedPermissionIds(
      role?.permissions.map((permission) => permission.id) ??
        [],
    );
    setExpandedPermissionGroups([]);
    setEditorMode("role");
  };

  const saveRole = async () => {
    const cleanName = roleName.trim();

    if (!cleanName) {
      setError(t("organization.enterRoleName"));
      return;
    }

    const payload: RolePayload = {
      name: cleanName,
      description: roleDescription.trim() || null,
      permission_ids: selectedPermissionIds,
    };

    const succeeded = await perform(
      () =>
        editingRole
          ? updateRole(editingRole.id, payload)
          : createRole(payload),
      editingRole
        ? t("organization.roleUpdated")
        : t("organization.roleCreated"),
    );

    if (succeeded) {
      setEditorMode(null);
      setEditingRole(null);
    }
  };

  const confirmDeleteRole = (role: OrganizationRole) => {
    Alert.alert(
      t("organization.deleteRoleTitle"),
      t("organization.deleteRoleConfirm", {
        name: role.name,
      }),
      [
        {
          text: t("organization.cancel"),
          style: "cancel",
        },
        {
          text: t("organization.deleteRole"),
          style: "destructive",
          onPress: () => {
            void perform(
              () => deleteRole(role.id),
              t("organization.roleDeleted"),
            );
          },
        },
      ],
    );
  };

  const sendInvitation = async () => {
    const cleanEmail = inviteEmail.trim().toLowerCase();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      setError(t("organization.enterValidEmail"));
      return;
    }

    if (!inviteRoleId) {
      setError(t("organization.chooseInvitationRole"));
      return;
    }

    const succeeded = await perform(
      () => createInvitation(cleanEmail, inviteRoleId),
      t("organization.invitationSent"),
    );

    if (succeeded) {
      setEditorMode(null);
      setInviteEmail("");
      setInviteRoleId("");
    }
  };

  const confirmRevokeInvitation = (
    invitation: OrganizationInvitation,
  ) => {
    Alert.alert(
      t("organization.revokeInvitationTitle"),
      t("organization.revokeInvitationConfirm", {
        email: invitation.email,
      }),
      [
        {
          text: t("organization.keepInvitation"),
          style: "cancel",
        },
        {
          text: t("organization.revoke"),
          style: "destructive",
          onPress: () => {
            void perform(
              () => revokeInvitation(invitation.id),
              t("organization.invitationRevoked"),
            );
          },
        },
      ],
    );
  };

  const filteredInvitations = invitations.filter(
    (invitation) => {
      if (invitationFilter === "all") {
        return true;
      }

      return invitationState(invitation) === "pending";
    },
  );

  if (loading) {
    return (
      <View style={styles.loadingScreen}>
        <ActivityIndicator size="large" color={colors.navy} />
        <Text style={styles.helperText}>
          {t("organization.loading")}
        </Text>
      </View>
    );
  }

  const titles: Record<OrganizationSection, string> = {
    overview: t("organization.overviewTitle"),
    settings: t("organization.settingsTitle"),
    members: t("organization.membersTitle"),
    roles: t("organization.rolesTitle"),
    invitations: t("organization.invitationsTitle"),
  };

  const subtitles: Record<OrganizationSection, string> = {
    overview: t("organization.overviewSubtitle"),
    settings: t("organization.settingsSubtitle"),
    members: t("organization.membersSubtitle"),
    roles: t("organization.rolesSubtitle"),
    invitations: t("organization.invitationsSubtitle"),
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        style={[styles.screen, isUrdu && { direction: "rtl" }]}
        contentContainerStyle={[
          styles.content,
          isUrdu && { direction: "rtl" },
        ]}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => void load(true)}
            tintColor={colors.navy}
          />
        }
      >
        <View style={styles.headingRow}>
          <View style={styles.headingCopy}>
            <Text style={styles.eyebrow}>
              {t("organization.eyebrow")}
            </Text>
            <Text style={styles.pageTitle}>{titles[section]}</Text>
            <Text style={styles.pageSubtitle}>
              {subtitles[section]}
            </Text>
          </View>

          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <LanguageSwitcher />
            <Pressable
              onPress={() => void load(true)}
              accessibilityRole="button"
              accessibilityLabel={t(
                "organization.refreshAccessibility",
              )}
              disabled={refreshing || busy}
              style={styles.refreshButton}
            >
              <Text style={styles.refreshText}>
                {refreshing
                  ? "…"
                  : t("organization.refresh")}
              </Text>
            </Pressable>
          </View>
        </View>

        {error ? (
          <View
            style={styles.errorBox}
            accessibilityRole="alert"
          >
            <Text style={styles.errorTitle}>
              {t("organization.attention")}
            </Text>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        {notice ? (
          <View
            style={styles.noticeBox}
            accessibilityRole="alert"
          >
            <Text style={styles.noticeText}>{notice}</Text>
          </View>
        ) : null}

        {section === "overview" ? (
          <Overview
            organization={organization}
            memberCount={members.length}
            roles={roles}
            canManageMembers={canManageMembers}
          />
        ) : null}

        {section === "settings" ? (
          <Settings
            organization={organization}
            name={name}
            slug={slug}
            currency={currency}
            canManageOrganization={canManageOrganization}
            busy={busy}
            onName={setName}
            onSlug={setSlug}
            onCurrency={setCurrency}
            onSave={() => void saveOrganization()}
            onAIChange={(value) =>
              void changeAISetting(value)
            }
          />
        ) : null}

        {section === "members" ? (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <View>
                <Text style={styles.sectionTitle}>
                  {t("organization.membersSection")}
                </Text>
                <Text style={styles.sectionHint}>
                  {members.length === 100
                    ? t("organization.firstHundredMembers")
                    : t("organization.memberCount", {
                        count: members.length,
                      })}
                </Text>
              </View>
            </View>

            <TextInput
              style={styles.input}
              value={search}
              onChangeText={setSearch}
              placeholder={t(
                "organization.searchNameEmail",
              )}
              placeholderTextColor={colors.muted}
              autoCapitalize="none"
              accessibilityLabel={t(
                "organization.searchMembersAccessibility",
              )}
            />

            <View style={styles.filterRow}>
              <FilterChip
                label={t("organization.filterAll")}
                selected={memberFilter === "all"}
                onPress={() => setMemberFilter("all")}
              />
              <FilterChip
                label={t("organization.filterActive")}
                selected={memberFilter === "active"}
                onPress={() => setMemberFilter("active")}
              />
              <FilterChip
                label={t("organization.filterInactive")}
                selected={memberFilter === "inactive"}
                onPress={() =>
                  setMemberFilter("inactive")
                }
              />
            </View>

            {visibleMembers.length ? (
              visibleMembers.map((member) => (
                <View
                  key={member.id}
                  style={styles.personCard}
                >
                  <View style={styles.personTop}>
                    <View style={styles.avatar}>
                      <Text style={styles.avatarText}>
                        {initials(
                          member.first_name,
                          member.last_name,
                        )}
                      </Text>
                    </View>

                    <View style={styles.personCopy}>
                      <Text style={styles.cardTitle}>
                        {`${member.first_name} ${member.last_name}`.trim() ||
                          member.email}
                      </Text>
                      <Text style={styles.cardDescription}>
                        {member.email}
                      </Text>
                    </View>

                    <StatusBadge
                      label={
                        member.is_active
                          ? t("organization.active")
                          : t("organization.inactive")
                      }
                      active={member.is_active}
                    />
                  </View>

                  <View style={styles.personMeta}>
                    <Text style={styles.metaPill}>
                      {member.role.name}
                    </Text>
                    <Text style={styles.metaText}>
                      {member.is_verified
                        ? t("organization.emailVerified")
                        : t("organization.unverified")}
                    </Text>
                  </View>

                  {canManageMembers ? (
                    <View style={styles.actionRow}>
                      <Button
                        label={t(
                          "organization.changeRole",
                        )}
                        variant="secondary"
                        disabled={busy}
                        onPress={() =>
                          setSelectedMember(member)
                        }
                      />

                      <Button
                        label={
                          member.is_active
                            ? t("organization.deactivate")
                            : t("organization.activate")
                        }
                        variant={
                          member.is_active
                            ? "danger"
                            : "secondary"
                        }
                        disabled={busy}
                        onPress={() =>
                          toggleMemberStatus(member)
                        }
                      />
                    </View>
                  ) : null}
                </View>
              ))
            ) : (
              <EmptyState
                title={t("organization.noMembersMatch")}
                description={
                  search || memberFilter !== "all"
                    ? t(
                        "organization.tryDifferentMemberFilter",
                      )
                    : t(
                        "organization.membersWillAppear",
                      )
                }
              />
            )}
          </View>
        ) : null}

        {section === "roles" ? (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <View style={styles.headingCopy}>
                <Text style={styles.sectionTitle}>
                  {t("organization.rolesSection")}
                </Text>
                <Text style={styles.sectionHint}>
                  {t("organization.rolesSubtitle")}
                </Text>
              </View>

              {canManageOrganization ? (
                <Button
                  label={t("organization.createRole")}
                  variant="primary"
                  disabled={busy}
                  onPress={() => openRoleEditor()}
                />
              ) : null}
            </View>

            {roles.length ? (
              roles.map((role) => (
                <RoleCard
                  key={role.id}
                  role={role}
                  canManage={canManageOrganization}
                  busy={busy}
                  onEdit={() => openRoleEditor(role)}
                  onDelete={() => confirmDeleteRole(role)}
                />
              ))
            ) : (
              <EmptyState
                title={t("organization.noRolesFound")}
                description={t(
                  "organization.rolesWillAppear",
                )}
              />
            )}
          </View>
        ) : null}

        {section === "invitations" ? (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <View style={styles.headingCopy}>
                <Text style={styles.sectionTitle}>
                  {t("organization.invitationsSection")}
                </Text>
                <Text style={styles.sectionHint}>
                  {canManageMembers
                    ? t(
                        "organization.managePendingInvitations",
                      )
                    : t(
                        "organization.invitationsRestricted",
                      )}
                </Text>
              </View>

              {canManageMembers ? (
                <Button
                  label={t("organization.invite")}
                  variant="primary"
                  disabled={busy || roles.length === 0}
                  onPress={() => {
                    setError("");
                    setEditorMode("invite");
                  }}
                />
              ) : null}
            </View>

            {canManageMembers ? (
              <>
                <View style={styles.filterRow}>
                  <FilterChip
                    label={t("organization.pending")}
                    selected={
                      invitationFilter === "pending"
                    }
                    onPress={() =>
                      setInvitationFilter("pending")
                    }
                  />

                  <FilterChip
                    label={t("organization.all")}
                    selected={invitationFilter === "all"}
                    onPress={() =>
                      setInvitationFilter("all")
                    }
                  />
                </View>

                {filteredInvitations.length ? (
                  filteredInvitations.map((invitation) => {
                    const state =
                      invitationState(invitation);

                    return (
                      <View
                        key={invitation.id}
                        style={styles.invitationCard}
                      >
                        <View style={styles.invitationTop}>
                          <View style={styles.personCopy}>
                            <Text style={styles.cardTitle}>
                              {invitation.email}
                            </Text>
                            <Text
                              style={styles.cardDescription}
                            >
                              {t(
                                "organization.invitedDate",
                                {
                                  date: formatDate(
                                    invitation.created_at,
                                  ),
                                },
                              )}
                            </Text>
                          </View>

                          <StatusBadge
                            label={t(
                              `organization.invitationState.${state}`,
                            )}
                            active={state === "pending"}
                          />
                        </View>

                        <Text style={styles.cardDescription}>
                          {t(
                            "organization.expiresDate",
                            {
                              date: formatDate(
                                invitation.expires_at,
                              ),
                            },
                          )}
                        </Text>

                        {state === "pending" ? (
                          <Button
                            label={t(
                              "organization.revokeInvitation",
                            )}
                            variant="danger"
                            disabled={busy}
                            onPress={() =>
                              confirmRevokeInvitation(
                                invitation,
                              )
                            }
                          />
                        ) : null}
                      </View>
                    );
                  })
                ) : (
                  <EmptyState
                    title={
                      invitationFilter === "pending"
                        ? t(
                            "organization.noPendingInvitations",
                          )
                        : t(
                            "organization.noInvitationsYet",
                          )
                    }
                    description={t(
                      "organization.sentInvitationsAppear",
                    )}
                  />
                )}
              </>
            ) : null}
          </View>
        ) : null}

        {busy ? (
          <View style={styles.busyRow}>
            <ActivityIndicator
              size="small"
              color={colors.navy}
            />
            <Text style={styles.helperText}>
              {t("organization.saving")}
            </Text>
          </View>
        ) : null}
      </ScrollView>

      <Modal
        visible={Boolean(selectedMember)}
        transparent
        animationType="slide"
        onRequestClose={() => setSelectedMember(null)}
      >
        <ModalBackdrop
          onClose={() => setSelectedMember(null)}
        >
          <View style={styles.sheet}>
            <View style={styles.sheetHandle} />

            <Text style={styles.sheetTitle}>
              {t("organization.changeMemberRole")}
            </Text>

            <Text style={styles.sheetSubtitle}>
              {selectedMember?.email}
            </Text>

            <ScrollView style={styles.sheetList}>
              {roles.map((role) => (
                <Pressable
                  key={role.id}
                  onPress={() =>
                    void submitMemberRole(role.id)
                  }
                  disabled={
                    busy ||
                    selectedMember?.role.id === role.id
                  }
                  style={[
                    styles.choiceRow,
                    selectedMember?.role.id === role.id &&
                      styles.choiceRowSelected,
                  ]}
                  accessibilityRole="button"
                >
                  <View style={styles.choiceCopy}>
                    <Text style={styles.choiceTitle}>
                      {role.name}
                    </Text>

                    {role.description ? (
                      <Text
                        style={styles.choiceDescription}
                      >
                        {role.description}
                      </Text>
                    ) : null}
                  </View>

                  <Text style={styles.choiceMark}>
                    {selectedMember?.role.id === role.id
                      ? t("organization.current")
                      : "›"}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>

            <Button
              label={t("organization.close")}
              variant="secondary"
              onPress={() => setSelectedMember(null)}
            />
          </View>
        </ModalBackdrop>
      </Modal>

      <Modal
        visible={editorMode !== null}
        transparent
        animationType="slide"
        onRequestClose={() => setEditorMode(null)}
      >
        <ModalBackdrop
          onClose={() => setEditorMode(null)}
        >
          {editorMode === "invite" ? (
            <View style={styles.sheet}>
              <View style={styles.sheetHandle} />

              <Text style={styles.sheetTitle}>
                {t("organization.inviteMember")}
              </Text>

              <Text style={styles.sheetSubtitle}>
                {t("organization.inviteMemberDescription")}
              </Text>

              <Text style={styles.fieldLabel}>
                {t("organization.emailAddress")}
              </Text>

              <TextInput
                style={styles.input}
                value={inviteEmail}
                onChangeText={setInviteEmail}
                placeholder={t(
                  "organization.emailPlaceholder",
                )}
                placeholderTextColor={colors.muted}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />

              <Text style={styles.fieldLabel}>
                {t("organization.organizationRole")}
              </Text>

              <ScrollView style={styles.sheetList}>
                {roles.map((role) => (
                  <Pressable
                    key={role.id}
                    onPress={() => setInviteRoleId(role.id)}
                    style={[
                      styles.choiceRow,
                      inviteRoleId === role.id &&
                        styles.choiceRowSelected,
                    ]}
                    accessibilityRole="button"
                  >
                    <View style={styles.choiceCopy}>
                      <Text style={styles.choiceTitle}>
                        {role.name}
                      </Text>

                      {role.description ? (
                        <Text
                          style={styles.choiceDescription}
                        >
                          {role.description}
                        </Text>
                      ) : null}
                    </View>

                    <Text style={styles.choiceMark}>
                      {inviteRoleId === role.id
                        ? t("organization.selected")
                        : "›"}
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>

              <Button
                label={
                  busy
                    ? t("organization.sending")
                    : t("organization.sendInvitation")
                }
                variant="primary"
                disabled={
                  busy ||
                  !inviteRoleId ||
                  !inviteEmail.trim()
                }
                onPress={() => void sendInvitation()}
              />

              <Button
                label={t("organization.cancel")}
                variant="secondary"
                disabled={busy}
                onPress={() => setEditorMode(null)}
              />
            </View>
          ) : editorMode === "role" ? (
            <View style={styles.sheet}>
              <View style={styles.sheetHandle} />

              <Text style={styles.sheetTitle}>
                {editingRole
                  ? t("organization.editRole")
                  : t("organization.createRole")}
              </Text>

              <Text style={styles.sheetSubtitle}>
                {t("organization.roleEditorDescription")}
              </Text>

              <ScrollView
                style={styles.roleEditorScroll}
                keyboardShouldPersistTaps="handled"
              >
                <Text style={styles.fieldLabel}>
                  {t("organization.roleName")}
                </Text>

                <TextInput
                  style={styles.input}
                  value={roleName}
                  onChangeText={setRoleName}
                  placeholder={t(
                    "organization.roleNamePlaceholder",
                  )}
                  placeholderTextColor={colors.muted}
                />

                <Text style={styles.fieldLabel}>
                  {t("organization.descriptionOptional")}
                </Text>

                <TextInput
                  style={[
                    styles.input,
                    styles.multilineInput,
                  ]}
                  value={roleDescription}
                  onChangeText={setRoleDescription}
                  placeholder={t(
                    "organization.roleDescriptionPlaceholder",
                  )}
                  placeholderTextColor={colors.muted}
                  multiline
                  textAlignVertical="top"
                />

                <Text style={styles.fieldLabel}>
                  {t("organization.permissions")}
                </Text>

                <PermissionGroups
                  permissions={permissions}
                  selectedIds={selectedPermissionIds}
                  expandedGroups={expandedPermissionGroups}
                  onToggleGroup={(group) =>
                    setExpandedPermissionGroups(
                      (current) =>
                        current.includes(group)
                          ? current.filter(
                              (item) => item !== group,
                            )
                          : [...current, group],
                    )
                  }
                  onTogglePermission={(permissionId) =>
                    setSelectedPermissionIds((current) =>
                      current.includes(permissionId)
                        ? current.filter(
                            (item) => item !== permissionId,
                          )
                        : [...current, permissionId],
                    )
                  }
                />
              </ScrollView>

              <Button
                label={
                  busy
                    ? t("organization.saving")
                    : editingRole
                      ? t("organization.saveRole")
                      : t("organization.createRole")
                }
                variant="primary"
                disabled={busy || !roleName.trim()}
                onPress={() => void saveRole()}
              />

              <Button
                label={t("organization.cancel")}
                variant="secondary"
                disabled={busy}
                onPress={() => setEditorMode(null)}
              />
            </View>
          ) : null}
        </ModalBackdrop>
      </Modal>
    </KeyboardAvoidingView>
  );
}

function Overview({
  organization,
  memberCount,
  roles,
  canManageMembers,
}: {
  organization: Organization | null;
  memberCount: number;
  roles: OrganizationRole[];
  canManageMembers: boolean;
}) {
  const { t } = useTranslation();

  if (!organization) {
    return (
      <EmptyState
        title={t("organization.organizationUnavailable")}
        description={t(
          "organization.organizationUnavailableHelp",
        )}
      />
    );
  }

  return (
    <>
      <View style={styles.organizationCard}>
        <View style={styles.organizationTop}>
          <View style={styles.organizationMark}>
            <Text style={styles.organizationMarkText}>
              {organization.name.trim().charAt(0).toUpperCase() ||
                "O"}
            </Text>
          </View>

          <StatusBadge
            label={
              organization.is_active
                ? t("organization.active")
                : t("organization.inactive")
            }
            active={organization.is_active}
            dark
          />
        </View>

        <Text style={styles.organizationName}>
          {organization.name}
        </Text>

        <Text style={styles.organizationSlug}>
          /{organization.slug}
        </Text>

        <View style={styles.organizationDetails}>
          <View style={styles.organizationDetail}>
            <Text style={styles.detailLabel}>
              {t("organization.currency")}
            </Text>
            <Text style={styles.detailValue}>
              {organization.currency}
            </Text>
          </View>

          <View style={styles.detailDivider} />

          <View style={styles.organizationDetail}>
            <Text style={styles.detailLabel}>
              {t("organization.aiFeaturesLabel")}
            </Text>
            <Text style={styles.detailValue}>
              {organization.ai_enabled
                ? t("organization.enabled")
                : t("organization.disabled")}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.metricsRow}>
        <MetricCard
          value={memberCount === 100 ? "100+" : String(memberCount)}
          label={t("organization.membersMetric")}
        />
        <MetricCard
          value={String(roles.length)}
          label={t("organization.rolesMetric")}
        />
      </View>

      <View style={styles.sectionHeaderStack}>
        <Text style={styles.sectionTitle}>
          {t("organization.workspaceManagement")}
        </Text>
        <Text style={styles.sectionHint}>
          {t("organization.workspaceManagementDescription")}
        </Text>
      </View>

      <View style={styles.linkList}>
        <OrganizationLink
          href="/organization/settings"
          index="01"
          title={t("organization.settingsCard")}
          description={t(
            "organization.settingsCardDescription",
          )}
        />

        <OrganizationLink
          href="/organization/members"
          index="02"
          title={t("organization.membersCard")}
          description={t(
            "organization.membersCardDescription",
          )}
        />

        <OrganizationLink
          href="/organization/roles"
          index="03"
          title={t("organization.rolesCard")}
          description={t(
            "organization.rolesCardDescription",
          )}
        />

        {canManageMembers ? (
          <OrganizationLink
            href="/organization/invitations"
            index="04"
            title={t("organization.invitationsCard")}
            description={t(
              "organization.invitationsCardDescription",
            )}
          />
        ) : null}

        <OrganizationLink
          href="/organization/subscription"
          index="05"
          title={t("organization.subscriptionCard")}
          description={t(
            "organization.subscriptionCardDescription",
          )}
        />
      </View>
    </>
  );
}

function Settings({
  organization,
  name,
  slug,
  currency,
  canManageOrganization,
  busy,
  onName,
  onSlug,
  onCurrency,
  onSave,
  onAIChange,
}: {
  organization: Organization | null;
  name: string;
  slug: string;
  currency: string;
  canManageOrganization: boolean;
  busy: boolean;
  onName: (value: string) => void;
  onSlug: (value: string) => void;
  onCurrency: (value: string) => void;
  onSave: () => void;
  onAIChange: (value: boolean) => void;
}) {
  const { t } = useTranslation();

  if (!organization) {
    return (
      <EmptyState
        title={t("organization.settingsUnavailable")}
        description={t(
          "organization.settingsUnavailableHelp",
        )}
      />
    );
  }

  return (
    <View style={styles.section}>
      <View style={styles.infoCard}>
        <Text style={styles.cardEyebrow}>
          {t("organization.profileEyebrow")}
        </Text>

        <Text style={styles.cardTitle}>
          {t("organization.workspaceDetails")}
        </Text>

        <Text style={styles.cardDescription}>
          {t("organization.workspaceDetailsDescription")}
        </Text>

        <Text style={styles.fieldLabel}>
          {t("organization.organizationName")}
        </Text>

        <TextInput
          style={[
            styles.input,
            !canManageOrganization &&
              styles.readOnlyInput,
          ]}
          value={name}
          onChangeText={onName}
          editable={canManageOrganization && !busy}
          placeholder={t("organization.organizationName")}
          placeholderTextColor={colors.muted}
        />

        <Text style={styles.fieldLabel}>
          {t("organization.organizationSlug")}
        </Text>

        <TextInput
          style={[
            styles.input,
            !canManageOrganization &&
              styles.readOnlyInput,
          ]}
          value={slug}
          onChangeText={onSlug}
          editable={canManageOrganization && !busy}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="organization-slug"
          placeholderTextColor={colors.muted}
        />

        <Text style={styles.fieldLabel}>
          {t("organization.currencyCode")}
        </Text>

        <TextInput
          style={[
            styles.input,
            !canManageOrganization &&
              styles.readOnlyInput,
          ]}
          value={currency}
          onChangeText={onCurrency}
          editable={canManageOrganization && !busy}
          autoCapitalize="characters"
          maxLength={3}
          placeholder="PKR"
          placeholderTextColor={colors.muted}
        />

        <View style={styles.readOnlyStatus}>
          <Text style={styles.detailLabel}>
            {t("organization.accountStatus")}
          </Text>

          <StatusBadge
            label={
              organization.is_active
                ? t("organization.active")
                : t("organization.inactive")
            }
            active={organization.is_active}
          />
        </View>

        {canManageOrganization ? (
          <Button
            label={
              busy
                ? t("organization.saving")
                : t("organization.saveDetails")
            }
            variant="primary"
            disabled={busy}
            onPress={onSave}
          />
        ) : (
          <Text style={styles.helperText}>
            {t("organization.readOnlySettingsHelp")}
          </Text>
        )}
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.cardEyebrow}>
          {t("organization.optionalFeature")}
        </Text>

        <Text style={styles.cardTitle}>
          {t("organization.aiFeatures")}
        </Text>

        <Text style={styles.cardDescription}>
          {t("organization.aiFeaturesDescription")}
        </Text>

        <View style={styles.settingRow}>
          <View style={styles.settingCopy}>
            <Text style={styles.settingTitle}>
              {organization.ai_enabled
                ? t("organization.enabled")
                : t("organization.disabled")}
            </Text>

            <Text style={styles.settingDescription}>
              {canManageOrganization
                ? t("organization.changeSettingHelp")
                : t("organization.managerSettingHelp")}
            </Text>
          </View>

          <Switch
            value={organization.ai_enabled}
            onValueChange={onAIChange}
            disabled={!canManageOrganization || busy}
            trackColor={{
              true: colors.navy,
              false: "#D8D0C3",
            }}
            accessibilityLabel={t(
              "organization.enableAiAccessibility",
            )}
          />
        </View>
      </View>
    </View>
  );
}

function RoleCard({
  role,
  canManage,
  busy,
  onEdit,
  onDelete,
}: {
  role: OrganizationRole;
  canManage: boolean;
  busy: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.roleCard}>
      <Pressable
        onPress={() => setExpanded((current) => !current)}
        style={styles.roleHeader}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
      >
        <View style={styles.roleCopy}>
          <View style={styles.roleTitleRow}>
            <Text style={styles.cardTitle}>{role.name}</Text>

            {role.is_system ? (
              <Text style={styles.systemBadge}>
                {t("organization.systemRole")}
              </Text>
            ) : null}
          </View>

          <Text style={styles.cardDescription}>
            {role.description ||
              t("organization.noDescription")}
          </Text>

          <Text style={styles.permissionCount}>
            {t("organization.permissionCount", {
              count: role.permissions.length,
            })}{" "}
            ·{" "}
            {expanded
              ? t("organization.hide")
              : t("organization.view")}
          </Text>
        </View>

        <Text style={styles.chevron}>
          {expanded ? "⌃" : "›"}
        </Text>
      </Pressable>

      {expanded ? (
        <View style={styles.permissionPreview}>
          {role.permissions.length ? (
            role.permissions.map((permission) => (
              <Text
                key={permission.id}
                style={styles.permissionLine}
              >
                • {permission.key}
              </Text>
            ))
          ) : (
            <Text style={styles.helperText}>
              {t("organization.noPermissionsAssigned")}
            </Text>
          )}
        </View>
      ) : null}

      {canManage ? (
        <View style={styles.actionRow}>
          <Button
            label={t("organization.editRoleAction")}
            variant="secondary"
            disabled={busy}
            onPress={onEdit}
          />

          {!role.is_system ? (
            <Button
              label={t("organization.delete")}
              variant="danger"
              disabled={busy}
              onPress={onDelete}
            />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function PermissionGroups({
  permissions,
  selectedIds,
  expandedGroups,
  onToggleGroup,
  onTogglePermission,
}: {
  permissions: AuthPermission[];
  selectedIds: string[];
  expandedGroups: string[];
  onToggleGroup: (group: string) => void;
  onTogglePermission: (permissionId: string) => void;
}) {
  const { t } = useTranslation();

  const groups = useMemo(() => {
    const grouped = new Map<string, AuthPermission[]>();

    for (const permission of permissions) {
      const group =
        permission.key.split(":")[0]?.split(".")[0] ||
        "other";

      grouped.set(group, [
        ...(grouped.get(group) ?? []),
        permission,
      ]);
    }

    return [...grouped.entries()].sort(([left], [right]) =>
      left.localeCompare(right),
    );
  }, [permissions]);

  if (permissions.length === 0) {
    return (
      <Text style={styles.helperText}>
        {t("organization.permissionsUnavailable")}
      </Text>
    );
  }

  return (
    <View style={styles.permissionGroups}>
      {groups.map(([group, groupPermissions]) => {
        const expanded = expandedGroups.includes(group);
        const selectedCount = groupPermissions.filter(
          (permission) => selectedIds.includes(permission.id),
        ).length;

        return (
          <View
            key={group}
            style={styles.permissionGroup}
          >
            <Pressable
              onPress={() => onToggleGroup(group)}
              style={styles.permissionGroupButton}
              accessibilityRole="button"
              accessibilityState={{ expanded }}
            >
              <View style={styles.permissionGroupCopy}>
                <Text style={styles.permissionGroupTitle}>
                  {capitalize(group.replaceAll("_", " "))}
                </Text>

                <Text style={styles.permissionGroupHint}>
                  {t("organization.permissionsSelected", {
                    selected: selectedCount,
                    total: groupPermissions.length,
                  })}
                </Text>
              </View>

              <Text style={styles.chevron}>
                {expanded ? "⌃" : "›"}
              </Text>
            </Pressable>

            {expanded ? (
              <View style={styles.permissionOptions}>
                {groupPermissions.map((permission) => {
                  const selected = selectedIds.includes(
                    permission.id,
                  );

                  return (
                    <Pressable
                      key={permission.id}
                      onPress={() =>
                        onTogglePermission(permission.id)
                      }
                      style={styles.permissionOption}
                      accessibilityRole="checkbox"
                      accessibilityState={{ checked: selected }}
                    >
                      <View
                        style={[
                          styles.checkbox,
                          selected &&
                            styles.checkboxSelected,
                        ]}
                      >
                        <Text style={styles.checkboxMark}>
                          {selected ? "✓" : ""}
                        </Text>
                      </View>

                      <View
                        style={styles.permissionOptionCopy}
                      >
                        <Text style={styles.permissionKey}>
                          {permission.key}
                        </Text>

                        {permission.description ? (
                          <Text
                            style={
                              styles.permissionDescription
                            }
                          >
                            {permission.description}
                          </Text>
                        ) : null}
                      </View>
                    </Pressable>
                  );
                })}
              </View>
            ) : null}
          </View>
        );
      })}
    </View>
  );
}

function OrganizationLink({
  href,
  index,
  title,
  description,
}: {
  href:
    | "/organization/settings"
    | "/organization/members"
    | "/organization/roles"
    | "/organization/invitations"
    | "/organization/subscription";
  index: string;
  title: string;
  description: string;
}) {
  return (
    <Link href={href} asChild>
      <Pressable
        style={({ pressed }) => [
          styles.linkCard,
          pressed && styles.linkCardPressed,
        ]}
        accessibilityRole="button"
      >
        <View style={styles.linkIndex}>
          <Text style={styles.linkIndexText}>{index}</Text>
        </View>

        <View style={styles.linkCopy}>
          <Text style={styles.linkTitle}>{title}</Text>
          <Text style={styles.linkDescription}>
            {description}
          </Text>
        </View>

        <Text style={styles.chevron}>›</Text>
      </Pressable>
    </Link>
  );
}

function MetricCard({
  value,
  label,
}: {
  value: string;
  label: string;
}) {
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function StatusBadge({
  label,
  active,
  dark = false,
}: {
  label: string;
  active: boolean;
  dark?: boolean;
}) {
  return (
    <View
      style={[
        styles.statusBadge,
        dark && styles.statusBadgeDark,
        active
          ? styles.statusActive
          : styles.statusInactive,
      ]}
    >
      <View
        style={[
          styles.statusDot,
          active
            ? styles.statusDotActive
            : styles.statusDotInactive,
        ]}
      />

      <Text
        style={[
          styles.statusText,
          dark && styles.statusTextDark,
          active
            ? styles.statusTextActive
            : styles.statusTextInactive,
        ]}
      >
        {label}
      </Text>
    </View>
  );
}

function FilterChip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.filterChip,
        selected && styles.filterChipSelected,
      ]}
      accessibilityRole="button"
      accessibilityState={{ selected }}
    >
      <Text
        style={[
          styles.filterChipText,
          selected && styles.filterChipTextSelected,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

function Button({
  label,
  variant,
  disabled = false,
  onPress,
}: {
  label: string;
  variant: "primary" | "secondary" | "danger";
  disabled?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        variant === "primary" && styles.buttonPrimary,
        variant === "secondary" &&
          styles.buttonSecondary,
        variant === "danger" && styles.buttonDanger,
        disabled && styles.buttonDisabled,
        pressed && !disabled && styles.buttonPressed,
      ]}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.buttonText,
          variant !== "primary" &&
            styles.buttonTextDark,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyDescription}>
        {description}
      </Text>
    </View>
  );
}

function ModalBackdrop({
  children,
  onClose,
}: {
  children: React.ReactNode;
  onClose: () => void;
}) {
  const { t, i18n: activeI18n } = useTranslation();
  const isUrdu = activeI18n.resolvedLanguage === "ur";

  return (
    <View style={[styles.modalRoot, isUrdu && { direction: "rtl" }]}>
      <Pressable
        style={styles.modalScrim}
        onPress={onClose}
        accessibilityRole="button"
        accessibilityLabel={t(
          "organization.closeDialogAccessibility",
        )}
      />
      {children}
    </View>
  );
}

function invitationState(
  invitation: OrganizationInvitation,
): InvitationState {
  if (invitation.accepted_at) {
    return "accepted";
  }

  if (invitation.revoked_at) {
    return "revoked";
  }

  if (
    new Date(invitation.expires_at).getTime() <
    Date.now()
  ) {
    return "expired";
  }

  return "pending";
}

function formatDate(value: string) {
  const date = new Date(value);
    return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleDateString(
        i18n.resolvedLanguage === "ur" ? "ur-PK" : "en-PK",
        { year: "numeric", month: "short", day: "numeric" },
      );
}

function initials(firstName: string, lastName: string) {
  const first = firstName.trim().charAt(0);
  const last = lastName.trim().charAt(0);

  return `${first}${last}`.toUpperCase() || "M";
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

const colors = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  navy: "#080D18",
  navySoft: "#18283B",
  gold: "#D9A441",
  text: "#191410",
  secondary: "#5C5347",
  muted: "#8C806E",
  border: "#E4D9C4",
  green: "#24744A",
  greenBackground: "#EAF4EC",
  red: "#A33C32",
  redBackground: "#FBECE9",
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 18, paddingTop: 22, paddingBottom: 38 },
  loadingScreen: { flex: 1, backgroundColor: colors.background, alignItems: "center", justifyContent: "center", gap: 10 },
  headingRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 20 },
  headingCopy: { flex: 1 },
  eyebrow: { color: colors.muted, fontSize: 10, fontWeight: "800", letterSpacing: 1.5 },
  pageTitle: { color: colors.text, fontSize: 27, fontWeight: "800", marginTop: 5 },
  pageSubtitle: { color: colors.secondary, fontSize: 13, lineHeight: 19, marginTop: 5 },
  refreshButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 11, borderRadius: 10, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  refreshText: { color: colors.navy, fontSize: 12, fontWeight: "700" },
  organizationCard: { backgroundColor: colors.navy, borderRadius: 18, padding: 19 },
  organizationTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  organizationMark: { width: 42, height: 42, borderRadius: 13, alignItems: "center", justifyContent: "center", backgroundColor: colors.navySoft, borderWidth: 1, borderColor: "#344356" },
  organizationMarkText: { color: "#FFFFFF", fontSize: 19, fontWeight: "800" },
  organizationName: { color: "#FFFFFF", fontSize: 22, fontWeight: "800", marginTop: 17 },
  organizationSlug: { color: "#B7C1CE", fontSize: 13, marginTop: 4 },
  organizationDetails: { flexDirection: "row", alignItems: "center", borderTopWidth: 1, borderTopColor: "#2B394B", marginTop: 17, paddingTop: 14 },
  organizationDetail: { flex: 1 },
  detailLabel: { color: "#9BA8B7", fontSize: 9, letterSpacing: 1, fontWeight: "800" },
  detailValue: { color: "#F6F0E6", fontSize: 14, fontWeight: "700", marginTop: 5 },
  detailDivider: { width: 1, height: 31, backgroundColor: "#2B394B", marginHorizontal: 14 },
  statusBadge: { alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6, borderRadius: 99, paddingHorizontal: 9, paddingVertical: 6, backgroundColor: colors.greenBackground },
  statusBadgeDark: { backgroundColor: "#23374A" },
  statusActive: { backgroundColor: colors.greenBackground },
  statusInactive: { backgroundColor: colors.redBackground },
  statusDot: { width: 7, height: 7, borderRadius: 4 },
  statusDotActive: { backgroundColor: "#2F9259" },
  statusDotInactive: { backgroundColor: "#B74A3D" },
  statusText: { fontSize: 11, fontWeight: "700" },
  statusTextDark: { color: "#F6F0E6" },
  statusTextActive: { color: colors.green },
  statusTextInactive: { color: colors.red },
  metricsRow: { flexDirection: "row", gap: 10, marginTop: 11 },
  metricCard: { flex: 1, backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 14, padding: 15 },
  metricValue: { color: colors.navy, fontSize: 22, fontWeight: "800" },
  metricLabel: { color: colors.secondary, fontSize: 12, marginTop: 3 },
  section: { marginTop: 4 },
  sectionHeaderStack: { marginTop: 25, marginBottom: 11 },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10, marginTop: 5, marginBottom: 12 },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: "800" },
  sectionHint: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 4 },
  linkList: { gap: 9 },
  linkCard: { minHeight: 72, flexDirection: "row", alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 14, paddingHorizontal: 13, paddingVertical: 11 },
  linkCardPressed: { opacity: 0.75 },
  linkIndex: { width: 33, height: 33, borderRadius: 10, backgroundColor: "#F4EEE3", alignItems: "center", justifyContent: "center", marginRight: 11 },
  linkIndexText: { color: colors.muted, fontSize: 10, fontWeight: "800" },
  linkCopy: { flex: 1 },
  linkTitle: { color: colors.text, fontSize: 14, fontWeight: "700" },
  linkDescription: { color: colors.secondary, fontSize: 11, lineHeight: 16, marginTop: 3 },
  chevron: { color: colors.muted, fontSize: 23, marginLeft: 9 },
  infoCard: { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 16, padding: 16, marginBottom: 12 },
  cardEyebrow: { color: colors.muted, fontSize: 9, fontWeight: "800", letterSpacing: 1.2 },
  cardTitle: { color: colors.text, fontSize: 15, fontWeight: "800" },
  cardDescription: { color: colors.secondary, fontSize: 12, lineHeight: 18, marginTop: 4 },
  fieldLabel: { color: colors.secondary, fontSize: 12, fontWeight: "700", marginTop: 14, marginBottom: 6 },
  input: { minHeight: 48, backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 11, color: colors.text, fontSize: 14, paddingHorizontal: 13, paddingVertical: 11 },
  readOnlyInput: { backgroundColor: "#F7F4EE", color: colors.secondary },
  multilineInput: { minHeight: 78, textAlignVertical: "top" },
  readOnlyStatus: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 17 },
  settingRow: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: "#F8F5EF", borderRadius: 12, padding: 13, marginTop: 14 },
  settingCopy: { flex: 1 },
  settingTitle: { color: colors.text, fontSize: 14, fontWeight: "700" },
  settingDescription: { color: colors.secondary, fontSize: 11, lineHeight: 16, marginTop: 3 },
  personCard: { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 14, padding: 14, marginTop: 10 },
  personTop: { flexDirection: "row", alignItems: "center", gap: 10 },
  avatar: { width: 39, height: 39, borderRadius: 13, alignItems: "center", justifyContent: "center", backgroundColor: "#F1E7D4" },
  avatarText: { color: colors.navy, fontSize: 12, fontWeight: "800" },
  personCopy: { flex: 1 },
  personMeta: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8, marginTop: 12 },
  metaPill: { color: colors.navy, backgroundColor: "#F1E7D4", overflow: "hidden", borderRadius: 99, paddingHorizontal: 9, paddingVertical: 5, fontSize: 11, fontWeight: "700" },
  metaText: { color: colors.muted, fontSize: 11 },
  actionRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  filterRow: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginTop: 10 },
  filterChip: { borderWidth: 1, borderColor: colors.border, borderRadius: 99, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: colors.surface },
  filterChipSelected: { backgroundColor: colors.navy, borderColor: colors.navy },
  filterChipText: { color: colors.secondary, fontSize: 12, fontWeight: "700" },
  filterChipTextSelected: { color: "#FFFFFF" },
  invitationCard: { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 14, padding: 14, marginTop: 10, gap: 10 },
  invitationTop: { flexDirection: "row", alignItems: "center", gap: 10 },
  roleCard: { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 14, padding: 14, marginTop: 10 },
  roleHeader: { flexDirection: "row", alignItems: "center", gap: 10 },
  roleCopy: { flex: 1 },
  roleTitleRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 7 },
  systemBadge: { overflow: "hidden", color: colors.muted, backgroundColor: "#F2EEE7", borderRadius: 99, paddingHorizontal: 7, paddingVertical: 3, fontSize: 9, fontWeight: "800" },
  permissionCount: { color: colors.navy, fontSize: 11, fontWeight: "700", marginTop: 8 },
  permissionPreview: { borderTopWidth: 1, borderTopColor: colors.border, marginTop: 12, paddingTop: 10, gap: 6 },
  permissionLine: { color: colors.secondary, fontSize: 11, lineHeight: 16 },
  permissionGroups: { gap: 8, marginTop: 8, marginBottom: 14 },
  permissionGroup: { borderWidth: 1, borderColor: colors.border, borderRadius: 11, overflow: "hidden" },
  permissionGroupButton: { flexDirection: "row", alignItems: "center", paddingHorizontal: 12, paddingVertical: 11, backgroundColor: "#F8F5EF" },
  permissionGroupCopy: { flex: 1 },
  permissionGroupTitle: { color: colors.text, fontSize: 12, fontWeight: "800" },
  permissionGroupHint: { color: colors.muted, fontSize: 10, marginTop: 3 },
  permissionOptions: { borderTopWidth: 1, borderTopColor: colors.border, paddingHorizontal: 10 },
  permissionOption: { flexDirection: "row", alignItems: "flex-start", gap: 9, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#F1ECE3" },
  checkbox: { width: 19, height: 19, borderWidth: 1, borderColor: "#BDB2A2", borderRadius: 5, alignItems: "center", justifyContent: "center" },
  checkboxSelected: { backgroundColor: colors.navy, borderColor: colors.navy },
  checkboxMark: { color: "#FFFFFF", fontSize: 12, fontWeight: "800" },
  permissionOptionCopy: { flex: 1 },
  permissionKey: { color: colors.text, fontSize: 11, fontWeight: "700" },
  permissionDescription: { color: colors.muted, fontSize: 10, lineHeight: 15, marginTop: 2 },
  button: { minHeight: 40, alignItems: "center", justifyContent: "center", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9 },
  buttonPrimary: { backgroundColor: colors.navy },
  buttonSecondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  buttonDanger: { backgroundColor: colors.redBackground, borderWidth: 1, borderColor: "#EAC6C0" },
  buttonDisabled: { opacity: 0.5 },
  buttonPressed: { opacity: 0.72 },
  buttonText: { color: "#FFFFFF", fontSize: 12, fontWeight: "800" },
  buttonTextDark: { color: colors.navy },
  emptyState: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 14, padding: 18, marginTop: 12 },
  emptyTitle: { color: colors.text, fontSize: 14, fontWeight: "800" },
  emptyDescription: { color: colors.secondary, fontSize: 12, lineHeight: 18, marginTop: 5 },
  errorBox: { backgroundColor: colors.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 12, padding: 12, marginBottom: 12 },
  errorTitle: { color: colors.red, fontSize: 13, fontWeight: "800" },
  errorText: { color: colors.secondary, fontSize: 12, lineHeight: 18, marginTop: 4 },
  noticeBox: { backgroundColor: colors.greenBackground, borderColor: "#C5E2CE", borderWidth: 1, borderRadius: 12, padding: 11, marginBottom: 12 },
  noticeText: { color: colors.green, fontSize: 12, fontWeight: "700" },
  busyRow: { flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 8, padding: 14 },
  helperText: { color: colors.muted, fontSize: 12, lineHeight: 18 },
  modalRoot: { flex: 1, justifyContent: "flex-end" },
  modalScrim: { ...StyleSheet.absoluteFill, backgroundColor: "rgba(8, 13, 24, 0.48)" },
  sheet: { maxHeight: "91%", backgroundColor: colors.background, borderTopLeftRadius: 22, borderTopRightRadius: 22, paddingHorizontal: 18, paddingTop: 10, paddingBottom: Platform.OS === "ios" ? 30 : 18 },
  sheetHandle: { alignSelf: "center", width: 38, height: 4, borderRadius: 3, backgroundColor: "#C5BBAE", marginBottom: 16 },
  sheetTitle: { color: colors.text, fontSize: 20, fontWeight: "800" },
  sheetSubtitle: { color: colors.secondary, fontSize: 12, lineHeight: 18, marginTop: 4, marginBottom: 10 },
  sheetList: { flexGrow: 0, maxHeight: 330, marginVertical: 8 },
  roleEditorScroll: { flexGrow: 0, maxHeight: 470, marginVertical: 8 },
  choiceRow: { flexDirection: "row", alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 11, padding: 12, marginBottom: 8 },
  choiceRowSelected: { borderColor: colors.navy, backgroundColor: "#F1E7D4" },
  choiceCopy: { flex: 1 },
  choiceTitle: { color: colors.text, fontSize: 13, fontWeight: "800" },
  choiceDescription: { color: colors.secondary, fontSize: 11, lineHeight: 16, marginTop: 3 },
  choiceMark: { color: colors.navy, fontSize: 12, fontWeight: "800" },
});