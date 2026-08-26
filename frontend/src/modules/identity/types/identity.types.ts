export type Permission = {
  id: string;
  key: string;
  description: string | null;
};

export type Role = {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Permission[];
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
};

export type User = {
  id: string;
  organization_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  role: Role;
  organization: Organization;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type LoginResponse = {
  user: User;
  tokens: TokenResponse;
};

export type CurrentUserResponse = {
  user: User;
};

export type MessageResponse = {
  message: string;
};

export type RegistrationResponse = {
  user: User;
  message: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  password_confirmation: string;
  first_name: string;
  last_name: string;
  organization_name: string;
};

export type ForgotPasswordPayload = {
  email: string;
};

export type ResetPasswordPayload = {
  token: string;
  password: string;
  password_confirmation: string;
};

export type VerifyEmailPayload = {
  token: string;
};

export type ResendVerificationPayload = {
  email: string;
};

export type ChangePasswordPayload = {
  current_password: string;
  new_password: string;
  new_password_confirmation: string;
};

export type ApiError = {
  detail?: string;
  message?: string;
  code?: string;
};