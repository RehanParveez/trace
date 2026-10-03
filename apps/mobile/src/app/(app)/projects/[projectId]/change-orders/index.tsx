import { useCallback, useState } from "react";
import {ActivityIndicator, Alert, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import {Stack, router, useFocusEffect, useLocalSearchParams,
} from "expo-router";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "../../../../../components/LanguageSwitcher";
import { restoreSession } from "../../../../../api/client";
import {approveChangeOrder, cancelChangeOrder, createChangeOrder, getChangeOrder, getProjectChangeOrderSummary, listChangeOrders, rejectChangeOrder,
} from "../../../../../api/changeOrders";
import {listBOQItems, listProjectBOQVersions,
} from "../../../../../api/drawingsBoq";
import { getProject } from "../../../../../api/projects";
import type {AuthUser, BOQItem, BOQVersion, ChangeOrderDetail, ChangeOrderLineItemInput, ChangeOrderType, Project, ProjectChangeOrderSummary,
} from "../../../../../api/types";

const PAGE_SIZE = 20;

const C = {
  background: "#F3EEE4",
  surface: "#FFFEFB",
  surfaceMuted: "#F7F1E7",
  navy: "#080D18",
  text: "#17212F",
  secondary: "#5C5347",
  muted: "#82796C",
  border: "#E5DCCB",
  gold: "#D9A441",
  green: "#26734D",
  greenBg: "#E8F2E9",
  amber: "#A96516",
  amberBg: "#F8EDDA",
  red: "#A33A32",
  redBg: "#F9E9E5",
};

type LineDraft = {
  mode: "new" | "adjust";
  description: string;
  unit: string;
  boqItemId: string;
  quantity: string;
  unitRate: string;
};

const newLine = (): LineDraft => ({
  mode: "new",
  description: "",
  unit: "",
  boqItemId: "",
  quantity: "",
  unitRate: "",
});

function money(value: number | string, currency: string, locale?: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);

  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString(locale)} ${currency}`;
  }
}

function humanize(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function ProjectChangeOrdersScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = i18n.resolvedLanguage || i18n.language;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [orders, setOrders] = useState<ChangeOrderDetail[]>([]);
  const [summary, setSummary] = useState<ProjectChangeOrderSummary | null>(null);
  const [versions, setVersions] = useState<BOQVersion[]>([]);
  const [boqItems, setBoqItems] = useState<BOQItem[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [ordersPage, setOrdersPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [changeType, setChangeType] = useState<ChangeOrderType>("ADDITION");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [clientReference, setClientReference] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([newLine()]);

  const [selectedOrder, setSelectedOrder] =
    useState<ChangeOrderDetail | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const permissionKeys = user?.role.permissions.map((permission) => permission.key) ?? [];
  const canRead = permissionKeys.includes("change_order:read");
  const canCreate = permissionKeys.includes("change_order:create");
  const canApprove = permissionKeys.includes("change_order:approve");
  const canReadBoq = permissionKeys.includes("drawing:read");

  function changeTypeLabel(value: ChangeOrderType): string {
    return t(`changeOrders.type.${value.toLowerCase()}`, {
      defaultValue: humanize(value),
    });
  }

  function changeStatusLabel(value: string): string {
    return t(`changeOrders.status.${value.toLowerCase()}`, {
      defaultValue: humanize(value),
    });
  }

  const load = useCallback(
    async (refresh = false) => {
      if (!projectId) {
        setError(t("changeOrders.projectIdMissing"));
        setLoading(false);
        return;
      }

      if (refresh) setRefreshing(true);
      else setLoading(true);

      setError("");
      setNotice("");
      setOrdersPage(1);

      try {
        const currentUser = await restoreSession();
        if (!currentUser) {
          router.replace("/");
          return;
        }

        setUser(currentUser);

        const hasRead = currentUser.role.permissions.some(
          (permission) => permission.key === "change_order:read",
        );

        if (!hasRead) {
          setProject(null);
          setOrders([]);
          setSummary(null);
          setVersions([]);
          setBoqItems([]);
          return;
        }

        const canLoadBoq = currentUser.role.permissions.some(
          (permission) =>
            permission.key === "change_order:create" &&
            currentUser.role.permissions.some(
              (item) => item.key === "drawing:read",
            ),
        );

        const [projectResult, orderRows, summaryResult, versionRows] =
          await Promise.all([
            getProject(projectId),
            listChangeOrders(projectId),
            getProjectChangeOrderSummary(projectId),
            canLoadBoq ? listProjectBOQVersions(projectId) : Promise.resolve([]),
          ]);

        setProject(projectResult);
        setOrders(orderRows);
        setSummary(summaryResult);
        setVersions(versionRows);

        const keepVersion = versionRows.some(
          (version) => version.id === selectedVersionId,
        );
        const nextVersionId = keepVersion
          ? selectedVersionId
          : versionRows.find((version) => version.status === "ACTIVE")?.id ??
            versionRows[0]?.id ??
            "";

        setSelectedVersionId(nextVersionId);

        if (nextVersionId && canLoadBoq) {
          const items = await listBOQItems(nextVersionId);
          setBoqItems(items);
        } else {
          setBoqItems([]);
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("changeOrders.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, selectedVersionId, t],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function selectVersion(versionId: string) {
    setSelectedVersionId(versionId);
    setBoqItems([]);
    setError("");

    if (!versionId || !canReadBoq) return;

    try {
      setBoqItems(await listBOQItems(versionId));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("changeOrders.loadBoqItemsFailure"),
      );
    }
  }

  function resetCreateForm() {
    setChangeType("ADDITION");
    setTitle("");
    setDescription("");
    setClientReference("");
    setLines([newLine()]);
  }

  function updateLine(index: number, patch: Partial<LineDraft>) {
    setLines((current) =>
      current.map((line, lineIndex) =>
        lineIndex === index ? { ...line, ...patch } : line,
      ),
    );
  }

  function validateAndBuildLines(): ChangeOrderLineItemInput[] | null {
    if (lines.length === 0) {
      setError(t("changeOrders.addAtLeastOneLine"));
      return null;
    }

    const result: ChangeOrderLineItemInput[] = [];

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      const quantity = Number(line.quantity);
      const unitRate =
        line.unitRate.trim() === "" ? null : Number(line.unitRate);
      const lineNumber = index + 1;

      if (!line.description.trim() || !line.unit.trim()) {
        setError(
          t("changeOrders.lineDescriptionAndUnitRequired", {
            index: lineNumber,
          }),
        );
        return null;
      }
      if (!Number.isFinite(quantity)) {
        setError(
          t("changeOrders.lineQuantityInvalid", { index: lineNumber }),
        );
        return null;
      }
      if (unitRate !== null && (!Number.isFinite(unitRate) || unitRate < 0)) {
        setError(
          t("changeOrders.lineRateInvalid", { index: lineNumber }),
        );
        return null;
      }

      if (line.mode === "new") {
        if (quantity <= 0) {
          setError(
            t("changeOrders.newLineQuantityPositive", { index: lineNumber }),
          );
          return null;
        }
        if (unitRate === null) {
          setError(
            t("changeOrders.newLineRateRequired", { index: lineNumber }),
          );
          return null;
        }
        if (changeType === "OMISSION") {
          setError(t("changeOrders.omissionMustAdjust"));
          return null;
        }

        result.push({
          description: line.description.trim(),
          unit: line.unit.trim(),
          boq_item_id: null,
          quantity,
          unit_rate: unitRate,
        });
      } else {
        if (!line.boqItemId) {
          setError(
            t("changeOrders.selectBoqItemForLine", { index: lineNumber }),
          );
          return null;
        }
        if (quantity === 0) {
          setError(
            t("changeOrders.adjustmentQuantityNonzero", {
              index: lineNumber,
            }),
          );
          return null;
        }
        if (changeType === "ADDITION" && quantity < 0) {
          setError(t("changeOrders.additionQuantityPositive"));
          return null;
        }
        if (changeType === "OMISSION" && quantity > 0) {
          setError(t("changeOrders.omissionQuantityNegative"));
          return null;
        }

        result.push({
          description: line.description.trim(),
          unit: line.unit.trim(),
          boq_item_id: line.boqItemId,
          quantity,
          unit_rate: unitRate,
        });
      }
    }

    return result;
  }

  async function submitCreate() {
    if (!canCreate || !canReadBoq || !projectId || saving) return;

    if (!selectedVersionId) {
      setError(t("changeOrders.selectBoqVersion"));
      return;
    }
    if (!title.trim()) {
      setError(t("changeOrders.titleRequired"));
      return;
    }

    const lineItems = validateAndBuildLines();
    if (!lineItems) return;

    setSaving(true);
    setError("");

    try {
      await createChangeOrder({
        project_id: projectId,
        boq_version_id: selectedVersionId,
        change_type: changeType,
        title: title.trim(),
        description: description.trim() || null,
        client_reference: clientReference.trim() || null,
        line_items: lineItems,
      });

      setCreateOpen(false);
      resetCreateForm();
      setNotice(t("changeOrders.draftCreated"));
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("changeOrders.createFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  async function openDetail(changeOrderId: string) {
    setDetailLoading(true);
    setError("");
    setSelectedOrder(null);

    try {
      setSelectedOrder(await getChangeOrder(changeOrderId));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("changeOrders.detailFailure"),
      );
    } finally {
      setDetailLoading(false);
    }
  }

  async function reloadSelected(changeOrderId: string) {
    await load(true);
    try {
      setSelectedOrder(await getChangeOrder(changeOrderId));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("changeOrders.refreshDetailFailure"),
      );
    }
  }

  async function runAction(action: "approve" | "reject" | "cancel") {
    if (!selectedOrder || saving) return;

    const current = selectedOrder;
    setSaving(true);
    setError("");

    try {
      if (action === "approve") {
        await approveChangeOrder(current.id, current.version);
        setNotice(t("changeOrders.approvedNotice"));
      } else if (action === "reject") {
        if (!rejectReason.trim()) {
          setError(t("changeOrders.rejectionReasonRequired"));
          return;
        }
        await rejectChangeOrder(
          current.id,
          current.version,
          rejectReason.trim(),
        );
        setRejectOpen(false);
        setRejectReason("");
        setNotice(t("changeOrders.rejectedNotice"));
      } else {
        await cancelChangeOrder(current.id, current.version);
        setNotice(t("changeOrders.cancelledNotice"));
      }

      await reloadSelected(current.id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("changeOrders.actionFailure", {
              action: t(`changeOrders.action.${action}`),
            }),
      );
    } finally {
      setSaving(false);
    }
  }

  function confirmAction(action: "approve" | "cancel") {
    if (!selectedOrder) return;

    const isApprove = action === "approve";
    Alert.alert(
      t(
        isApprove
          ? "changeOrders.approveConfirmTitle"
          : "changeOrders.cancelConfirmTitle",
      ),
      t(
        isApprove
          ? "changeOrders.approveConfirmMessage"
          : "changeOrders.cancelConfirmMessage",
      ),
      [
        { text: t("changeOrders.keep"), style: "cancel" },
        {
          text: t(`changeOrders.action.${action}`),
          style: action === "cancel" ? "destructive" : "default",
          onPress: () => void runAction(action),
        },
      ],
    );
  }

  const totalPages = Math.ceil(orders.length / PAGE_SIZE);
  const pageStart = (ordersPage - 1) * PAGE_SIZE;
  const visibleOrders = orders.slice(pageStart, pageStart + PAGE_SIZE);
  const visiblePages = Array.from(
    { length: totalPages },
    (_, index) => index + 1,
  ).filter((page) => Math.abs(page - ordersPage) <= 2);

  if (loading) {
    return (
      <View style={[styles.page, isUrdu && styles.rtlPage]}>
        <Stack.Screen options={{ title: t("changeOrders.pageTitle") }} />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("changeOrders.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("changeOrders.loading")}
          </Text>
        </View>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={[styles.page, isUrdu && styles.rtlPage]}>
        <Stack.Screen options={{ title: t("changeOrders.pageTitle") }} />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("changeOrders.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <View style={styles.messageCard}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("changeOrders.accessUnavailable")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("changeOrders.accessDenied")}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => void load(true)}
          tintColor={C.navy}
          colors={[C.navy]}
        />
      }
    >
      <Stack.Screen options={{ title: t("changeOrders.pageTitle") }} />

      <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
        <View style={styles.headerContent}>
          <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
            {t("changeOrders.eyebrow")}
          </Text>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {project?.name ?? t("changeOrders.pageTitle")}
          </Text>
          {project?.code ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("changeOrders.projectCode", { code: project.code })}
            </Text>
          ) : null}
        </View>
        <LanguageSwitcher />
      </View>

      {error ? (
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error}
        </Text>
      ) : null}
      {notice ? (
        <Text style={[styles.notice, isUrdu && styles.rtlText]}>
          {notice}
        </Text>
      ) : null}

      {summary ? (
        <View style={styles.card}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("changeOrders.summaryTitle")}
          </Text>
          <InfoRow
            label={t("changeOrders.approved")}
            value={String(summary.approved_count)}
            isUrdu={isUrdu}
          />
          <InfoRow
            label={t("changeOrders.drafts")}
            value={String(summary.draft_count)}
            isUrdu={isUrdu}
          />
          <InfoRow
            label={t("changeOrders.approvedNetImpact")}
            value={money(
              summary.approved_net_value_impact,
              summary.currency,
              locale,
            )}
            isUrdu={isUrdu}
          />
        </View>
      ) : null}

      {canCreate ? (
        <Pressable
          style={styles.primaryButton}
          accessibilityRole="button"
          onPress={() => {
            setError("");
            setCreateOpen((value) => !value);
          }}
        >
          <Text style={styles.primaryButtonText}>
            {createOpen
              ? t("changeOrders.closeCreateForm")
              : t("changeOrders.createChangeOrder")}
          </Text>
        </Pressable>
      ) : null}

      {createOpen ? (
        <View style={styles.card}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("changeOrders.newDraft")}
          </Text>

          {!canReadBoq ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>
              {t("changeOrders.boqPermissionRequired")}
            </Text>
          ) : versions.length === 0 ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("changeOrders.noBoqVersions")}
            </Text>
          ) : (
            <>
              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("changeOrders.boqVersion")}
              </Text>
              {versions.map((version) => (
                <Choice
                  key={version.id}
                  label={`${version.label} · ${t(
                    `changeOrders.versionStatus.${version.status.toLowerCase()}`,
                    { defaultValue: humanize(version.status) },
                  )}`}
                  selected={selectedVersionId === version.id}
                  onPress={() => void selectVersion(version.id)}
                  isUrdu={isUrdu}
                />
              ))}

              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("changeOrders.changeType")}
              </Text>
              <View style={[styles.row, isUrdu && styles.rtlRow]}>
                {(["ADDITION", "OMISSION", "VARIATION"] as const).map(
                  (type) => (
                    <Choice
                      key={type}
                      label={changeTypeLabel(type)}
                      selected={changeType === type}
                      onPress={() => setChangeType(type)}
                      isUrdu={isUrdu}
                    />
                  ),
                )}
              </View>

              <Field
                label={t("changeOrders.title")}
                value={title}
                onChangeText={setTitle}
                isUrdu={isUrdu}
              />
              <Field
                label={t("changeOrders.descriptionOptional")}
                value={description}
                onChangeText={setDescription}
                multiline
                isUrdu={isUrdu}
              />
              <Field
                label={t("changeOrders.clientReferenceOptional")}
                value={clientReference}
                onChangeText={setClientReference}
                isUrdu={isUrdu}
              />

              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("changeOrders.lineItems")}
              </Text>
              {lines.map((line, index) => (
                <View key={index} style={styles.lineCard}>
                  <Text style={[styles.lineTitle, isUrdu && styles.rtlText]}>
                    {t("changeOrders.lineNumber", { index: index + 1 })}
                  </Text>
                  <View style={[styles.row, isUrdu && styles.rtlRow]}>
                    <Choice
                      label={t("changeOrders.newItem")}
                      selected={line.mode === "new"}
                      onPress={() =>
                        updateLine(index, {
                          mode: "new",
                          boqItemId: "",
                        })
                      }
                      isUrdu={isUrdu}
                    />
                    <Choice
                      label={t("changeOrders.adjustBoqItem")}
                      selected={line.mode === "adjust"}
                      onPress={() => updateLine(index, { mode: "adjust" })}
                      isUrdu={isUrdu}
                    />
                  </View>

                  {line.mode === "adjust" ? (
                    <View>
                      <Text style={[styles.label, isUrdu && styles.rtlText]}>
                        {t("changeOrders.existingBoqItem")}
                      </Text>
                      {boqItems.map((item) => (
                        <Choice
                          key={item.id}
                          label={`${item.material_name} · ${item.quantity} ${item.unit}`}
                          selected={line.boqItemId === item.id}
                          onPress={() =>
                            updateLine(index, {
                              boqItemId: item.id,
                              description: t(
                                "changeOrders.adjustmentDescription",
                                { name: item.material_name },
                              ),
                              unit: item.unit,
                            })
                          }
                          isUrdu={isUrdu}
                        />
                      ))}
                      {boqItems.length === 0 ? (
                        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                          {t("changeOrders.noBoqItems")}
                        </Text>
                      ) : null}
                    </View>
                  ) : null}

                  <Field
                    label={t("changeOrders.description")}
                    value={line.description}
                    onChangeText={(value) =>
                      updateLine(index, { description: value })
                    }
                    isUrdu={isUrdu}
                  />
                  <Field
                    label={t("changeOrders.unit")}
                    value={line.unit}
                    onChangeText={(value) => updateLine(index, { unit: value })}
                    isUrdu={isUrdu}
                  />
                  <Field
                    label={
                      line.mode === "adjust"
                        ? t("changeOrders.quantityChange")
                        : t("changeOrders.quantity")
                    }
                    value={line.quantity}
                    onChangeText={(value) =>
                      updateLine(index, { quantity: value })
                    }
                    keyboardType="decimal-pad"
                    isUrdu={isUrdu}
                  />
                  <Field
                    label={
                      line.mode === "adjust"
                        ? t("changeOrders.rateOverrideOptional")
                        : t("changeOrders.unitRate")
                    }
                    value={line.unitRate}
                    onChangeText={(value) =>
                      updateLine(index, { unitRate: value })
                    }
                    keyboardType="decimal-pad"
                    isUrdu={isUrdu}
                  />

                  {lines.length > 1 ? (
                    <Pressable
                      onPress={() =>
                        setLines((current) =>
                          current.filter(
                            (_, lineIndex) => lineIndex !== index,
                          ),
                        )
                      }
                    >
                      <Text style={styles.dangerLink}>
                        {t("changeOrders.removeLine")}
                      </Text>
                    </Pressable>
                  ) : null}
                </View>
              ))}

              <Pressable
                style={styles.secondaryButton}
                onPress={() => setLines((current) => [...current, newLine()])}
              >
                <Text style={styles.secondaryButtonText}>
                  {t("changeOrders.addLineItem")}
                </Text>
              </Pressable>

              <Pressable
                style={[
                  styles.primaryButton,
                  saving && styles.disabledButton,
                ]}
                disabled={saving || !canReadBoq || versions.length === 0}
                onPress={() => void submitCreate()}
              >
                <Text style={styles.primaryButtonText}>
                  {saving
                    ? t("changeOrders.creating")
                    : t("changeOrders.createDraft")}
                </Text>
              </Pressable>
            </>
          )}
        </View>
      ) : null}

      <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
        {t("changeOrders.ordersTitle")}
      </Text>

      {orders.length === 0 ? (
        <View style={styles.card}>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("changeOrders.noOrders")}
          </Text>
        </View>
      ) : (
        <>
          {visibleOrders.map((order) => (
            <Pressable
              key={order.id}
              style={styles.card}
              accessibilityRole="button"
              onPress={() => void openDetail(order.id)}
            >
              <View style={[styles.rowBetween, isUrdu && styles.rtlRow]}>
                <Text style={[styles.orderTitle, isUrdu && styles.rtlText]}>
                  {t("changeOrders.orderTitle", {
                    number: order.change_order_number,
                    title: order.title,
                  })}
                </Text>
                <Text style={styles.status}>
                  {changeStatusLabel(order.status)}
                </Text>
              </View>
              <InfoRow
                label={t("changeOrders.type")}
                value={changeTypeLabel(order.change_type)}
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("changeOrders.valueImpact")}
                value={money(order.value_impact, order.currency, locale)}
                isUrdu={isUrdu}
              />
              <Text style={styles.link}>
                {t("changeOrders.openDetails")}
              </Text>
            </Pressable>
          ))}

          {totalPages > 1 ? (
            <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
              <Pressable
                style={[
                  styles.pageNavButton,
                  ordersPage === 1 && styles.disabledButton,
                ]}
                disabled={ordersPage === 1}
                onPress={() =>
                  setOrdersPage((current) => Math.max(1, current - 1))
                }
                accessibilityRole="button"
              >
                <Text style={styles.pageNavText}>
                  {t("changeOrders.previousPage")}
                </Text>
              </Pressable>

              <View style={[styles.pageNumbers, isUrdu && styles.rtlRow]}>
                {visiblePages.map((page) => (
                  <Pressable
                    key={page}
                    style={[
                      styles.pageNumber,
                      page === ordersPage && styles.pageNumberSelected,
                    ]}
                    disabled={page === ordersPage}
                    onPress={() => setOrdersPage(page)}
                    accessibilityRole="button"
                    accessibilityState={{ selected: page === ordersPage }}
                  >
                    <Text
                      style={[
                        styles.pageNumberText,
                        page === ordersPage && styles.pageNumberTextSelected,
                      ]}
                    >
                      {page}
                    </Text>
                  </Pressable>
                ))}
              </View>

              <Pressable
                style={[
                  styles.pageNavButton,
                  ordersPage === totalPages && styles.disabledButton,
                ]}
                disabled={ordersPage === totalPages}
                onPress={() =>
                  setOrdersPage((current) =>
                    Math.min(totalPages, current + 1),
                  )
                }
                accessibilityRole="button"
              >
                <Text style={styles.pageNavText}>
                  {t("changeOrders.nextPage")}
                </Text>
              </Pressable>
            </View>
          ) : null}
        </>
      )}

      <Modal
        visible={detailLoading || selectedOrder !== null}
        animationType="slide"
        onRequestClose={() => {
          setSelectedOrder(null);
          setRejectOpen(false);
          setError("");
        }}
      >
        <ScrollView
          contentContainerStyle={[
            styles.modalPage,
            isUrdu && styles.rtlPage,
          ]}
        >
          <View style={[styles.modalHeader, isUrdu && styles.rtlRow]}>
            <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
              {detailLoading
                ? t("changeOrders.loadingDetail")
                : selectedOrder
                  ? t("changeOrders.detailTitle", {
                      number: selectedOrder.change_order_number,
                    })
                  : ""}
            </Text>
            <LanguageSwitcher />
          </View>

          {detailLoading ? (
            <ActivityIndicator size="large" color={C.navy} />
          ) : selectedOrder ? (
            <>
              {error ? (
                <Text style={[styles.error, isUrdu && styles.rtlText]}>
                  {error}
                </Text>
              ) : null}
              <Text style={[styles.orderTitle, isUrdu && styles.rtlText]}>
                {selectedOrder.title}
              </Text>
              <InfoRow
                label={t("changeOrders.status")}
                value={changeStatusLabel(selectedOrder.status)}
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("changeOrders.type")}
                value={changeTypeLabel(selectedOrder.change_type)}
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("changeOrders.valueImpact")}
                value={money(
                  selectedOrder.value_impact,
                  selectedOrder.currency,
                  locale,
                )}
                isUrdu={isUrdu}
              />
              {selectedOrder.description ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {selectedOrder.description}
                </Text>
              ) : null}
              {selectedOrder.client_reference ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {t("changeOrders.clientReference", {
                    reference: selectedOrder.client_reference,
                  })}
                </Text>
              ) : null}
              {selectedOrder.rejection_reason ? (
                <Text style={[styles.error, isUrdu && styles.rtlText]}>
                  {t("changeOrders.rejectionReason", {
                    reason: selectedOrder.rejection_reason,
                  })}
                </Text>
              ) : null}

              <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
                {t("changeOrders.lineItems")}
              </Text>
              {selectedOrder.line_items.map((line) => (
                <View key={line.id} style={styles.lineCard}>
                  <Text style={[styles.lineTitle, isUrdu && styles.rtlText]}>
                    {line.description}
                  </Text>
                  <InfoRow
                    label={t("changeOrders.unit")}
                    value={line.unit}
                    isUrdu={isUrdu}
                  />
                  <InfoRow
                    label={t("changeOrders.quantityChange")}
                    value={`${Number(line.quantity) > 0 ? "+" : ""}${line.quantity}`}
                    isUrdu={isUrdu}
                  />
                  <InfoRow
                    label={t("changeOrders.unitRate")}
                    value={
                      line.unit_rate === null
                        ? t("changeOrders.boqRate")
                        : money(line.unit_rate, selectedOrder.currency, locale)
                    }
                    isUrdu={isUrdu}
                  />
                  <InfoRow
                    label={t("changeOrders.realizedImpact")}
                    value={
                      line.realized_value_impact === null
                        ? t("changeOrders.pendingApproval")
                        : money(
                            line.realized_value_impact,
                            selectedOrder.currency,
                            locale,
                          )
                    }
                    isUrdu={isUrdu}
                  />
                  {line.created_boq_item_id ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {t("changeOrders.approvedAsNewBoqItem")}
                    </Text>
                  ) : null}
                </View>
              ))}

              {selectedOrder.status === "DRAFT" &&
              canApprove &&
              !rejectOpen ? (
                <View style={[styles.row, isUrdu && styles.rtlRow]}>
                  <ActionButton
                    label={t("changeOrders.approve")}
                    disabled={saving}
                    onPress={() => confirmAction("approve")}
                  />
                  <ActionButton
                    label={t("changeOrders.reject")}
                    secondary
                    disabled={saving}
                    onPress={() => {
                      setError("");
                      setRejectReason("");
                      setRejectOpen(true);
                    }}
                  />
                </View>
              ) : null}

              {selectedOrder.status === "DRAFT" && canCreate ? (
                <ActionButton
                  label={t("changeOrders.cancelDraft")}
                  secondary
                  disabled={saving}
                  onPress={() => confirmAction("cancel")}
                />
              ) : null}

              {rejectOpen ? (
                <View style={styles.card}>
                  <Text style={[styles.label, isUrdu && styles.rtlText]}>
                    {t("changeOrders.reasonForRejection")}
                  </Text>
                  <TextInput
                    style={[
                      styles.input,
                      styles.multiline,
                      isUrdu && styles.rtlText,
                    ]}
                    value={rejectReason}
                    onChangeText={setRejectReason}
                    multiline
                    textAlignVertical="top"
                    textAlign={isUrdu ? "right" : "left"}
                    placeholderTextColor={C.muted}
                  />
                  <ActionButton
                    label={
                      saving
                        ? t("changeOrders.rejecting")
                        : t("changeOrders.confirmRejection")
                    }
                    disabled={saving || !rejectReason.trim()}
                    onPress={() => void runAction("reject")}
                  />
                  <ActionButton
                    label={t("changeOrders.back")}
                    secondary
                    disabled={saving}
                    onPress={() => setRejectOpen(false)}
                  />
                </View>
              ) : null}
            </>
          ) : null}

          <ActionButton
            label={t("changeOrders.close")}
            secondary
            disabled={saving}
            onPress={() => {
              setSelectedOrder(null);
              setRejectOpen(false);
              setError("");
            }}
          />
        </ScrollView>
      </Modal>
    </ScrollView>
  );
}

function InfoRow({
  label,
  value,
  isUrdu,
}: {
  label: string;
  value: string;
  isUrdu: boolean;
}) {
  return (
    <View style={[styles.infoRow, isUrdu && styles.rtlRow]}>
      <Text style={[styles.infoLabel, isUrdu && styles.rtlText]}>
        {label}
      </Text>
      <Text style={[styles.infoValue, isUrdu && styles.rtlText]}>
        {value}
      </Text>
    </View>
  );
}

function Field({
  label,
  value,
  onChangeText,
  keyboardType,
  multiline,
  isUrdu,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  multiline?: boolean;
  isUrdu: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={[styles.label, isUrdu && styles.rtlText]}>{label}</Text>
      <TextInput
        style={[
          styles.input,
          multiline && styles.multiline,
          isUrdu && styles.rtlText,
        ]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType ?? "default"}
        multiline={multiline}
        textAlignVertical={multiline ? "top" : "center"}
        textAlign={isUrdu ? "right" : "left"}
        placeholderTextColor={C.muted}
      />
    </View>
  );
}

function Choice({
  label,
  selected,
  onPress,
  isUrdu,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[styles.choice, selected && styles.choiceSelected]}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
    >
      <Text
        style={[
          styles.choiceText,
          selected && styles.choiceTextSelected,
          isUrdu && styles.rtlText,
        ]}
      >
        {selected ? "✓ " : ""}
        {label}
      </Text>
    </Pressable>
  );
}

function ActionButton({
  label,
  disabled,
  secondary,
  onPress,
}: {
  label: string;
  disabled: boolean;
  secondary?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[
        styles.actionButton,
        secondary && styles.secondaryButton,
        disabled && styles.disabledButton,
      ]}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
    >
      <Text
        style={[
          styles.actionButtonText,
          secondary && styles.secondaryButtonText,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  modalPage: { flexGrow: 1, padding: 22, paddingTop: 32, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 14 },
  modalHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 12 },
  headerContent: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: C.background, padding: 24 },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 26, fontWeight: "800", marginTop: 5 },
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: "800", marginTop: 18, marginBottom: 10 },
  card: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, padding: 16, marginTop: 12 },
  messageCard: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, padding: 18, marginTop: 12 },
  lineCard: { backgroundColor: C.surfaceMuted, borderRadius: 12, borderWidth: 1, borderColor: C.border, padding: 14, marginTop: 10 },
  lineTitle: { color: C.text, fontSize: 15, fontWeight: "800" },
  orderTitle: { color: C.text, fontSize: 16, fontWeight: "800", flexShrink: 1 },
  status: { color: C.navy, backgroundColor: C.surfaceMuted, overflow: "hidden", borderRadius: 99, paddingHorizontal: 9, paddingVertical: 5, fontSize: 11, fontWeight: "800" },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 8, borderTopWidth: 1, borderTopColor: C.border },
  infoLabel: { color: C.secondary, fontSize: 13, flex: 1 },
  infoValue: { color: C.text, fontSize: 13, fontWeight: "700", flex: 1, textAlign: "right" },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  error: { color: C.red, backgroundColor: C.redBg, borderWidth: 1, borderColor: "#EAC6C0", borderRadius: 11, fontSize: 13, lineHeight: 19, padding: 12, marginTop: 10 },
  notice: { color: C.green, backgroundColor: C.greenBg, borderWidth: 1, borderColor: "#CEE1D2", borderRadius: 11, fontSize: 13, lineHeight: 19, padding: 12, marginTop: 10 },
  label: { color: C.secondary, fontSize: 13, fontWeight: "700", marginTop: 13, marginBottom: 7 },
  field: { marginTop: 10 },
  input: { minHeight: 48, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, paddingHorizontal: 13, color: C.text, fontSize: 14 },
  multiline: { minHeight: 82, paddingTop: 12 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 },
  rowBetween: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  choice: { minHeight: 42, justifyContent: "center", paddingHorizontal: 12, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, marginTop: 7 },
  choiceSelected: { borderColor: C.navy, backgroundColor: C.surfaceMuted },
  choiceText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  choiceTextSelected: { color: C.navy },
  link: { color: C.navy, fontWeight: "800", marginTop: 12 },
  dangerLink: { color: C.red, fontWeight: "800", marginTop: 12 },
  primaryButton: { minHeight: 48, alignItems: "center", justifyContent: "center", backgroundColor: C.navy, borderRadius: 11, padding: 14, marginTop: 14 },
  primaryButtonText: { color: C.surface, fontSize: 13, fontWeight: "800", textAlign: "center" },
  secondaryButton: { minHeight: 46, alignItems: "center", justifyContent: "center", backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 10, padding: 13, marginTop: 12 },
  secondaryButtonText: { color: C.navy, fontWeight: "800", textAlign: "center" },
  actionButton: { minHeight: 46, alignItems: "center", justifyContent: "center", backgroundColor: C.navy, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, marginTop: 12 },
  actionButtonText: { color: C.surface, fontWeight: "800", textAlign: "center" },
  disabledButton: { opacity: 0.5 },
  allocationHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10, marginTop: 18, marginBottom: 8 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 16, padding: 10, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13 },
  pageNavButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: C.surfaceMuted },
  pageNavText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pageNumbers: { flexDirection: "row", alignItems: "center", gap: 5 },
  pageNumber: { minWidth: 36, height: 36, alignItems: "center", justifyContent: "center", borderRadius: 9, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  pageNumberSelected: { backgroundColor: C.navy, borderColor: C.navy },
  pageNumberText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  pageNumberTextSelected: { color: C.surface },
});