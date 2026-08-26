type PasswordChecks = {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  number: boolean;
  special: boolean;
  notCommon: boolean;
};

function getPasswordChecks(password: string): PasswordChecks {
  const commonPasswords = [
    "password",
    "password123",
    "12345678",
    "qwerty123",
    "letmein",
    "welcome",
    "admin123",
  ];

  return {
    length: password.length >= 12 && password.length <= 128,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
    notCommon:
      password.length > 0 &&
      !commonPasswords.includes(password.toLowerCase()),
  };
}

type PasswordStrengthProps = {
  password: string;
};

const checks = [
  ["length", "12–128 characters"],
  ["uppercase", "Uppercase letter"],
  ["lowercase", "Lowercase letter"],
  ["number", "Number"],
  ["special", "Special character"],
  ["notCommon", "Not a common password"],
] as const;

export function PasswordStrength({
  password,
}: PasswordStrengthProps) {
  const result = getPasswordChecks(password);

  const passed = Object.values(result).filter(Boolean).length;

  const percentage =
    password.length === 0
      ? 0
      : Math.round((passed / checks.length) * 100);

  return (
    <div className="rounded-[10px] border border-[#E1D5BC] bg-[#F8F3E9] p-3.5">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#6B6152]">
          Password strength
        </span>

        <span className="font-mono text-[10px] text-[#A2957C]">
          {passed}/{checks.length}
        </span>
      </div>

      <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-[#E6DCC9]">
        <div
          className="h-full rounded-full bg-[#D9A441] transition-all"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        {checks.map(([key, label]) => {
          const valid = result[key];

          return (
            <div
              key={key}
              className="flex items-center gap-2 text-[11px]"
            >
              <span
                className={[
                  "grid h-4 w-4 place-items-center rounded-full text-[9px] font-bold",
                  valid
                    ? "bg-[#D9A441] text-[#0D1424]"
                    : "border border-[#D8CDB9] text-transparent",
                ].join(" ")}
              >
                ✓
              </span>

              <span
                className={
                  valid
                    ? "text-[#332A21]"
                    : "text-[#A2957C]"
                }
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}