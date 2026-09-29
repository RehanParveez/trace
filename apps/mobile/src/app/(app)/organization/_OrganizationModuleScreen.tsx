import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from "react-native";
import { Link, router } from "expo-router";
import { restoreSession } from "../../../api/client";
import {acceptInvitation, createInvitation, createRole, deleteRole, getAISettings, getOrganization, listInvitations, listMembers, listPermissions, listRoles, revokeInvitation,
  updateAISettings, updateMemberRole, updateMemberStatus, updateOrganization, updateRole,
} from "../../../api/organizations";
import type { AuthPermission, Organization, OrganizationInvitation, OrganizationMember, OrganizationRole,
} from "../../../api/types";

const ORG_MANAGE = "organization.manage";
const MEMBER_MANAGE = "organization.members.manage";

type OrganizationSection =
  | "overview"
  | "settings"
  | "members"
  | "roles"
  | "invitations";

export function OrganizationModuleScreen({
  section,
}: {
  section: OrganizationSection;
}) {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [roles, setRoles] = useState<OrganizationRole[]>([]);
  const [permissions, setPermissions] = useState<AuthPermission[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [canManageOrganization, setCanManageOrganization] = useState(false);
  const [canManageMembers, setCanManageMembers] = useState(false);

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [currency, setCurrency] = useState("");

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRoleId, setInviteRoleId] = useState("");

  const [roleId, setRoleId] = useState("");
  const [roleName, setRoleName] = useState("");
  const [roleDescription, setRoleDescription] = useState("");
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<string[]>(
    [],
  );

  const [invitationToken, setInvitationToken] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const user = await restoreSession();

      if (!user) {
        router.replace("/");
        return;
      }

      const permissionKeys = user.role.permissions.map(
        (permission) => permission.key,
      );

      setCanManageOrganization(permissionKeys.includes(ORG_MANAGE));
      setCanManageMembers(permissionKeys.includes(MEMBER_MANAGE));

      if (!permissionKeys.includes("organization.read")) {
        setError(
          "Your organization role does not allow viewing organization details.",
        );
        return;
      }

      const results = await Promise.allSettled([
        getOrganization(),
        getAISettings(),
        listMembers(),
        listRoles(),
        listInvitations(),
        listPermissions(),
      ]);

      const [
        orgResult,
        aiResult,
        memberResult,
        roleResult,
        inviteResult,
        permissionResult,
      ] = results;

      if (orgResult.status !== "fulfilled") {
        throw orgResult.reason;
      }

      const loadedOrganization = orgResult.value;

      if (aiResult.status === "fulfilled") {
        loadedOrganization.ai_enabled = aiResult.value.ai_enabled;
      }

      setOrganization(loadedOrganization);
      setName(loadedOrganization.name);
      setSlug(loadedOrganization.slug);
      setCurrency(loadedOrganization.currency);

      if (memberResult.status === "fulfilled") {
        setMembers(memberResult.value);
      }

      if (roleResult.status === "fulfilled") {
        setRoles(roleResult.value);
      }

      if (inviteResult.status === "fulfilled") {
        setInvitations(inviteResult.value);
      }

      if (permissionResult.status === "fulfilled") {
        setPermissions(permissionResult.value);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load organization.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function perform(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setNotice("");

    try {
      await action();
      setNotice("Changes saved.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveOrganization() {
    if (!name.trim() || !slug.trim()) {
      setError("Organization name and slug are required.");
      return;
    }

    await perform(() =>
      updateOrganization({
        name: name.trim(),
        slug: slug.trim().toLowerCase(),
        currency: currency.trim().toUpperCase(),
      }),
    );
  }

  async function toggleAI(enabled: boolean) {
    await perform(() => updateAISettings(enabled));
  }

  async function inviteMember() {
    if (!inviteEmail.trim() || !inviteRoleId) {
      setError("Enter an email and select a role.");
      return;
    }

    await perform(async () => {
      await createInvitation(inviteEmail, inviteRoleId);
      setInviteEmail("");
    });
  }

  async function changeMemberRole(memberId: string, nextRoleId: string) {
    await perform(() => updateMemberRole(memberId, nextRoleId));
  }

  async function toggleMember(member: OrganizationMember) {
    const next = !member.is_active;

    Alert.alert(
      next ? "Activate member?" : "Deactivate member?",
      `${member.first_name} ${member.last_name}`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: next ? "Activate" : "Deactivate",
          style: next ? "default" : "destructive",
          onPress: () =>
            void perform(() => updateMemberStatus(member.id, next)),
        },
      ],
    );
  }

  function startRoleEdit(role?: OrganizationRole) {
    setRoleId(role?.id ?? "");
    setRoleName(role?.name ?? "");
    setRoleDescription(role?.description ?? "");
    setSelectedPermissionIds(
      role?.permissions.map((permission) => permission.id) ?? [],
    );
  }

  function togglePermission(id: string) {
    setSelectedPermissionIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  }

  async function saveRole() {
    if (!roleName.trim()) {
      setError("Enter a role name.");
      return;
    }

    const payload = {
      name: roleName.trim(),
      description: roleDescription.trim() || null,
      permission_ids: selectedPermissionIds,
    };

    await perform(async () => {
      if (roleId) {
        await updateRole(roleId, payload);
      } else {
        await createRole(payload);
      }

      startRoleEdit();
    });
  }

  function confirmDeleteRole(role: OrganizationRole) {
    Alert.alert("Delete role?", `Delete “${role.name}”?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: () => void perform(() => deleteRole(role.id)),
      },
    ]);
  }

  function confirmRevoke(invitation: OrganizationInvitation) {
    Alert.alert("Revoke invitation?", invitation.email, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Revoke",
        style: "destructive",
        onPress: () => void perform(() => revokeInvitation(invitation.id)),
      },
    ]);
  }

  async function handleAcceptInvitation() {
    if (!invitationToken.trim()) {
      setError("Enter the invitation token.");
      return;
    }

    await perform(async () => {
      await acceptInvitation(invitationToken);
      setInvitationToken("");
    });
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading organization…</Text>
      </View>
    );
  }

  const pageTitles: Record<OrganizationSection, string> = {
    overview: "Organization",
    settings: "Organization settings",
    members: "Members",
    roles: "Roles and access",
    invitations: "Invitations",
  };

  const pageSubtitles: Record<OrganizationSection, string> = {
    overview: "Organization workspace and administration.",
    settings: "Manage organization details and AI access.",
    members: "Manage organization members and their access.",
    roles: "Configure roles and permissions.",
    invitations: "Send invitations and manage existing invitations.",
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.topBar}>
          <Link href="/projects" asChild>
            <Pressable accessibilityRole="button">
              <Text style={styles.link}>‹ Projects</Text>
            </Pressable>
          </Link>

          <Text style={styles.brand}>TRACE</Text>

          <Pressable
            onPress={() => void load()}
            accessibilityRole="button"
            disabled={busy}
          >
            <Text style={styles.link}>Refresh</Text>
          </Pressable>
        </View>

        <Text style={styles.title}>{pageTitles[section]}</Text>
        <Text style={styles.subtitle}>{pageSubtitles[section]}</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}
        {notice ? <Text style={styles.success}>{notice}</Text> : null}

        {section === "overview" ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              {organization?.name ?? "Your organization"}
            </Text>

            <Text style={styles.muted}>
              {organization?.is_active ? "Active" : "Inactive"}
              {" · "}
              {members.length} members
              {" · "}
              {roles.length} roles
            </Text>

            <Link href="/organization/settings" asChild>
              <Pressable style={styles.card} accessibilityRole="button">
                <Text style={styles.itemTitle}>Organization settings</Text>
                <Text style={styles.muted}>
                  Organization details and AI settings ›
                </Text>
              </Pressable>
            </Link>

            <Link href="/organization/members" asChild>
              <Pressable style={styles.card} accessibilityRole="button">
                <Text style={styles.itemTitle}>Members</Text>
                <Text style={styles.muted}>View and manage members ›</Text>
              </Pressable>
            </Link>

            <Link href="/organization/roles" asChild>
              <Pressable style={styles.card} accessibilityRole="button">
                <Text style={styles.itemTitle}>Roles and access</Text>
                <Text style={styles.muted}>
                  Manage roles and permissions ›
                </Text>
              </Pressable>
            </Link>

            <Link href="/organization/invitations" asChild>
              <Pressable style={styles.card} accessibilityRole="button">
                <Text style={styles.itemTitle}>Invitations</Text>
                <Text style={styles.muted}>
                  Send or revoke invitations ›
                </Text>
              </Pressable>
            </Link>
          </View>
        ) : null}

        {section === "settings" && organization ? (
          <>
            <Section title="Organization details">
              <Field label="Name" value={name} onChangeText={setName} />
              <Field
                label="Slug"
                value={slug}
                onChangeText={setSlug}
                autoCapitalize="none"
              />
              <Field
                label="Currency"
                value={currency}
                onChangeText={setCurrency}
                autoCapitalize="characters"
              />

              <Text style={styles.muted}>
                Status: {organization.is_active ? "Active" : "Inactive"}
              </Text>

              {canManageOrganization ? (
                <Action
                  title="Save organization"
                  onPress={() => void saveOrganization()}
                  disabled={busy}
                />
              ) : null}
            </Section>

            <Section title="AI settings">
              <View style={styles.switchRow}>
                <View style={styles.flexText}>
                  <Text style={styles.itemTitle}>AI features</Text>
                  <Text style={styles.muted}>
                    {organization.ai_enabled ? "Enabled" : "Disabled"} for this
                    organization
                  </Text>
                </View>

                <Switch
                  value={organization.ai_enabled}
                  onValueChange={(value) => void toggleAI(value)}
                  disabled={!canManageOrganization || busy}
                  trackColor={{ true: "#183153" }}
                />
              </View>
            </Section>
          </>
        ) : null}

        {section === "members" ? (
          <Section title={`Members (${members.length})`}>
            {members.map((member) => (
              <View key={member.id} style={styles.card}>
                <Text style={styles.itemTitle}>
                  {member.first_name} {member.last_name}
                </Text>

                <Text style={styles.muted}>{member.email}</Text>

                <Text style={styles.muted}>
                  {member.role.name} · {member.is_active ? "Active" : "Inactive"}
                  {member.is_verified ? " · Verified" : ""}
                </Text>

                {canManageMembers ? (
                  <>
                    <Text style={styles.label}>Change role</Text>

                    <View style={styles.chips}>
                      {roles.map((role) => (
                        <Chip
                          key={role.id}
                          label={role.name}
                          selected={member.role.id === role.id}
                          onPress={() =>
                            void changeMemberRole(member.id, role.id)
                          }
                        />
                      ))}
                    </View>

                    <Action
                      title={
                        member.is_active
                          ? "Deactivate member"
                          : "Activate member"
                      }
                      secondary={!member.is_active}
                      danger={member.is_active}
                      onPress={() => toggleMember(member)}
                      disabled={busy}
                    />
                  </>
                ) : null}
              </View>
            ))}

            {members.length === 0 ? (
              <Text style={styles.muted}>No members found.</Text>
            ) : null}
          </Section>
        ) : null}

        {section === "invitations" ? (
          <>
            <Section title="Invitations">
              {canManageMembers ? (
                <>
                  <Field
                    label="Invite by email"
                    value={inviteEmail}
                    onChangeText={setInviteEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />

                  <Text style={styles.label}>Assign role</Text>

                  <View style={styles.chips}>
                    {roles.map((role) => (
                      <Chip
                        key={role.id}
                        label={role.name}
                        selected={inviteRoleId === role.id}
                        onPress={() => setInviteRoleId(role.id)}
                      />
                    ))}
                  </View>

                  <Action
                    title="Send invitation"
                    onPress={() => void inviteMember()}
                    disabled={busy}
                  />
                </>
              ) : null}

              {invitations.map((invitation) => {
                const state = invitation.accepted_at
                  ? "Accepted"
                  : invitation.revoked_at
                    ? "Revoked"
                    : new Date(invitation.expires_at) < new Date()
                      ? "Expired"
                      : "Pending";

                return (
                  <View key={invitation.id} style={styles.card}>
                    <Text style={styles.itemTitle}>{invitation.email}</Text>

                    <Text style={styles.muted}>
                      {state} · expires{" "}
                      {new Date(invitation.expires_at).toLocaleDateString()}
                    </Text>

                    {canManageMembers && state === "Pending" ? (
                      <Action
                        title="Revoke invitation"
                        danger
                        onPress={() => confirmRevoke(invitation)}
                        disabled={busy}
                      />
                    ) : null}
                  </View>
                );
              })}

              {invitations.length === 0 ? (
                <Text style={styles.muted}>No invitations found.</Text>
              ) : null}
            </Section>

            <Section title="Accept an invitation">
              <Text style={styles.muted}>
                Use this when signed in with the email address the invitation
                was sent to.
              </Text>

              <Field
                label="Invitation token"
                value={invitationToken}
                onChangeText={setInvitationToken}
                autoCapitalize="none"
              />

              <Action
                title="Accept invitation"
                onPress={() => void handleAcceptInvitation()}
                disabled={busy}
              />
            </Section>
          </>
        ) : null}

        {section === "roles" ? (
          <Section title="Roles and permissions">
            {canManageOrganization ? (
              <RoleEditor
                roles={roles}
                permissions={permissions}
                roleId={roleId}
                roleName={roleName}
                roleDescription={roleDescription}
                selectedPermissionIds={selectedPermissionIds}
                onStartEdit={startRoleEdit}
                onName={setRoleName}
                onDescription={setRoleDescription}
                onTogglePermission={togglePermission}
                onSave={() => void saveRole()}
                onDelete={confirmDeleteRole}
                busy={busy}
              />
            ) : (
              roles.map((role) => (
                <View key={role.id} style={styles.card}>
                  <Text style={styles.itemTitle}>{role.name}</Text>
                  <Text style={styles.muted}>
                    {role.description ||
                      `${role.permissions.length} permissions`}
                    {role.is_system ? " · System role" : ""}
                  </Text>
                </View>
              ))
            )}
          </Section>
        ) : null}

        {busy ? (
          <ActivityIndicator color="#183153" style={styles.spinner} />
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

export default function OrganizationModuleScreenRoute() {
  return <OrganizationModuleScreen section="overview" />;
}

function RoleEditor({
  roles,
  permissions,
  roleId,
  roleName,
  roleDescription,
  selectedPermissionIds,
  onStartEdit,
  onName,
  onDescription,
  onTogglePermission,
  onSave,
  onDelete,
  busy,
}: {
  roles: OrganizationRole[];
  permissions: AuthPermission[];
  roleId: string;
  roleName: string;
  roleDescription: string;
  selectedPermissionIds: string[];
  onStartEdit: (role?: OrganizationRole) => void;
  onName: (value: string) => void;
  onDescription: (value: string) => void;
  onTogglePermission: (id: string) => void;
  onSave: () => void;
  onDelete: (role: OrganizationRole) => void;
  busy: boolean;
}) {
  return (
    <>
      <Action
        title="Create role"
        onPress={() => onStartEdit()}
        disabled={busy}
      />

      {roles.map((role) => (
        <View key={role.id} style={styles.card}>
          <Text style={styles.itemTitle}>{role.name}</Text>

          <Text style={styles.muted}>
            {role.description || `${role.permissions.length} permissions`}
            {role.is_system ? " · System role" : ""}
          </Text>

          <View style={styles.row}>
            <Action
              title="Edit"
              secondary
              onPress={() => onStartEdit(role)}
              disabled={busy}
            />

            {!role.is_system ? (
              <Action
                title="Delete"
                danger
                onPress={() => onDelete(role)}
                disabled={busy}
              />
            ) : null}
          </View>
        </View>
      ))}

      {roleName || roleId ? (
        <View style={styles.card}>
          <Text style={styles.itemTitle}>
            {roleId ? "Edit role" : "New role"}
          </Text>

          <Field label="Role name" value={roleName} onChangeText={onName} />
          <Field
            label="Description"
            value={roleDescription}
            onChangeText={onDescription}
          />

          <Text style={styles.label}>Permissions</Text>

          <View style={styles.chips}>
            {permissions.map((permission) => (
              <Chip
                key={permission.id}
                label={permission.key}
                selected={selectedPermissionIds.includes(permission.id)}
                onPress={() => onTogglePermission(permission.id)}
              />
            ))}
          </View>

          <Action title="Save role" onPress={onSave} disabled={busy} />
          <Action
            title="Cancel"
            secondary
            onPress={() => onStartEdit()}
            disabled={busy}
          />
        </View>
      ) : null}
    </>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Field({
  label,
  value,
  onChangeText,
  keyboardType = "default",
  autoCapitalize = "sentences",
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "email-address";
  autoCapitalize?: "none" | "sentences" | "characters";
}) {
  return (
    <>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
      />
    </>
  );
}

function Chip({
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
      style={[styles.chip, selected && styles.chipSelected]}
      accessibilityRole="button"
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
        {label}
      </Text>
    </Pressable>
  );
}

function Action({
  title,
  onPress,
  secondary = false,
  danger = false,
  disabled = false,
}: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.action,
        secondary && styles.actionSecondary,
        danger && styles.actionDanger,
        disabled && styles.actionDisabled,
      ]}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          secondary && styles.actionSecondaryText,
        ]}
      >
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#F4F6F8" },
  page: {
    flexGrow: 1,
    padding: 22,
    paddingTop: 48,
    paddingBottom: 48,
    backgroundColor: "#F4F6F8",
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  brand: { color: "#183153", fontWeight: "800", letterSpacing: 1.2 },
  title: {
    color: "#17212F",
    fontSize: 30,
    fontWeight: "700",
    marginTop: 22,
  },
  subtitle: {
    color: "#667085",
    marginTop: 6,
    marginBottom: 14,
    lineHeight: 21,
  },
  section: { marginTop: 22 },
  sectionTitle: {
    color: "#17212F",
    fontSize: 19,
    fontWeight: "700",
    marginBottom: 10,
  },
  card: {
    backgroundColor: "white",
    borderColor: "#E4E7EC",
    borderWidth: 1,
    borderRadius: 13,
    padding: 15,
    marginTop: 10,
  },
  itemTitle: { color: "#17212F", fontSize: 15, fontWeight: "700" },
  label: {
    color: "#344054",
    fontSize: 13,
    fontWeight: "600",
    marginTop: 12,
    marginBottom: 6,
  },
  input: {
    backgroundColor: "white",
    borderColor: "#D0D5DD",
    borderWidth: 1,
    borderRadius: 10,
    padding: 13,
    fontSize: 15,
    color: "#17212F",
  },
  muted: { color: "#667085", marginTop: 5, lineHeight: 19 },
  error: {
    color: "#B42318",
    backgroundColor: "#FEF3F2",
    padding: 11,
    borderRadius: 9,
    marginTop: 14,
  },
  success: {
    color: "#067647",
    backgroundColor: "#ECFDF3",
    padding: 11,
    borderRadius: 9,
    marginTop: 14,
  },
  link: { color: "#183153", fontWeight: "700" },
  switchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 12,
    padding: 15,
  },
  flexText: { flex: 1 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginTop: 4 },
  chip: {
    borderWidth: 1,
    borderColor: "#D0D5DD",
    borderRadius: 20,
    paddingHorizontal: 11,
    paddingVertical: 8,
    marginTop: 5,
    backgroundColor: "white",
  },
  chipSelected: { borderColor: "#183153", backgroundColor: "#E8EEF5" },
  chipText: { color: "#344054", fontSize: 12, fontWeight: "600" },
  chipTextSelected: { color: "#183153" },
  action: {
    backgroundColor: "#183153",
    padding: 13,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 11,
  },
  actionSecondary: {
    backgroundColor: "white",
    borderWidth: 1,
    borderColor: "#D0D5DD",
  },
  actionDanger: { backgroundColor: "#B42318" },
  actionDisabled: { opacity: 0.55 },
  actionText: { color: "white", fontWeight: "700" },
  actionSecondaryText: { color: "#183153" },
  row: { flexDirection: "row", gap: 8 },
  spinner: { marginTop: 20 },
});