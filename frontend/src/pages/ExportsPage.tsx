import { useState } from "react";
import { Title, Paper, Stack, Group, Button, Select, MultiSelect, Text, SegmentedControl } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDownload } from "@tabler/icons-react";
import { downloadFile } from "../lib/apiClient";
import { useHostels } from "../hooks/useHostels";

const TICKET_COLUMNS = [
  "id", "reservation_number", "guest_name", "hostel_id", "channel", "reason",
  "priority", "description", "status", "assignee_id", "resolution_notes",
  "recontacted", "recontacted_notes", "created_at", "resolved_at",
];

const GUEST_COLUMNS = [
  "id", "full_name", "email", "phone", "total_tickets", "last_contact_at",
  "common_reasons", "preferred_channel", "linked_reservations", "data_quality_score",
];

export function ExportsPage() {
  const { hostels } = useHostels();
  const [dataset, setDataset] = useState<"tickets" | "guests">("tickets");
  const [format, setFormat] = useState<"csv" | "xlsx">("csv");
  const [columns, setColumns] = useState<string[]>([]);
  const [hostelId, setHostelId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const availableColumns = dataset === "tickets" ? TICKET_COLUMNS : GUEST_COLUMNS;

  const handleExport = async () => {
    setDownloading(true);
    try {
      const params = new URLSearchParams();
      params.set("fmt", format);
      if (columns.length) params.set("columns", columns.join(","));
      if (dataset === "tickets") {
        if (hostelId) params.set("hostel_id", hostelId);
        if (status) params.set("status", status);
      }
      await downloadFile(`/exports/${dataset}?${params.toString()}`, `${dataset}_export.${format}`);
      notifications.show({ title: "Export ready", message: "Your download has started.", color: "green" });
    } catch (err) {
      notifications.show({
        title: "Export failed",
        message: err instanceof Error ? err.message : "Unknown error",
        color: "red",
      });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Stack gap="md" maw={560}>
      <Title order={2}>Export Data</Title>
      <Paper withBorder p="md" radius="md">
        <Stack gap="md">
          <div>
            <Text size="sm" fw={500} mb={4}>Dataset</Text>
            <SegmentedControl
              value={dataset}
              onChange={(v) => { setDataset(v as "tickets" | "guests"); setColumns([]); }}
              data={[{ label: "Tickets", value: "tickets" }, { label: "Guest Master List", value: "guests" }]}
            />
          </div>
          <div>
            <Text size="sm" fw={500} mb={4}>Format</Text>
            <SegmentedControl
              value={format}
              onChange={(v) => setFormat(v as "csv" | "xlsx")}
              data={[{ label: "CSV", value: "csv" }, { label: "Excel (.xlsx)", value: "xlsx" }]}
            />
          </div>
          {dataset === "tickets" && (
            <Group grow>
              <Select label="Hostel filter" clearable data={hostels.map((h) => ({ value: h.id, label: h.name }))} value={hostelId} onChange={setHostelId} />
              <Select
                label="Status filter" clearable
                data={["open", "in_progress", "resolved", "closed"].map((v) => ({ value: v, label: v }))}
                value={status} onChange={setStatus}
              />
            </Group>
          )}
          <MultiSelect
            label="Columns to include"
            description="Leave empty to export all default columns"
            data={availableColumns}
            value={columns}
            onChange={setColumns}
          />
          <Group justify="flex-end">
            <Button leftSection={<IconDownload size={16} />} onClick={handleExport} loading={downloading}>
              Download {format.toUpperCase()}
            </Button>
          </Group>
          <Text size="xs" c="dimmed">
            Every export is recorded in the audit log with who exported what, when, and with which filters.
          </Text>
        </Stack>
      </Paper>
    </Stack>
  );
}
