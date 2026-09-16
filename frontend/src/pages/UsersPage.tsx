import { useEffect, useState } from "react";
import {
  Title, Paper, Table, Badge, Stack, Group, Button, Modal, TextInput, Select,
  MultiSelect, PasswordInput, Text, ActionIcon,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconUserOff } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { useHostels } from "../hooks/useHostels";
import type { AppUser, UserRole } from "../types";

const ROLE_OPTIONS = [
  { value: "admin", label: "Admin" },
  { value: "supervisor", label: "Supervisor" },
  { value: "agent", label: "Agent" },
];

function generateTempPassword(): string {
  return `Hostel${Math.random().toString(36).slice(2, 8)}!${Math.floor(Math.random() * 100)}`;
}

export function UsersPage() {
  const { hostels } = useHostels();
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, { open, close }] = useDisclosure(false);
  const [saving, setSaving] = useState(false);

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("agent");
  const [hostelIds, setHostelIds] = useState<string[]>([]);
  const [tempPassword, setTempPassword] = useState(generateTempPassword());

  const load = () => {
    setLoading(true);
    api.get<AppUser[]>("/users").then(setUsers).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await api.post("/users", {
        email, full_name: fullName, role, hostel_ids: hostelIds, temporary_password: tempPassword,
      });
      notifications.show({
        title: "User created",
        message: `${fullName} can log in with the temporary password shown — share it securely.`,
        color: "green",
      });
      close();
      setEmail(""); setFullName(""); setRole("agent"); setHostelIds([]); setTempPassword(generateTempPassword());
      load();
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (userId: string) => {
    await api.post(`/users/${userId}/deactivate`);
    notifications.show({ title: "User deactivated", message: "Access has been revoked.", color: "gray" });
    load();
  };

  const hostelName = (id: string) => hostels.find((h) => h.id === id)?.name ?? id;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Users</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={open}>Add User</Button>
      </Group>

      <Paper withBorder radius="md">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Email</Table.Th>
              <Table.Th>Role</Table.Th>
              <Table.Th>Hostels</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((u) => (
              <Table.Tr key={u.id}>
                <Table.Td>{u.full_name}</Table.Td>
                <Table.Td>{u.email}</Table.Td>
                <Table.Td><Badge variant="light">{u.role}</Badge></Table.Td>
                <Table.Td><Text size="xs">{u.hostel_ids.map(hostelName).join(", ") || "—"}</Text></Table.Td>
                <Table.Td><Badge color={u.is_active ? "green" : "gray"}>{u.is_active ? "Active" : "Deactivated"}</Badge></Table.Td>
                <Table.Td>
                  {u.is_active && (
                    <ActionIcon variant="subtle" color="red" onClick={() => handleDeactivate(u.id)} title="Deactivate">
                      <IconUserOff size={16} />
                    </ActionIcon>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
            {!loading && users.length === 0 && (
              <Table.Tr><Table.Td colSpan={6}><Text c="dimmed" ta="center" py="md">No users yet.</Text></Table.Td></Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal opened={opened} onClose={close} title="Add User" size="md">
        <Stack gap="sm">
          <TextInput label="Full Name" required value={fullName} onChange={(e) => setFullName(e.currentTarget.value)} />
          <TextInput label="Email" type="email" required value={email} onChange={(e) => setEmail(e.currentTarget.value)} />
          <Select label="Role" data={ROLE_OPTIONS} value={role} onChange={(v) => setRole((v as UserRole) || "agent")} />
          <MultiSelect
            label="Assigned Hostel(s)"
            description="Which hostel(s) this user works at (defines their access scope)"
            data={hostels.map((h) => ({ value: h.id, label: h.name }))}
            value={hostelIds}
            onChange={setHostelIds}
            searchable
          />
          <PasswordInput
            label="Temporary Password"
            description="Share this with the user through a secure channel — they should change it on first login."
            value={tempPassword}
            onChange={(e) => setTempPassword(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button onClick={handleCreate} loading={saving} disabled={!email || !fullName}>Create User</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
