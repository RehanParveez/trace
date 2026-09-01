from app.modules.identity.enums import PermissionKey

DRAWINGS_BOQ_PERMISSIONS = {
  PermissionKey.DRAWING_READ: "View drawings and parsed BOQ data.",
  PermissionKey.DRAWING_CREATE: "Upload drawings for BIM/IFC ingestion.",
  PermissionKey.DRAWING_DELETE: "Delete uploaded drawings.",
  PermissionKey.BOQ_UPDATE: "Edit draft BOQ items.",
  PermissionKey.BOQ_APPROVE: "Approve BOQ items for export.",
  PermissionKey.BOQ_ITEM_CREATE: "Add custom line items to a BOQ.",
  PermissionKey.BOQ_EXPORT: "Generate priced BOQ PDF/Excel exports.",
  PermissionKey.MATERIAL_LIBRARY_MANAGE: "Manage the organization's material library.",
  PermissionKey.LABOUR_RATE_MANAGE: "Manage the organization's labour rates.",
}