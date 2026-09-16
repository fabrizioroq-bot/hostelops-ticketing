import { Outlet, NavLink as RouterNavLink, useNavigate } from "react-router-dom";
import { AppShell, Burger, Group, NavLink, Text, Menu, Avatar, UnstyledButton, Divider } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconTicket, IconLayoutDashboard, IconUsers, IconBuildingSkyscraper,
  IconUserSearch, IconFileExport, IconLogout, IconChevronDown, IconTool,
} from "@tabler/icons-react";
import { useAuth } from "../hooks/useAuth";

export function AppLayout() {
  const [opened, { toggle }] = useDisclosure();
  const { profile, signOut } = useAuth();
  const navigate = useNavigate();

  const isMaintenanceRole = profile?.role === "maintenance";
  const canSeeExecutive = profile?.role === "admin" || profile?.role === "supervisor";
  const canSeeDataQuality = profile?.role === "admin";
  const canManageUsers = profile?.role === "admin";
  const canDedup = profile?.role === "admin" || profile?.role === "supervisor";
  const canExport = profile?.role === "admin" || profile?.role === "supervisor";
  const canSeeMaintenance = profile?.role === "admin" || profile?.role === "supervisor" || isMaintenanceRole;

  const handleLogout = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 260, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Text fw={700} size="lg">HostelOps Ticketing</Text>
          </Group>
          <Menu shadow="md" width={200}>
            <Menu.Target>
              <UnstyledButton>
                <Group gap={8}>
                  <Avatar radius="xl" size="sm">{profile?.full_name?.[0] ?? "?"}</Avatar>
                  <Text size="sm">{profile?.full_name}</Text>
                  <IconChevronDown size={14} />
                </Group>
              </UnstyledButton>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>{profile?.role.toUpperCase()}</Menu.Label>
              <Menu.Item leftSection={<IconLogout size={16} />} onClick={handleLogout}>
                Log out
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        {isMaintenanceRole ? (
          // Maintenance-role users get an isolated experience: only the
          // Maintenance module, nothing from the guest-ticketing system.
          <NavLink component={RouterNavLink} to="/maintenance" label="Maintenance" leftSection={<IconTool size={18} />} />
        ) : (
          <>
            <NavLink component={RouterNavLink} to="/dashboard/agent" label="My Dashboard" leftSection={<IconLayoutDashboard size={18} />} />
            {canSeeExecutive && (
              <NavLink component={RouterNavLink} to="/dashboard/executive" label="Executive Dashboard" leftSection={<IconLayoutDashboard size={18} />} />
            )}
            {canSeeExecutive && (
              <NavLink component={RouterNavLink} to="/dashboard/hostel-performance" label="Hostel Performance" leftSection={<IconBuildingSkyscraper size={18} />} />
            )}
            {canSeeDataQuality && (
              <NavLink component={RouterNavLink} to="/dashboard/data-quality" label="Data Quality" leftSection={<IconUserSearch size={18} />} />
            )}
            <NavLink component={RouterNavLink} to="/tickets" label="Tickets" leftSection={<IconTicket size={18} />} />
            <NavLink component={RouterNavLink} to="/guests" label="Guests" leftSection={<IconUsers size={18} />} />
            {canDedup && (
              <NavLink component={RouterNavLink} to="/dedup" label="Deduplication Review" leftSection={<IconUserSearch size={18} />} />
            )}
            <NavLink component={RouterNavLink} to="/hostels" label="Hostels" leftSection={<IconBuildingSkyscraper size={18} />} />
            {canManageUsers && (
              <NavLink component={RouterNavLink} to="/users" label="Users" leftSection={<IconUsers size={18} />} />
            )}
            {canExport && (
              <NavLink component={RouterNavLink} to="/exports" label="Exports" leftSection={<IconFileExport size={18} />} />
            )}
            {canSeeMaintenance && (
              <>
                <Divider my="sm" label="Separate module" labelPosition="center" />
                <NavLink component={RouterNavLink} to="/maintenance" label="Maintenance" leftSection={<IconTool size={18} />} />
              </>
            )}
          </>
        )}
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
