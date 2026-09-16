import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Paper, Title, Stack, TextInput, Select, Textarea, Button, Group, Alert,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { useHostels } from "../hooks/useHostels";
import { CHANNEL_LABEL, REASON_LABEL } from "../lib/labels";
import type { Ticket, TicketChannel, TicketPriority, TicketReason } from "../types";

const CHANNEL_OPTIONS = Object.entries(CHANNEL_LABEL).map(([value, label]) => ({ value, label }));
const REASON_OPTIONS = Object.entries(REASON_LABEL).map(([value, label]) => ({ value, label }));
const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

export function TicketCreatePage() {
  const navigate = useNavigate();
  const { hostels, loading: hostelsLoading } = useHostels();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [guestName, setGuestName] = useState("");
  const [reservationNumber, setReservationNumber] = useState("");
  const [hostelId, setHostelId] = useState<string | null>(null);
  const [channel, setChannel] = useState<TicketChannel | null>(null);
  const [reason, setReason] = useState<TicketReason | null>(null);
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [description, setDescription] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!hostelId || !channel || !reason || !guestName.trim() || !description.trim()) {
      setError("Please fill in all required fields.");
      return;
    }

    setSubmitting(true);
    try {
      const ticket = await api.post<Ticket>("/tickets", {
        guest_name: guestName.trim(),
        reservation_number: reservationNumber.trim() || null,
        hostel_id: hostelId,
        channel,
        reason,
        priority,
        description: description.trim(),
      });
      navigate(`/tickets/${ticket.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Paper withBorder p="xl" radius="md" maw={640}>
      <Title order={2} mb="md">New Ticket</Title>
      {error && (
        <Alert color="red" icon={<IconAlertCircle size={16} />} mb="md">
          {error}
        </Alert>
      )}
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <TextInput
            label="Reservation Number or Guest Name"
            description="Enter the guest's full name; reservation number is optional but improves guest matching."
            required
            value={guestName}
            onChange={(e) => setGuestName(e.currentTarget.value)}
            placeholder="e.g. Lucas Fernandez"
          />
          <TextInput
            label="Reservation Number"
            value={reservationNumber}
            onChange={(e) => setReservationNumber(e.currentTarget.value)}
            placeholder="e.g. RES-2026-0123"
          />
          <Select
            label="Hostel / Property"
            required
            data={hostels.map((h) => ({ value: h.id, label: h.name }))}
            value={hostelId}
            onChange={setHostelId}
            disabled={hostelsLoading}
            searchable
          />
          <Select
            label="Channel"
            required
            data={CHANNEL_OPTIONS}
            value={channel}
            onChange={(v) => setChannel(v as TicketChannel)}
          />
          <Select
            label="Reason"
            required
            data={REASON_OPTIONS}
            value={reason}
            onChange={(v) => setReason(v as TicketReason)}
          />
          <Select
            label="Priority"
            required
            data={PRIORITY_OPTIONS}
            value={priority}
            onChange={(v) => setPriority((v as TicketPriority) || "medium")}
          />
          <Textarea
            label="Brief Description"
            required
            minRows={3}
            maxLength={500}
            description={`${description.length}/500 characters`}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => navigate(-1)} type="button">
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Create Ticket
            </Button>
          </Group>
        </Stack>
      </form>
    </Paper>
  );
}
