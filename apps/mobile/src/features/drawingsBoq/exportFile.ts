import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import type { ExportFile } from "../../api/boqEngine";

export async function shareExportFile(file: ExportFile): Promise<void> {
  const target = new File(Paths.cache, file.filename);
  if (target.exists) target.delete();
  target.create();
  target.write(file.bytes);

  if (!(await Sharing.isAvailableAsync())) {
    throw new Error("Sharing is not available on this device.");
  }
  await Sharing.shareAsync(target.uri, {
    mimeType: file.mime,
    dialogTitle: file.filename,
  });
}