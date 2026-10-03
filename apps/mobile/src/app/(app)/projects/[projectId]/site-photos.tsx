import { useCallback, useState } from "react";
import {ActivityIndicator, FlatList, Image, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Stack, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import {addPhotoTag, getSitePhoto, listSitePhotos, removePhotoTag, updateSitePhoto, uploadSitePhoto,
} from "../../../../api/sitePhotos";
import type { AuthUser, PhotoTag, SitePhoto } from "../../../../api/types";
import { restoreSession } from "../../../../api/client";
import * as ImagePicker from "expo-image-picker";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";

const PAGE_SIZE = 5;

function hasPermission(user: AuthUser | null, key: string): boolean {
  const permissions = user?.role?.permissions ?? [];
  return permissions.some((permission) => permission.key === key);
}

export default function ProjectSitePhotosScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const params = useLocalSearchParams<{ projectId?: string | string[] }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [photos, setPhotos] = useState<SitePhoto[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SitePhoto | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const canManage = hasPermission(user, "site_photo.manage");
  const canRead = hasPermission(user, "site_photo.read");

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;

      async function restore() {
        try {
          const restoredUser = await restoreSession();
          if (!cancelled) {
            setUser(restoredUser);
            setAuthLoading(false);
          }
        } catch {
          if (!cancelled) {
            setUser(null);
            setAuthLoading(false);
          }
        }
      }

      void restore();

      return () => {
        cancelled = true;
      };
    }, []),
  );

  const load = useCallback(
    async (isRefresh = false, requestedPage = page) => {
      if (!projectId || !canRead) return;

      if (isRefresh) setRefreshing(true);
      else setLoading(true);

      setError(null);

      try {
        const data = await listSitePhotos({
          project_id: projectId,
          skip: (requestedPage - 1) * PAGE_SIZE,
          limit: PAGE_SIZE,
        });
        setPhotos(data);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("sitePhotos.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, canRead, page, t],
  );

  useFocusEffect(
    useCallback(() => {
      if (!authLoading && canRead) void load();
    }, [authLoading, canRead, load]),
  );

  async function openDetail(photo: SitePhoto) {
    setSelected(photo);
    setDetailLoading(true);

    try {
      const fresh = await getSitePhoto(photo.id);
      setSelected(fresh);
    } catch {
    } finally {
      setDetailLoading(false);
    }
  }

  async function onImageError(photo: SitePhoto) {
    try {
      const fresh = await getSitePhoto(photo.id);
      setPhotos((previous) =>
        previous.map((current) => (current.id === photo.id ? fresh : current)),
      );

      setSelected((current) =>
        current?.id === photo.id ? fresh : current,
      );
    } catch {
    }
  }

  async function handleUploadPhoto() {
    if (!projectId || uploading) return;

    setUploadError(null);

    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: false,
        quality: 0.85,
      });

      if (result.canceled || !result.assets?.length) return;

      const asset = result.assets[0];
      const mimeType = asset.mimeType ?? "";

      if (!["image/jpeg", "image/png", "image/webp"].includes(mimeType)) {
        setUploadError(t("sitePhotos.uploadTypeError"));
        return;
      }

      if (asset.fileSize && asset.fileSize > 10 * 1024 * 1024) {
        setUploadError(t("sitePhotos.uploadSizeError"));
        return;
      }

      setUploading(true);

      await uploadSitePhoto(projectId, {
        uri: asset.uri,
        fileName: asset.fileName,
        mimeType: asset.mimeType,
      });

      setPage(1);
      await load(true, 1);
    } catch (err) {
      setUploadError(
        err instanceof Error
          ? err.message
          : t("sitePhotos.uploadFailure"),
      );
    } finally {
      setUploading(false);
    }
  }

  async function goToPage(nextPage: number) {
    if (nextPage < 1 || nextPage === page) return;
    setPage(nextPage);
    await load(false, nextPage);
  }

  async function refreshPhotos() {
    setPage(1);
    await load(true, 1);
  }

  if (authLoading) {
    return (
      <View style={styles.centered}>
        <View style={styles.headerRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.centered}>
        <View style={styles.headerRow}>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.title, isUrdu && styles.rtlText]}>
          {t("sitePhotos.title")}
        </Text>
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("sitePhotos.accessDenied")}
        </Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: t("sitePhotos.title") }} />

      <View style={styles.screen}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, styles.headerTitle, isUrdu && styles.rtlText]}>
            {t("sitePhotos.title")}
          </Text>
          <LanguageSwitcher />
        </View>

        {canManage ? (
          <Pressable
            style={[styles.button, uploading && styles.disabled]}
            onPress={() => void handleUploadPhoto()}
            disabled={uploading}
            accessibilityRole="button"
          >
            <Text style={styles.buttonText}>
              {uploading
                ? t("sitePhotos.uploading")
                : t("sitePhotos.uploadPhoto")}
            </Text>
          </Pressable>
        ) : null}

        {uploadError ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {uploadError}
          </Text>
        ) : null}

        {loading ? (
          <View style={styles.loadingArea}>
            <ActivityIndicator size="large" color={COLORS.navy} />
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("sitePhotos.loading")}
            </Text>
          </View>
        ) : error ? (
          <View style={styles.errorArea}>
            <Text style={[styles.error, isUrdu && styles.rtlText]}>
              {error}
            </Text>
            <Pressable
              style={styles.button}
              onPress={() => void load()}
              accessibilityRole="button"
            >
              <Text style={styles.buttonText}>{t("sitePhotos.retry")}</Text>
            </Pressable>
          </View>
        ) : (
          <FlatList
            data={photos}
            keyExtractor={(item) => item.id}
            contentContainerStyle={
              photos.length === 0 ? styles.emptyList : styles.list
            }
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={() => void refreshPhotos()}
                tintColor={COLORS.navy}
              />
            }
            ListEmptyComponent={
              <Text style={[styles.empty, isUrdu && styles.rtlText]}>
                {t("sitePhotos.empty")}
              </Text>
            }
            ListFooterComponent={
              photos.length > 0 ? (
                <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
                  <Pressable
                    style={[
                      styles.pageButton,
                      page <= 1 && styles.disabled,
                    ]}
                    onPress={() => void goToPage(page - 1)}
                    disabled={page <= 1}
                    accessibilityRole="button"
                  >
                    <Text
                      style={[
                        styles.pageButtonText,
                        isUrdu && styles.rtlText,
                      ]}
                    >
                      {t("sitePhotos.previous")}
                    </Text>
                  </Pressable>
                  <Text style={[styles.pageLabel, isUrdu && styles.rtlText]}>
                    {t("sitePhotos.page", { page })}
                  </Text>
                  <Pressable
                    style={[
                      styles.pageButton,
                      photos.length < PAGE_SIZE && styles.disabled,
                    ]}
                    onPress={() => void goToPage(page + 1)}
                    disabled={photos.length < PAGE_SIZE}
                    accessibilityRole="button"
                  >
                    <Text
                      style={[
                        styles.pageButtonText,
                        isUrdu && styles.rtlText,
                      ]}
                    >
                      {t("sitePhotos.next")}
                    </Text>
                  </Pressable>
                </View>
              ) : null
            }
            renderItem={({ item }) => (
              <Pressable
                style={styles.card}
                onPress={() => void openDetail(item)}
                accessibilityRole="button"
              >
                <Image
                  source={{ uri: item.photo_url }}
                  style={styles.thumb}
                  onError={() => void onImageError(item)}
                />

                <View style={styles.cardBody}>
                  <Text style={[styles.meta, isUrdu && styles.rtlText]}>
                    {item.photo_date ?? item.created_at.slice(0, 10)}
                  </Text>

                  {item.location_text ? (
                    <Text
                      numberOfLines={1}
                      style={[styles.bodyText, isUrdu && styles.rtlText]}
                    >
                      {item.location_text}
                    </Text>
                  ) : null}

                  {item.caption_raw ? (
                    <Text
                      numberOfLines={2}
                      style={[styles.caption, isUrdu && styles.rtlText]}
                    >
                      {item.caption_raw}
                    </Text>
                  ) : null}

                  {item.sender_phone_number ? (
                    <Text style={[styles.meta, isUrdu && styles.rtlText]}>
                      {t("sitePhotos.fromSender", {
                        sender: item.sender_phone_number,
                      })}
                    </Text>
                  ) : null}

                  <View style={[styles.tagRow, isUrdu && styles.rtlRow]}>
                    {item.tags.map((tag: PhotoTag) => (
                      <View key={tag.id} style={styles.tag}>
                        <Text style={styles.tagText}>{tag.tag}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              </Pressable>
            )}
          />
        )}
      </View>

      <PhotoDetailModal
        photo={selected}
        loading={detailLoading}
        canManage={canManage}
        isUrdu={isUrdu}
        onClose={() => setSelected(null)}
        onUpdated={(updated) => {
          setSelected(updated);
          setPhotos((previous) =>
            previous.map((photo) =>
              photo.id === updated.id ? updated : photo,
            ),
          );
        }}
        onImageError={() => {
          if (selected) void onImageError(selected);
        }}
      />
    </>
  );
}

