import { Paper, Text, Group, ThemeIcon } from "@mantine/core";
import type { Icon as TablerIconType } from "@tabler/icons-react";

export function StatCard({
  label, value, icon: Icon, color = "indigo",
}: {
  label: string;
  value: string | number;
  icon?: TablerIconType;
  color?: string;
}) {
  return (
    <Paper withBorder p="md" radius="md">
      <Group justify="space-between">
        <div>
          <Text c="dimmed" size="xs" tt="uppercase" fw={700}>{label}</Text>
          <Text fw={700} size="xl">{value}</Text>
        </div>
        {Icon && (
          <ThemeIcon color={color} variant="light" size={38} radius="md">
            <Icon size={22} />
          </ThemeIcon>
        )}
      </Group>
    </Paper>
  );
}
