// ABOUTME: Admin permission flags for the UI's edit/delete/rollback controls.
// ABOUTME: No auth backend exists yet — every flag is hardcoded true so the full admin UI is reachable.

export interface AdminPermissions {
  canEdit: boolean;
  canAdmin: boolean;
  canRollback: boolean;
  canEditPromptsAndProviders: boolean;
}

export const ADMIN_PERMISSIONS: AdminPermissions = {
  canEdit: true,
  canAdmin: true,
  canRollback: true,
  canEditPromptsAndProviders: true,
};
