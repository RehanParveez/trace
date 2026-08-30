from app.modules.identity.enums import PermissionKey

DRAWINGS_BOQ_PERMISSIONS = {
  PermissionKey.DRAWING_READ: "View drawings and parsed BOQ data.",
  PermissionKey.DRAWING_CREATE: "Upload drawings for BIM/IFC ingestion.",
  PermissionKey.DRAWING_DELETE: "Delete uploaded drawings.",
  PermissionKey.BOQ_UPDATE: "Edit draft BOQ items.",
  PermissionKey.BOQ_APPROVE: "Approve BOQ items for export.",
  PermissionKey.MATERIAL_LIBRARY_MANAGE: "Manage the organization's material library.",
}