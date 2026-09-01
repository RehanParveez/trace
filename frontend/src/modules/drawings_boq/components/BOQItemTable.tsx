import { useState } from "react";
import axios from "axios";
import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import { useApproveBOQItem, useBOQItems, useUpdateBOQItem } from "../hooks";
import type { BOQItem } from "../types/drawings-boq.types";
import { computeLineTotal, formatBOQItemStatus, formatBOQItemType, formatCurrency, formatQuantity } from "../utils/drawings-boq.utils";

interface BOQItemTableProps {
  boqVersionId: string;
  canUpdate: boolean;
  canApprove: boolean;
}

export function BOQItemTable({ boqVersionId, canUpdate, canApprove }: BOQItemTableProps) {
  const itemsQuery = useBOQItems(boqVersionId);
  const updateItem = useUpdateBOQItem(boqVersionId);
  const approveItem = useApproveBOQItem(boqVersionId);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const items = itemsQuery.data ?? [];

  function handleConflict() {
    setNotice("Someone else edited this item first. It's been refreshed with the latest version — review and try again.");
    void itemsQuery.refetch();
    setEditingId(null);
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="BILL OF QUANTITIES"
        title="BOQ items"
        description="Draft line items generated from the drawing. Approve only once quantities and rates are confirmed."
        action={<span className="rounded-full bg-[#efe6d3] px-2.5 py-1 font-mono text-[11px] font-semibold text-[#6b6152]">{items.length}</span>}
      />

      {notice ? (
        <div className="border-b border-[#cfe0f2] bg-[#e7f0fa] px-5 py-3 text-[11px] text-[#2c5c8f]">{notice}</div>
      ) : null}

      {items.length === 0 ? (
        <EmptyState icon="building" title="No BOQ items yet" description="Items appear here once a drawing has finished parsing." />
      ) : (
        <TableShell>
          <table className="w-full min-w-[800px] text-left">
            <thead className="bg-[#f5efe3]">
              <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                <th className="px-4 py-3">Material</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Unit</th>
                <th className="px-4 py-3 text-right">Quantity</th>
                <th className="px-4 py-3 text-right">Rate</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) =>
                editingId === item.id ? (
                  <BOQItemEditRow
                    key={item.id}
                    item={item}
                    isSaving={updateItem.isPending}
                    onCancel={() => setEditingId(null)}
                    onSave={(payload) =>
                      updateItem.mutate(
                        { itemId: item.id, payload: { ...payload, version: item.version } },
                        {
                          onSuccess: () => { setEditingId(null); setNotice(null); },
                          onError: (error) => {
                            if (axios.isAxiosError(error) && error.response?.status === 409) {
                              handleConflict();
                              return;
                            }
                            setNotice("Couldn't save this item. Please try again.");
                          },
                        },
                      )
                    }
                  />
                ) : (
                  <tr key={item.id} className="border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]">
                    <td className="px-4 py-3.5">
                      <span className="block text-[12px] font-semibold text-[#191410]">{item.material_name}</span>
                      {item.category ? <span className="mt-0.5 block text-[10px] text-[#756957]">{item.category}</span> : null}
                    </td>
                    <td className="px-4 py-3.5 text-[10.5px] text-[#6b6152]">{formatBOQItemType(item.item_type)}</td>
                    <td className="px-4 py-3.5 text-[11px] text-[#6b6152]">{item.unit}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[11px] text-[#191410]">{formatQuantity(item.quantity)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[11px] text-[#191410]">{formatCurrency(item.unit_rate)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[11px] font-semibold text-[#191410]">
                      {formatCurrency(computeLineTotal(item.quantity, item.unit_rate))}
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge tone={item.status === "APPROVED" ? "green" : "slate"}>{formatBOQItemStatus(item.status)}</Badge>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <div className="flex justify-end gap-2">
                        {canUpdate && item.status === "DRAFT" ? (
                          <Button variant="ghost" size="sm" onClick={() => setEditingId(item.id)}>
                            <Icon name="edit" size={12} />Edit
                          </Button>
                        ) : null}
                        {canApprove && item.status === "DRAFT" ? (
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={approveItem.isPending}
                            onClick={() => approveItem.mutate(item.id, { onError: () => setNotice("Couldn't approve this item. Please try again.") })}
                          >
                            Approve
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}

interface BOQItemEditRowProps {
  item: BOQItem;
  isSaving: boolean;
  onCancel: () => void;
  onSave: (payload: { material_name: string; category: string | null; unit: string; quantity: number; unit_rate: number | null }) => void;
}

function BOQItemEditRow({ item, isSaving, onCancel, onSave }: BOQItemEditRowProps) {
  const [materialName, setMaterialName] = useState(item.material_name);
  const [category, setCategory] = useState(item.category ?? "");
  const [unit, setUnit] = useState(item.unit);
  const [quantity, setQuantity] = useState(String(item.quantity));
  const [unitRate, setUnitRate] = useState(item.unit_rate !== null ? String(item.unit_rate) : "");

  const cls = "w-full rounded-[6px] border border-[#d9ceb9] bg-white px-2 py-1.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]";

  return (
    <tr className="border-t border-[#e1d5bc] bg-[#fffaf0]">
      <td className="px-4 py-3">
        <input className={cls} value={materialName} onChange={(e) => setMaterialName(e.target.value)} />
        <input className={`${cls} mt-1.5`} placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} />
      </td>
      <td className="px-4 py-3 text-[10.5px] text-[#a2957c]">{formatBOQItemType(item.item_type)}</td>
      <td className="px-4 py-3"><input className={cls} value={unit} onChange={(e) => setUnit(e.target.value)} /></td>
      <td className="px-4 py-3"><input className={`${cls} text-right`} type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></td>
      <td className="px-4 py-3"><input className={`${cls} text-right`} type="number" step="any" placeholder="—" value={unitRate} onChange={(e) => setUnitRate(e.target.value)} /></td>
      <td className="px-4 py-3 text-right font-mono text-[11px] text-[#a2957c]">—</td>
      <td className="px-4 py-3" />
      <td className="px-4 py-3">
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={isSaving}>Cancel</Button>
          <Button
            variant="primary"
            size="sm"
            disabled={isSaving || !materialName.trim() || !unit.trim() || quantity === ""}
            onClick={() =>
              onSave({
                material_name: materialName.trim(),
                category: category.trim() || null,
                unit: unit.trim(),
                quantity: Number(quantity),
                unit_rate: unitRate === "" ? null : Number(unitRate),
              })
            }
          >
            {isSaving ? "Saving…" : "Save"}
          </Button>
        </div>
      </td>
    </tr>
  );
}