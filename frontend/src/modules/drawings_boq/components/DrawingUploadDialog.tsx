import { useRef, useState } from "react";
import { Button, Icon, Modal } from "../../organizations/components/OrganizationUi";
import { useUploadDrawing } from "../hooks";
import { formatFileSize } from "../utils/drawings-boq.utils";

interface DrawingUploadDialogProps {
  projectId: string;
  onClose: () => void;
}

export function DrawingUploadDialog({ projectId, onClose }: DrawingUploadDialogProps) {
  const upload = useUploadDrawing(projectId);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const idempotencyKeyRef = useRef(crypto.randomUUID());
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setError(null);

    if (selected && !selected.name.toLowerCase().endsWith(".ifc")) {
      setError("Only .ifc files are supported right now — export IFC from Revit or your BIM tool.");
      setFile(null);
      return;
    }

    setFile(selected);
  }

  function submit() {
    if (!file) return;

    upload.mutate(
      { file, idempotencyKey: idempotencyKeyRef.current },
      { onSuccess: onClose, onError: () => setError("Upload failed. Check the file and try again.") },
    );
  }

  return (
    <Modal title="Upload drawing" description="Upload an IFC drawing to generate a draft bill of quantities." onClose={onClose}>
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center gap-2 rounded-[10px] border border-dashed border-[#d9ceb9] bg-white px-4 py-8 text-center transition hover:border-[#c39a38]"
        >
          <Icon name="download" size={20} className="text-[#a2957c]" />
          <span className="text-[12px] font-semibold text-[#332a21]">{file ? file.name : "Choose an IFC file"}</span>
          <span className="text-[10.5px] text-[#a2957c]">{file ? formatFileSize(file.size) : ".ifc files only, for now"}</span>
        </button>

        <input ref={inputRef} type="file" accept=".ifc" onChange={handleFileChange} className="hidden" />

        {error ? (
          <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">{error}</div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={upload.isPending}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!file || upload.isPending}>
            {upload.isPending ? "Uploading…" : "Upload & parse"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}