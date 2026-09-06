export type PasswordChecks = {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  number: boolean;
  special: boolean;
  notCommon: boolean;
};

const COMMON_PASSWORDS = new Set([
  "password",
  "password123",
  "password123!",
  "admin123",
  "admin123!",
  "qwerty123",
  "12345678",
  "123456789",
  "1234567890",
]);

export function getPasswordChecks(password: string): PasswordChecks {
  const normalized = password.toLowerCase();

  return {
    length: password.length >= 12 && password.length <= 128,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /\d/.test(password),
    special: /[^\w\s]/.test(password),
    notCommon: password.length > 0 && !COMMON_PASSWORDS.has(normalized),
  };
}

export function isPasswordStrong(password: string): boolean {
  return Object.values(getPasswordChecks(password)).every(Boolean);
}