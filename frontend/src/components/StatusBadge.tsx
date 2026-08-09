const statusClass: Record<string, string> = {
  approved: "success",
  pending: "pending",
  draft: "neutral",
  rejected: "error",
  suspended: "error",
};

export function StatusBadge({
  status,
  label,
}: {
  status: string;
  label: string;
}) {
  return (
    <span className={`status-badge ${statusClass[status] ?? "neutral"}`}>
      {label}
    </span>
  );
}