function PhotoDetailModal(props: {
  photo: SitePhoto | null;
  loading: boolean;
  canManage: boolean;
  isUrdu: boolean;
  onClose: () => void;
  onUpdated: (photo: SitePhoto) => void;
  onImageError: () => void;
}) {
  const { t } = useTranslation();
  const [location, setLocation] = useState("");
  const [photoDate, setPhotoDate] = useState("");
  const [newTag, setNewTag] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const photo = props.photo;

  useFocusEffect(
    useCallback(() => {
      if (photo) {
        setLocation(photo.location_text ?? "");
        setPhotoDate(photo.photo_date ?? "");
        setNewTag("");
        setError(null);
      }
    }, [photo?.id]),
  );

  if (!photo) return null;

  async function saveMeta() {
  if (!photo) return;
  const photoId = photo.id;

  setSaving(true);
  setError(null);

  try {
    const updated = await updateSitePhoto(photoId, {
      location_text: location.trim() || null,
      photo_date: photoDate.trim() || null,
    });
    props.onUpdated(updated);
  } catch (err) {
    setError(
      err instanceof Error ? err.message : t("sitePhotos.updateFailure"),
    );
  } finally {
    setSaving(false);
  }
}

  async function addTag() {
  if (!photo) return;
  const photoId = photo.id;
  const tagValue = newTag.trim();
  if (!tagValue) return;

  setSaving(true);
  setError(null);

  try {
    await addPhotoTag(photoId, tagValue);
    const fresh = await getSitePhoto(photoId);
    props.onUpdated(fresh);
    setNewTag("");
  } catch (err) {
    setError(
      err instanceof Error ? err.message : t("sitePhotos.addTagFailure"),
    );
  } finally {
    setSaving(false);
  }
}

  async function removeTag(tag: PhotoTag) {
  if (!photo) return;

  const photoId = photo.id;
  setSaving(true);
  setError(null);

  try {
    await removePhotoTag(photoId, tag.id);
    const fresh = await getSitePhoto(photoId);
    props.onUpdated(fresh);
  } catch (err) {
    setError(
      err instanceof Error ? err.message : t("sitePhotos.removeTagFailure"),
    );
  } finally {
    setSaving(false);
  }
}

  return (
    <Modal
      visible
      animationType="slide"
      onRequestClose={props.onClose}
    >
      <ScrollView
        style={styles.modal}
        contentContainerStyle={styles.modalContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[styles.modalHeader, props.isUrdu && styles.rtlRow]}>
          <Text style={[styles.modalTitle, props.isUrdu && styles.rtlText]}>
            {t("sitePhotos.photoDetails")}
          </Text>
          <LanguageSwitcher />
        </View>

        <Pressable
          onPress={props.onClose}
          style={styles.closeButton}
          accessibilityRole="button"
        >
          <Text style={styles.buttonText}>{t("sitePhotos.close")}</Text>
        </Pressable>

        {props.loading ? (
          <ActivityIndicator size="large" color={COLORS.navy} />
        ) : (
          <>
            <Image
              source={{ uri: photo.photo_url }}
              style={styles.fullImage}
              onError={props.onImageError}
            />

            <Text style={[styles.meta, props.isUrdu && styles.rtlText]}>
              {photo.sender_phone_number
                ? t("sitePhotos.fromSender", {
                    sender: photo.sender_phone_number,
                  })
                : t("sitePhotos.noSender")}
            </Text>

            {photo.caption_raw ? (
              <Text style={[styles.caption, props.isUrdu && styles.rtlText]}>
                {photo.caption_raw}
              </Text>
            ) : null}

            {props.canManage ? (
              <View style={styles.form}>
                <Text style={[styles.label, props.isUrdu && styles.rtlText]}>
                  {t("sitePhotos.location")}
                </Text>
                <TextInput
                  style={[styles.input, props.isUrdu && styles.rtlText]}
                  value={location}
                  onChangeText={setLocation}
                  placeholder={t("sitePhotos.location")}
                  textAlign={props.isUrdu ? "right" : "left"}
                />

                <Text style={[styles.label, props.isUrdu && styles.rtlText]}>
                  {t("sitePhotos.photoDate")}
                </Text>
                <TextInput
                  style={[styles.input, props.isUrdu && styles.rtlText]}
                  value={photoDate}
                  onChangeText={setPhotoDate}
                  placeholder="2025-01-15"
                  textAlign={props.isUrdu ? "right" : "left"}
                />

                <Pressable
                  style={[styles.button, saving && styles.disabled]}
                  onPress={() => void saveMeta()}
                  disabled={saving}
                  accessibilityRole="button"
                >
                  <Text style={styles.buttonText}>
                    {saving
                      ? t("sitePhotos.saving")
                      : t("sitePhotos.save")}
                  </Text>
                </Pressable>

                <Text style={[styles.label, props.isUrdu && styles.rtlText]}>
                  {t("sitePhotos.tags")}
                </Text>
                <View style={[styles.tagRow, props.isUrdu && styles.rtlRow]}>
                  {photo.tags.map((tag: PhotoTag) => (
                    <Pressable
                      key={tag.id}
                      style={styles.tag}
                      onPress={() => void removeTag(tag)}
                      disabled={saving}
                      accessibilityRole="button"
                    >
                      <Text style={styles.tagText}>{tag.tag} ×</Text>
                    </Pressable>
                  ))}
                </View>

                <View style={[styles.tagInputRow, props.isUrdu && styles.rtlRow]}>
                  <TextInput
                    style={[
                      styles.input,
                      styles.flexInput,
                      props.isUrdu && styles.rtlText,
                    ]}
                    value={newTag}
                    onChangeText={setNewTag}
                    placeholder={t("sitePhotos.newTag")}
                    textAlign={props.isUrdu ? "right" : "left"}
                  />
                  <Pressable
                    style={[styles.button, saving && styles.disabled]}
                    onPress={() => void addTag()}
                    disabled={saving}
                    accessibilityRole="button"
                  >
                    <Text style={styles.buttonText}>{t("sitePhotos.add")}</Text>
                  </Pressable>
                </View>
              </View>
            ) : (
              <View style={[styles.tagRow, props.isUrdu && styles.rtlRow]}>
                {photo.tags.map((tag: PhotoTag) => (
                  <View key={tag.id} style={styles.tag}>
                    <Text style={styles.tagText}>{tag.tag}</Text>
                  </View>
                ))}
              </View>
            )}

            {error ? (
              <Text style={[styles.error, props.isUrdu && styles.rtlText]}>
                {error}
              </Text>
            ) : null}
          </>
        )}
      </ScrollView>
    </Modal>
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
  tagBackground: "#F5EBD6",
  tagText: "#76581E",
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background, paddingHorizontal: 16, paddingTop: 12 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24, gap: 12, backgroundColor: COLORS.background },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10 },
  headerTitle: { flex: 1, marginTop: 0 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 24, fontWeight: "800" },
  list: { paddingBottom: 28 },
  emptyList: { flexGrow: 1, justifyContent: "center", paddingBottom: 28 },
  loadingArea: { flex: 1, alignItems: "center", justifyContent: "center", gap: 10 },
  errorArea: { flex: 1, alignItems: "center", justifyContent: "center", padding: 18 },
  card: { flexDirection: "row", backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, marginBottom: 12, overflow: "hidden" },
  thumb: { width: 96, height: 112, backgroundColor: COLORS.surfaceMuted },
  cardBody: { flex: 1, padding: 11 },
  bodyText: { color: COLORS.text, fontSize: 13, marginTop: 4 },
  meta: { fontSize: 12, color: COLORS.muted, marginBottom: 4 },
  caption: { fontSize: 13, color: COLORS.secondary, lineHeight: 19 },
  tagRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 7 },
  tag: { backgroundColor: COLORS.tagBackground, paddingHorizontal: 9, paddingVertical: 5, borderRadius: 99 },
  tagText: { fontSize: 12, color: COLORS.tagText, fontWeight: "700" },
  empty: { textAlign: "center", color: COLORS.muted, fontSize: 14, lineHeight: 21, padding: 20 },
  muted: { color: COLORS.muted, fontSize: 13, lineHeight: 20, textAlign: "center" },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginVertical: 8, lineHeight: 19 },
  button: { minHeight: 42, backgroundColor: COLORS.navy, paddingHorizontal: 15, paddingVertical: 10, borderRadius: 10, alignItems: "center", justifyContent: "center", marginTop: 7 },
  buttonText: { color: COLORS.surface, fontWeight: "800", fontSize: 13 },
  disabled: { opacity: 0.5 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, paddingVertical: 10 },
  pageButton: { minHeight: 40, justifyContent: "center", paddingHorizontal: 13, borderRadius: 10, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  pageButtonText: { color: COLORS.navy, fontSize: 12, fontWeight: "800" },
  pageLabel: { color: COLORS.secondary, fontSize: 12, fontWeight: "700" },
  modal: { flex: 1, backgroundColor: COLORS.background },
  modalContent: { padding: 18, paddingBottom: 36 },
  modalHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 8 },
  modalTitle: { color: COLORS.text, fontSize: 20, fontWeight: "800", flex: 1 },
  closeButton: { alignSelf: "flex-end", backgroundColor: COLORS.navy, paddingHorizontal: 14, paddingVertical: 9, borderRadius: 10, marginBottom: 10 },
  fullImage: { width: "100%", height: 280, backgroundColor: COLORS.surfaceMuted, borderRadius: 14 },
  form: { marginTop: 12 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 10, marginBottom: 5 },
  input: { minHeight: 44, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, paddingHorizontal: 11, paddingVertical: 9, backgroundColor: COLORS.surface, color: COLORS.text, fontSize: 14 },
  tagInputRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 8 },
  flexInput: { flex: 1 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});