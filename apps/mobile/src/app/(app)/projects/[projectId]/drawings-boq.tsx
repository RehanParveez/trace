import { useCallback, useEffect, useRef, useState } from "react";
import {Alert, ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import * as DocumentPicker from "expo-document-picker";
import { restoreSession } from "../../../../api/client";
import { getProject } from "../../../../api/projects";
import {addCustomBOQItem, approveBOQItem, createBOQVersion, deleteDrawing, getBOQSummary, getDrawingAudit, listBOQItems, listProjectBOQVersions, listProjectDrawings, reviseDrawing, 
  suggestBOQItemsFromPDF, updateBOQItem, uploadProjectDrawing,
} from "../../../../api/drawingsBoq";
import type {BOQItem, BOQSummary, BOQVersion, Drawing, DrawingAudit, Project,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { isEngine, isLocked } from "../../../../features/drawingsBoq/lifecycle";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { describeError } from "../../../../features/drawingsBoq/errors";

const PAGE_SIZE = 10;

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

function formatDate(value: string | null, locale: string, notSet: string) {
  if (!value) return notSet;
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(locale);
}

function formatMoney(
  value: number | string | null,
  locale: string,
  notAvailable: string,
) {
  if (value === null) return notAvailable;
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "PKR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function DrawingsBoqScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [versions, setVersions] = useState<BOQVersion[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [drawingsError, setDrawingsError] = useState("");
  const [boqError, setBoqError] = useState("");

  const [drawingsPage, setDrawingsPage] = useState(1);
  const [versionsPage, setVersionsPage] = useState(1);
  const [itemsPage, setItemsPage] = useState(1);
  const [expandedVersion, setExpandedVersion] = useState("");
  const [boqLoading, setBoqLoading] = useState(false);
  const [boqItems, setBoqItems] = useState<BOQItem[]>([]);
  const [boqSummary, setBoqSummary] = useState<BOQSummary | null>(null);
  const boqRequest = useRef(0);

  const [versionLabel, setVersionLabel] = useState("");
  const [itemName, setItemName] = useState("");
  const [itemUnit, setItemUnit] = useState("");
  const [itemQuantity, setItemQuantity] = useState("");
  const [itemCategory, setItemCategory] = useState("");
  const [itemRate, setItemRate] = useState("");
  const [editingItemId, setEditingItemId] = useState("");
  const [editingItemVersion, setEditingItemVersion] = useState<number | null>(
    null,
  );
  const [itemReason, setItemReason] = useState("");
  const [editingIsModel, setEditingIsModel] = useState(false);
  const [audits, setAudits] = useState<Record<string, DrawingAudit>>({});

  const canUpload = hasPerm(permissions, PERM.DRAWING_CREATE);
  const canCreateItem = hasPerm(permissions, PERM.BOQ_ITEM_CREATE);
  const canUpdateItem = hasPerm(permissions, PERM.BOQ_UPDATE);
  const canApprove = hasPerm(permissions, PERM.BOQ_APPROVE);
  const canDeleteDrawing = hasPerm(permissions, PERM.DRAWING_DELETE);
  const canRun = hasPerm(permissions, PERM.CALC_RUN);

  const currentDrawings = drawings.filter(
    (drawing) => drawing.is_current_revision,
  );
  const drawingsPages = pageCount(currentDrawings.length);
  const versionsPages = pageCount(versions.length);
  const itemsPages = pageCount(boqItems.length);
  const visibleDrawings = paginate(currentDrawings, drawingsPage);
  const visibleVersions = paginate(versions, versionsPage);
  const visibleItems = paginate(boqItems, itemsPage);
  const expandedVersionObj =
    versions.find((version) => version.id === expandedVersion) ?? null;
  const engineVersion = expandedVersionObj ? isEngine(expandedVersionObj) : false;
  const locked = expandedVersionObj ? isLocked(expandedVersionObj) : false;

  const load = useCallback(
    async (silent = false) => {
      if (!projectId) {
        setError(t("drawingsBoq.projectNotFound"));
        setLoading(false);
        return;
      }

      if (!silent) {
        setLoading(true);
        setError("");
        setDrawingsError("");
        setBoqError("");
      }

      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }

        setPermissions(
          user.role.permissions.map((permission) => permission.key),
        );
        setProject(await getProject(projectId));

        const [drawingResult, versionResult] = await Promise.allSettled([
          listProjectDrawings(projectId),
          listProjectBOQVersions(projectId),
        ]);

        if (drawingResult.status === "fulfilled") {
          setDrawings(drawingResult.value);
          setDrawingsPage(1);
        } else {
          setDrawingsError(
            drawingResult.reason instanceof Error
              ? drawingResult.reason.message
              : t("drawingsBoq.drawingsLoadFailure"),
          );
        }

        if (versionResult.status === "fulfilled") {
          setVersions(versionResult.value);
          setVersionsPage(1);
        } else {
          setBoqError(
            versionResult.reason instanceof Error
              ? versionResult.reason.message
              : t("drawingsBoq.versionsLoadFailure"),
          );
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("drawingsBoq.projectLoadFailure"),
        );
      } finally {
        setLoading(false);
      }
    },
    [projectId, t],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const hasPendingDrawing = drawings.some(
    (drawing) =>
      drawing.status === "UPLOADED" || drawing.status === "PROCESSING",
  );

  useEffect(() => {
    if (!hasPendingDrawing) return;
    const timer = setInterval(() => {
      void load(true);
    }, 5000);
    return () => clearInterval(timer);
  }, [hasPendingDrawing, load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");

    try {
      await action();
      await load(true);
    } catch (err) {
      setError(describeError(err, t("drawingsBoq.actionFailure")));
    } finally {
      setBusy(false);
    }
  }

  async function toggleVersion(version: BOQVersion) {
    if (version.origin === "ENGINE" && project) {
      router.push({
        pathname: "/projects/[projectId]/boq-version",
        params: { projectId: project.id, versionId: version.id },
      });
      return;
    }

    if (expandedVersion === version.id) {
      boqRequest.current += 1;
      setExpandedVersion("");
      setBoqLoading(false);
      setBoqItems([]);
      setBoqSummary(null);
      setItemsPage(1);
      setEditingItemId("");
      setEditingItemVersion(null);
      return;
    }

    const requestId = boqRequest.current + 1;
    boqRequest.current = requestId;
    setExpandedVersion(version.id);
    setBoqLoading(true);
    setBoqError("");
    setBoqItems([]);
    setBoqSummary(null);
    setItemsPage(1);
    setEditingItemId("");
    setEditingItemVersion(null);

    try {
      const [items, summary] = await Promise.all([
        listBOQItems(version.id),
        getBOQSummary(version.id),
      ]);

      if (boqRequest.current === requestId) {
        setBoqItems(items);
        setBoqSummary(summary);
      }
    } catch (err) {
      if (boqRequest.current === requestId) {
        setBoqError(
          err instanceof Error
            ? err.message
            : t("drawingsBoq.versionLoadFailure"),
        );
      }
    } finally {
      if (boqRequest.current === requestId) setBoqLoading(false);
    }
  }

  async function refreshExpandedVersion() {
    const version = versions.find((item) => item.id === expandedVersion);
    if (!version) return;

    const requestId = boqRequest.current + 1;
    boqRequest.current = requestId;
    setBoqLoading(true);
    setBoqError("");

    try {
      const [items, summary] = await Promise.all([
        listBOQItems(version.id),
        getBOQSummary(version.id),
      ]);

      if (boqRequest.current === requestId) {
        setBoqItems(items);
        setBoqSummary(summary);
        setItemsPage(1);
      }
    } catch (err) {
      if (boqRequest.current === requestId) {
        setBoqError(
          err instanceof Error
            ? err.message
            : t("drawingsBoq.versionLoadFailure"),
        );
      }
    } finally {
      if (boqRequest.current === requestId) setBoqLoading(false);
    }
  }

  async function handleUploadDrawing() {
    if (!projectId || !canUpload) return;

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*", "*/*"],
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;

      const file = result.assets[0];
      const lowerName = file.name.toLowerCase();
      if (!lowerName.endsWith(".ifc") && !lowerName.endsWith(".pdf")) {
        setError(
          t("drawingsBoq.unsupportedFileType", {
            defaultValue:
              "Upload an .ifc file for automatic BOQ, or a .pdf as a reference drawing.",
          }),
        );
        return;
      }
      setBusy(true);
      setError("");

      await uploadProjectDrawing(projectId, {
        uri: file.uri,
        name: file.name,
        mimeType: file.mimeType,
      });

      await load(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("drawingsBoq.uploadFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleReviseDrawing(drawing: Drawing) {
    if (!canUpload) return;

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "*/*",
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;

      const file = result.assets[0];
      const lowerName = file.name.toLowerCase();
      if (!lowerName.endsWith(".ifc") && !lowerName.endsWith(".pdf")) {
        setError(
          t("drawingsBoq.unsupportedFileType", {
            defaultValue:
              "Upload an .ifc file for automatic BOQ, or a .pdf as a reference drawing.",
          }),
        );
        return;
      }

      setBusy(true);
      setError("");
      await reviseDrawing(drawing.id, {
        uri: file.uri,
        name: file.name,
        mimeType: file.mimeType,
      });
      await load(true);
    } catch (err) {
      setError(describeError(err, t("drawingsBoq.uploadFailure")));
    } finally {
      setBusy(false);
    }
  }

  function handleDeleteDrawing(drawing: Drawing) {
    Alert.alert(
      t("drawingsBoq.deleteDrawingTitle", { defaultValue: "Delete drawing?" }),
      t("drawingsBoq.deleteDrawingBody", {
        defaultValue:
          "{{name}} will be removed. This is blocked if an approved BOQ uses it.",
        name: drawing.original_filename,
      }),
      [
        { text: t("drawingsBoq.cancel"), style: "cancel" },
        {
          text: t("drawingsBoq.delete", { defaultValue: "Delete" }),
          style: "destructive",
          onPress: () =>
            void run(async () => {
              await deleteDrawing(drawing.id);
            }),
        },
      ],
    );
  }

  async function handleShowAudit(drawing: Drawing) {
    setBusy(true);
    setError("");
    try {
      const audit = await getDrawingAudit(drawing.id);
      setAudits((current) => ({ ...current, [drawing.id]: audit }));
    } catch (err) {
      setError(describeError(err, t("drawingsBoq.actionFailure")));
    } finally {
      setBusy(false);
    }
  }

  async function handleSuggestItems(drawing: Drawing) {
    await run(async () => {
      await suggestBOQItemsFromPDF(drawing.id);
    });
  }

  async function handleCreateVersion() {
    if (!projectId) return;

    if (!versionLabel.trim()) {
      setError(t("drawingsBoq.enterVersionLabel"));
      return;
    }

    await run(async () => {
      await createBOQVersion(projectId, { label: versionLabel.trim() });
      setVersionLabel("");
    });
  }

  async function handleAddCustomItem() {
    if (!expandedVersion) {
      setError(t("drawingsBoq.expandVersionFirst"));
      return;
    }
    if (!itemName.trim() || !itemUnit.trim()) {
      setError(t("drawingsBoq.enterMaterialAndUnit"));
      return;
    }

    const quantity = Number(itemQuantity);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError(t("drawingsBoq.quantityPositive"));
      return;
    }

    const rate = itemRate.trim() === "" ? null : Number(itemRate);
    if (rate !== null && !Number.isFinite(rate)) {
      setError(t("drawingsBoq.rateValid"));
      return;
    }

    await run(async () => {
      await addCustomBOQItem(expandedVersion, {
        material_name: itemName.trim(),
        unit: itemUnit.trim(),
        quantity,
        category: itemCategory.trim() || null,
        unit_rate: rate,
      });

      setItemName("");
      setItemUnit("");
      setItemQuantity("");
      setItemCategory("");
      setItemRate("");
      await refreshExpandedVersion();
    });
  }

  function beginEditItem(item: BOQItem) {
    setEditingItemId(item.id);
    setEditingItemVersion(item.version ?? null);
    setEditingIsModel(item.source_kind === "MODEL");
    setItemReason("");
    setItemName(item.material_name);
    setItemUnit(item.unit);
    setItemQuantity(String(item.quantity));
    setItemCategory(item.category ?? "");
    setItemRate(item.unit_rate === null ? "" : String(item.unit_rate));
  }

  function clearItemForm() {
    setItemReason("");
    setEditingIsModel(false);
    setEditingItemId("");
    setEditingItemVersion(null);
    setItemName("");
    setItemUnit("");
    setItemQuantity("");
    setItemCategory("");
    setItemRate("");
  }

  async function handleSaveItem() {
    if (!editingItemId) return;

    if (editingItemVersion == null) {
      setError(t("drawingsBoq.itemVersionMissing"));
      return;
    }
    if (!itemName.trim() || !itemUnit.trim()) {
      setError(t("drawingsBoq.enterMaterialAndUnit"));
      return;
    }

    const quantity = Number(itemQuantity);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError(t("drawingsBoq.quantityPositive"));
      return;
    }

    const rate = itemRate.trim() === "" ? null : Number(itemRate);
    if (rate !== null && !Number.isFinite(rate)) {
      setError(t("drawingsBoq.rateValid"));
      return;
    }

    const original = boqItems.find((item) => item.id === editingItemId);
    const isModel = original?.source_kind === "MODEL";
    const quantityChanged = !original || Number(original.quantity) !== quantity;

    if (isModel && quantityChanged && !itemReason.trim()) {
      setError(
        t("drawingsBoq.adjustmentReasonRequired", {
          defaultValue: "Enter a reason for changing a calculated quantity.",
        }),
      );
      return;
    }

    await run(async () => {
      await updateBOQItem(editingItemId, {
        material_name: itemName.trim(),
        unit: itemUnit.trim(),
        ...(!isModel || quantityChanged ? { quantity } : {}),
        ...(isModel && quantityChanged
          ? { adjustment_reason: itemReason.trim() }
          : {}),
        category: itemCategory.trim() || null,
        unit_rate: rate,
        version: editingItemVersion,
      });

      clearItemForm();
      await refreshExpandedVersion();
    });
  }

  async function handleApproveItem(item: BOQItem) {
    await run(async () => {
      await approveBOQItem(item.id);
      await refreshExpandedVersion();
    });
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("drawingsBoq.loading")}
        </Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, styles.headerCopy, isUrdu && styles.rtlText]}>
            {t("drawingsBoq.title")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error || t("drawingsBoq.projectNotFound")}
        </Text>
        <Pressable onPress={() => router.back()}>
          <Text style={[styles.link, isUrdu && styles.rtlText]}>
            {t("drawingsBoq.backToProject")}
          </Text>
        </Pressable>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("drawingsBoq.backToProjectName", { name: project.name })}
              </Text>
            </Pressable>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("drawingsBoq.title")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
        ) : null}

        <Text style={[styles.section, isUrdu && styles.rtlText]}>
          {t("drawingsBoq.drawings")}
        </Text>

        {drawingsError ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {drawingsError}
          </Text>
        ) : null}

        {canUpload ? (
          <Action
            title={t("drawingsBoq.uploadDrawing")}
            isUrdu={isUrdu}
            onPress={() => void handleUploadDrawing()}
          />
        ) : null}

        {!drawingsError && currentDrawings.length === 0 ? (
          <View style={styles.card}>
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("drawingsBoq.noDrawings")}
            </Text>
          </View>
        ) : (
          <>
            {visibleDrawings.map((drawing) => (
              <View key={drawing.id} style={styles.listCard}>
                <Text style={[styles.itemTitle, isUrdu && styles.rtlText]}>
                  {drawing.original_filename}
                </Text>
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {t("drawingsBoq.formatAndStatus", {
                    format: drawing.format,
                    status: t(
                      `drawingsBoq.status.${drawing.status.toLowerCase()}`,
                      { defaultValue: drawing.status.replaceAll("_", " ") },
                    ),
                  })}
                </Text>
                {drawing.revision_label ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("drawingsBoq.revision", {
                      revision: drawing.revision_label,
                    })}
                  </Text>
                ) : null}
                {drawing.error_message ? (
                  <Text style={[styles.error, isUrdu && styles.rtlText]}>
                    {drawing.error_message}
                  </Text>
                ) : null}
                {audits[drawing.id] ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("drawingsBoq.auditSummary", {
                      defaultValue:
                        "Readiness score: {{score}} · {{issues}} issues · {{missing}} without material",
                      score: Number(audits[drawing.id].overall_score).toFixed(0),
                      issues: audits[drawing.id].issues.length,
                      missing: audits[drawing.id].missing_material_count,
                    })}
                  </Text>
                ) : null}
                <View style={[styles.row, isUrdu && styles.rtlRow]}>
                  {drawing.format === "IFC" && drawing.status === "PARSED" ? (
                    <Action
                      title={t("drawingsBoq.viewAudit", { defaultValue: "Readiness" })}
                      secondary
                      isUrdu={isUrdu}
                      onPress={() => void handleShowAudit(drawing)}
                    />
                  ) : null}
                  {drawing.format === "PDF" && canCreateItem ? (
                    <Action
                      title={t("drawingsBoq.suggestItems", { defaultValue: "Suggest items" })}
                      secondary
                      isUrdu={isUrdu}
                      onPress={() => void handleSuggestItems(drawing)}
                    />
                  ) : null}
                  {canUpload ? (
                    <Action
                      title={t("drawingsBoq.revise", { defaultValue: "Revise" })}
                      secondary
                      isUrdu={isUrdu}
                      onPress={() => void handleReviseDrawing(drawing)}
                    />
                  ) : null}
                  {canDeleteDrawing ? (
                    <Action
                      title={t("drawingsBoq.delete", { defaultValue: "Delete" })}
                      secondary
                      isUrdu={isUrdu}
                      onPress={() => handleDeleteDrawing(drawing)}
                    />
                  ) : null}
                </View>
              </View>
            ))}
            <Pagination
              page={drawingsPage}
              pages={drawingsPages}
              isUrdu={isUrdu}
              onPrevious={() =>
                setDrawingsPage((page) => Math.max(1, page - 1))
              }
              onNext={() =>
                setDrawingsPage((page) => Math.min(drawingsPages, page + 1))
              }
            />
          </>
        )}

        <Text style={[styles.section, isUrdu && styles.rtlText]}>
          {t("drawingsBoq.billOfQuantities")}
        </Text>

        <View style={[styles.row, isUrdu && styles.rtlRow]}>
          {canRun ? (
            <Action
              title={t("drawingsBoq.runCalculation", { defaultValue: "Run calculation" })}
              isUrdu={isUrdu}
              onPress={() =>
                router.push({
                  pathname: "/projects/[projectId]/calculation",
                  params: { projectId: project.id },
                })
              }
            />
          ) : null}
          <Action
            title={t("drawingsBoq.reviewIssues", { defaultValue: "Review issues" })}
            secondary
            isUrdu={isUrdu}
            onPress={() =>
              router.push({
                pathname: "/projects/[projectId]/review-issues",
                params: { projectId: project.id },
              })
            }
          />
        </View>

        {boqError && !expandedVersion ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {boqError}
          </Text>
        ) : null}

        <Text style={[styles.label, isUrdu && styles.rtlText]}>
          {t("drawingsBoq.newVersionLabel")}
        </Text>
        <TextInput
          style={[styles.input, isUrdu && styles.rtlText]}
          value={versionLabel}
          onChangeText={setVersionLabel}
          placeholder={t("drawingsBoq.versionPlaceholder")}
          textAlign={isUrdu ? "right" : "left"}
        />
        <Action
          title={t("drawingsBoq.createVersion")}
          isUrdu={isUrdu}
          onPress={() => void handleCreateVersion()}
        />

        {!boqError && versions.length === 0 ? (
          <View style={styles.card}>
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("drawingsBoq.noVersions")}
            </Text>
          </View>
        ) : (
          <>
            {visibleVersions.map((version) => (
              <View key={version.id} style={styles.listCard}>
                <Pressable
                  onPress={() => void toggleVersion(version)}
                  accessibilityRole="button"
                >
                  <View style={[styles.versionHeading, isUrdu && styles.rtlRow]}>
                    <View style={styles.versionCopy}>
                      <Text style={[styles.itemTitle, isUrdu && styles.rtlText]}>
                        {version.label}
                      </Text>
                      <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                        {t("drawingsBoq.versionOriginLifecycle", {
                          defaultValue: "{{origin}} · {{lifecycle}}",
                          origin: t(
                            `drawingsBoq.origin.${version.origin.toLowerCase()}`,
                            { defaultValue: version.origin },
                          ),
                          lifecycle: t(
                            `drawingsBoq.lifecycle.${version.lifecycle.toLowerCase()}`,
                            { defaultValue: version.lifecycle.replaceAll("_", " ") },
                          ),
                        })}
                      </Text>
                      <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                        {t("drawingsBoq.versionStatusDate", {
                          status: t(
                            `drawingsBoq.status.${version.status.toLowerCase()}`,
                            {
                              defaultValue: version.status.replaceAll("_", " "),
                            },
                          ),
                          date: formatDate(
                            version.created_at,
                            locale,
                            t("drawingsBoq.notSet"),
                          ),
                        })}
                      </Text>
                    </View>
                    <Text style={[styles.link, isUrdu && styles.rtlText]}>
                      {expandedVersion === version.id
                        ? t("drawingsBoq.hide")
                        : t("drawingsBoq.view")}
                    </Text>
                  </View>
                </Pressable>

                {expandedVersion === version.id ? (
                  <View style={styles.versionDetails}>
                    {boqLoading ? (
                      <ActivityIndicator color={COLORS.navy} />
                    ) : null}
                    {boqError ? (
                      <Text style={[styles.error, isUrdu && styles.rtlText]}>
                        {boqError}
                      </Text>
                    ) : null}

                    {boqSummary ? (
                      <View style={styles.summaryBox}>
                        <InfoRow
                          label={t("drawingsBoq.items")}
                          value={String(boqSummary.item_count)}
                          isUrdu={isUrdu}
                        />
                        <InfoRow
                          label={t("drawingsBoq.total")}
                          value={formatMoney(
                            boqSummary.grand_total,
                            locale,
                            t("drawingsBoq.notAvailable"),
                          )}
                          isUrdu={isUrdu}
                        />
                        <InfoRow
                          label={t("drawingsBoq.awaitingApproval")}
                          value={String(boqSummary.unapproved_item_count)}
                          isUrdu={isUrdu}
                        />
                        <InfoRow
                          label={t("drawingsBoq.unpricedItems")}
                          value={String(boqSummary.unpriced_item_count)}
                          isUrdu={isUrdu}
                        />
                      </View>
                    ) : null}

                    {!locked && (canCreateItem || canUpdateItem) && (
                      <>
                        <Text style={[styles.label, isUrdu && styles.rtlText]}>
                          {editingItemId
                            ? t("drawingsBoq.editBOQItem")
                            : t("drawingsBoq.addCustomBOQItem")}
                        </Text>
                        <Field
                          label={t("drawingsBoq.materialName")}
                          value={itemName}
                          onChangeText={setItemName}
                          isUrdu={isUrdu}
                        />
                        <Field
                          label={t("drawingsBoq.unit")}
                          value={itemUnit}
                          onChangeText={setItemUnit}
                          editable={!(editingItemId !== "" && editingIsModel)}
                          isUrdu={isUrdu}
                        />
                        <Field
                          label={t("drawingsBoq.quantity")}
                          value={itemQuantity}
                          onChangeText={setItemQuantity}
                          keyboardType="decimal-pad"
                          isUrdu={isUrdu}
                        />
                        <Field
                          label={t("drawingsBoq.category")}
                          value={itemCategory}
                          onChangeText={setItemCategory}
                          isUrdu={isUrdu}
                        />
                        <Field
                          label={t("drawingsBoq.unitRateOptional")}
                          value={itemRate}
                          onChangeText={setItemRate}
                          keyboardType="decimal-pad"
                          isUrdu={isUrdu}
                        />
                        {editingItemId !== "" && editingIsModel ? (
                          <Field
                            label={t("drawingsBoq.adjustmentReason", {
                              defaultValue: "Reason for quantity change",
                            })}
                            value={itemReason}
                            onChangeText={setItemReason}
                            isUrdu={isUrdu}
                          />
                        ) : null}

                        {editingItemId ? (
                          <View style={[styles.row, isUrdu && styles.rtlRow]}>
                            <Action
                              title={t("drawingsBoq.saveItem")}
                              isUrdu={isUrdu}
                              onPress={() => void handleSaveItem()}
                            />
                            <Action
                              title={t("drawingsBoq.cancel")}
                              secondary
                              isUrdu={isUrdu}
                              onPress={clearItemForm}
                            />
                          </View>
                        ) : canCreateItem ? (
                          <Action
                            title={t("drawingsBoq.addCustomItem")}
                            isUrdu={isUrdu}
                            onPress={() => void handleAddCustomItem()}
                          />
                        ) : null}
                      </>
                    )}

                    {!boqLoading && !boqError && boqItems.length === 0 ? (
                      <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                        {t("drawingsBoq.noItems")}
                      </Text>
                    ) : null}

                    {visibleItems.map((item) => (
                      <View key={item.id} style={styles.boqItem}>
                        <View
                          style={[
                            styles.versionHeading,
                            isUrdu && styles.rtlRow,
                          ]}
                        >
                          <Text
                            style={[styles.itemTitle, isUrdu && styles.rtlText]}
                          >
                            {item.material_name}
                          </Text>
                          <Text
                            style={
                              item.status === "APPROVED"
                                ? styles.approved
                                : styles.draft
                            }
                          >
                            {t(
                              `drawingsBoq.status.${item.status.toLowerCase()}`,
                              { defaultValue: item.status.replaceAll("_", " ") },
                            )}
                          </Text>
                        </View>
                        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                          {t("drawingsBoq.quantityAndUnit", {
                            quantity: item.quantity,
                            unit: item.unit,
                            category: item.category
                              ? ` · ${item.category}`
                              : "",
                          })}
                        </Text>
                        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                          {item.unit_rate === null
                            ? t("drawingsBoq.rateNotSet")
                            : t("drawingsBoq.ratePerUnit", {
                                rate: formatMoney(
                                  item.unit_rate,
                                  locale,
                                  t("drawingsBoq.notAvailable"),
                                ),
                                unit: item.unit,
                              })}
                        </Text>
                        {item.review_status && item.review_status !== "OK" ? (
                          <Text style={[styles.draft, isUrdu && styles.rtlText]}>
                            {t(
                              `drawingsBoq.review.${item.review_status.toLowerCase()}`,
                              { defaultValue: item.review_status.replaceAll("_", " ") },
                            )}
                          </Text>
                        ) : null}
                        <View style={[styles.row, isUrdu && styles.rtlRow]}>
                          {!locked && canUpdateItem && item.status !== "APPROVED" ? (
                            <Action
                              title={t("drawingsBoq.edit")}
                              secondary
                              isUrdu={isUrdu}
                              onPress={() => beginEditItem(item)}
                            />
                          ) : null}
                          {canApprove && !engineVersion && item.status !== "APPROVED" ? (
                            <Action
                              title={t("drawingsBoq.approve")}
                              isUrdu={isUrdu}
                              onPress={() => void handleApproveItem(item)}
                            />
                          ) : null}
                        </View>
                      </View>
                    ))}

                    {boqItems.length > 0 ? (
                      <Pagination
                        page={itemsPage}
                        pages={itemsPages}
                        isUrdu={isUrdu}
                        onPrevious={() =>
                          setItemsPage((page) => Math.max(1, page - 1))
                        }
                        onNext={() =>
                          setItemsPage((page) => Math.min(itemsPages, page + 1))
                        }
                      />
                    ) : null}
                  </View>
                ) : null}
              </View>
            ))}
            <Pagination
              page={versionsPage}
              pages={versionsPages}
              isUrdu={isUrdu}
              onPrevious={() =>
                setVersionsPage((page) => Math.max(1, page - 1))
              }
              onNext={() =>
                setVersionsPage((page) => Math.min(versionsPages, page + 1))
              }
            />
          </>
        )}

        {busy ? (
          <View style={styles.busy}>
            <ActivityIndicator color={COLORS.navy} />
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("drawingsBoq.working")}
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
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
      <Action
        title={t("drawingsBoq.previous")}
        secondary
        isUrdu={props.isUrdu}
        disabled={props.page <= 1}
        onPress={props.onPrevious}
      />
      <Text style={[styles.pageText, props.isUrdu && styles.rtlText]}>
        {t("drawingsBoq.pageOf", {
          page: props.page,
          pages: props.pages,
        })}
      </Text>
      <Action
        title={t("drawingsBoq.next")}
        secondary
        isUrdu={props.isUrdu}
        disabled={props.page >= props.pages}
        onPress={props.onNext}
      />
    </View>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  editable?: boolean;
  isUrdu: boolean;
}) {
  return (
    <>
      <Text style={[styles.fieldLabel, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <TextInput
        style={[styles.input, props.isUrdu && styles.rtlText]}
        value={props.value}
        onChangeText={props.onChangeText}
        editable={props.editable ?? true}
        keyboardType={props.keyboardType ?? "default"}
        textAlign={props.isUrdu ? "right" : "left"}
      />
    </>
  );
}

function InfoRow(props: {
  label: string;
  value: string;
  isUrdu: boolean;
}) {
  return (
    <View style={[styles.infoRow, props.isUrdu && styles.rtlRow]}>
      <Text style={[styles.infoLabel, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <Text style={[styles.infoValue, props.isUrdu && styles.rtlText]}>
        {props.value}
      </Text>
    </View>
  );
}

function Action(props: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  disabled?: boolean;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.action,
        props.secondary && styles.actionSecondary,
        props.disabled && styles.disabled,
      ]}
      onPress={props.onPress}
      disabled={props.disabled}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          props.secondary && styles.actionSecondaryText,
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
  green: "#287456",
  amber: "#9B641A",
};

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: COLORS.background },
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 38, gap: 10, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8 },
  headerCopy: { flex: 1 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 26, fontWeight: "800", marginTop: 10 },
  section: { color: COLORS.text, fontSize: 18, fontWeight: "800", marginTop: 18, marginBottom: 2 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 10, marginBottom: 4 },
  fieldLabel: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 10, marginBottom: 5 },
  input: { minHeight: 46, backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: COLORS.text },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 8 },
  listCard: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 6 },
  itemTitle: { flex: 1, color: COLORS.text, fontSize: 14, fontWeight: "800", marginRight: 8 },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 5, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginTop: 8, lineHeight: 19, fontSize: 13 },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  versionHeading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  versionCopy: { flex: 1 },
  versionDetails: { borderTopWidth: 1, borderTopColor: COLORS.border, marginTop: 14, paddingTop: 12 },
  summaryBox: { backgroundColor: COLORS.surfaceMuted, borderWidth: 1, borderColor: COLORS.border, borderRadius: 11, paddingHorizontal: 12, paddingTop: 4, marginBottom: 12 },
  boqItem: { borderTopWidth: 1, borderTopColor: COLORS.border, paddingVertical: 12 },
  approved: { color: COLORS.green, fontSize: 11, fontWeight: "800" },
  draft: { color: COLORS.amber, fontSize: 11, fontWeight: "800" },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 8, borderTopWidth: 1, borderTopColor: COLORS.border },
  infoLabel: { color: COLORS.muted, fontSize: 12, flex: 1 },
  infoValue: { color: COLORS.text, fontSize: 13, fontWeight: "700", flex: 1, textAlign: "right" },
  action: { minHeight: 44, flexGrow: 1, backgroundColor: COLORS.navy, borderWidth: 1, borderColor: COLORS.navy, borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 13, paddingVertical: 11, marginTop: 8 },
  actionSecondary: { backgroundColor: COLORS.surface, borderColor: COLORS.border },
  actionText: { color: COLORS.surface, fontWeight: "800", fontSize: 13, textAlign: "center" },
  actionSecondaryText: { color: COLORS.navy },
  disabled: { opacity: 0.5 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 8 },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", textAlign: "center" },
  busy: { alignItems: "center", padding: 18, gap: 8 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});
