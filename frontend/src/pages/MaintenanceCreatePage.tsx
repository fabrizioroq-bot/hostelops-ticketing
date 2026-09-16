import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Paper, Title, Stack, TextInput, Select, Textarea, Button, Group, Alert } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { useHostels } from "../hooks/useHostels";
import type { MaintenancePriority, MaintenanceTicket } from "../types";

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

export function MaintenanceCreatePage() {
  const navigate = useNavigate();
  const { hostels, loading: hostelsLoading } = useHostels();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [hostelId, setHostelId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<MaintenancePriority>("medium");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!hostelId || !title.trim() || !description.trim()) {
      setError("Please fill in all required fields.");
      return;
    }
    setSubmitting(true);
    try {
      const ticket = await api.post<MaintenanceTicket>("/maintenance-tickets", {
        hostel_id: hostelId, title: title.trim(), description: description.trim(), priority,
      });
      navigate(`/maintenance/${ticket.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the maintenance ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Paper withBorder p="xl" radius="md" maw={640}>
      <Title order={2} mb="md">Report a Maintenance Issue</Title>
      {error && <Alert color="red" icon={<IconAlertCircle size={16} />} mb="md">{error}</Alert>}
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Select
            label="Hostel / Property" required searchable
            data={hostels.map((h) => ({ value: h.id, label: h.name }))}
            value={hostelId} onChange={setHostelId} disabled={hostelsLoading}
          />
          <TextInput
            label="Title" required maxLength={200}
            value={title} onChange={(e) => setTitle(e.currentTarget.value)}
            placeholder="e.g. Leaking faucet in room 204"
          />
          <Textarea
            label="Description" required minRows={4} maxLength={2000}
            description={`${description.length}/2000 characters`}
            value={description} onChange={(e) => setDescription(e.currentTarget.value)}
          />
          <Select
            label="Priority" required data={PRIORITY_OPTIONS}
            value={priority} onChange={(v) => setPriority((v as MaintenancePriority) || "medium")}
          />
          <Group justify="flex-end">
            <Button variant="default" type="button" onClick={() => navigate(-1)}>Cancel</Button>
            <Button type="submit" loading={submitting}>Report Issue</Button>
          </Group>
        </Stack>
      </form>
    </Paper>
  );
}
