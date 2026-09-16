import { useCallback, useEffect, useState } from "react";
import { Title, Paper, Stack, Text, Group, Button, Badge, Table } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconRefresh, IconCheck, IconX } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import type { MergeCandidate } from "../types";

export function DedupReviewPage() {
  const [candidates, setCandidates] = useState<MergeCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [actingOn, setActingOn] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    api.get<MergeCandidate[]>("/dedup/candidates?status=pending").then(setCandidates).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await api.post<{ new_candidates_found: number }>("/dedup/scan");
      notifications.show({
        title: "Scan complete",
        message: `${result.new_candidates_found} new duplicate candidate(s) found.`,
        color: "blue",
      });
      load();
    } finally {
      setScanning(false);
    }
  };

  const handleDecision = async (id: string, decision: "approve" | "reject") => {
    setActingOn(id);
    try {
      await api.post(`/dedup/candidates/${id}/${decision}`);
      notifications.show({
        title: decision === "approve" ? "Guests merged" : "Candidate rejected",
        message: decision === "approve"
          ? "The duplicate guest records have been merged into a single golden record."
          : "This pair will no longer be suggested for merging.",
        color: decision === "approve" ? "green" : "gray",
      });
      setCandidates((prev) => prev.filter((c) => c.id !== id));
    } finally {
      setActingOn(null);
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Guest Deduplication Review</Title>
          <Text c="dimmed" size="sm">
            Merges are manual-review-only — approving here is the only way two guest golden records
            get combined. Nothing merges automatically.
          </Text>
        </div>
        <Button leftSection={<IconRefresh size={16} />} onClick={handleScan} loading={scanning} variant="light">
          Scan for Duplicates
        </Button>
      </Group>

      <Paper withBorder radius="md">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Match Score</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Detected</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {candidates.map((c) => (
              <Table.Tr key={c.id}>
                <Table.Td><Badge color={c.match_score >= 95 ? "red" : "yellow"}>{c.match_score}%</Badge></Table.Td>
                <Table.Td>{c.match_reason}</Table.Td>
                <Table.Td>{new Date(c.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs" color="green" leftSection={<IconCheck size={14} />}
                      loading={actingOn === c.id} onClick={() => handleDecision(c.id, "approve")}
                    >
                      Approve Merge
                    </Button>
                    <Button
                      size="xs" variant="default" leftSection={<IconX size={14} />}
                      loading={actingOn === c.id} onClick={() => handleDecision(c.id, "reject")}
                    >
                      Reject
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {!loading && candidates.length === 0 && (
              <Table.Tr><Table.Td colSpan={4}><Text c="dimmed" ta="center" py="md">No pending duplicates. Run a scan to check for new ones.</Text></Table.Td></Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
