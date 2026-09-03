/**
 * Deterministic formatting utilities for RecoverAI presentation layer.
 * Zero floating-point calculation: uses exact integer minor units (paise).
 */

export function formatPaise(minor: number, currency: string = "INR"): string {
  if (minor === 0) return "₹0.00";
  const sign = minor < 0 ? "-" : "";
  const absMinor = Math.abs(minor);

  const rupees = Math.floor(absMinor / 100);
  const paise = absMinor % 100;
  const paiseStr = paise < 10 ? `0${paise}` : `${paise}`;

  // Format integer part with Indian grouping (e.g. 53,11,619)
  const rupeesStr = formatIndianCurrency(rupees);

  if (currency === "INR") {
    return `${sign}₹${rupeesStr}.${paiseStr}`;
  }
  return `${sign}${currency} ${rupeesStr}.${paiseStr}`;
}

export function formatIndianCurrency(num: number): string {
  const str = num.toString();
  if (str.length <= 3) return str;

  const lastThree = str.substring(str.length - 3);
  const rest = str.substring(0, str.length - 3);

  // Group rest by pairs of 2 digits
  const formattedRest = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return `${formattedRest},${lastThree}`;
}

export function formatBps(bps: number): string {
  const pct = (bps / 100).toFixed(1);
  return `${pct}%`;
}

export function getStatusBadge(status: string): { label: string; bg: string; text: string; border: string } {
  switch (status.toUpperCase()) {
    case "SUCCEEDED":
    case "RECONCILED":
    case "APPROVED":
    case "PASSED":
    case "SUCCESS":
      return {
        label: status,
        bg: "bg-emerald-500/10",
        text: "text-emerald-400",
        border: "border-emerald-500/30",
      };

    case "BLOCKED":
    case "FAILED":
    case "UNRECOVERABLE":
    case "KILL_SWITCH_ACTIVE":
      return {
        label: status,
        bg: "bg-rose-500/10",
        text: "text-rose-400",
        border: "border-rose-500/30",
      };

    case "REQUIRES_REVIEW":
    case "HUMAN_REVIEW":
    case "ESCALATED":
      return {
        label: "REQUIRES REVIEW",
        bg: "bg-amber-500/10",
        text: "text-amber-400",
        border: "border-amber-500/30",
      };

    case "DEFERRED":
    case "RETRY_LATER":
      return {
        label: "DEFERRED (COOLDOWN)",
        bg: "bg-cyan-500/10",
        text: "text-cyan-400",
        border: "border-cyan-500/30",
      };

    case "UNKNOWN_PROVIDER_STATE":
      return {
        label: "UNKNOWN (PENDING)",
        bg: "bg-indigo-500/10",
        text: "text-indigo-400",
        border: "border-indigo-500/30",
      };

    default:
      return {
        label: status,
        bg: "bg-slate-500/10",
        text: "text-slate-400",
        border: "border-slate-500/30",
      };
  }
}

export function getActionLabel(action: string): string {
  switch (action) {
    case "RETRY_PAYMENT":
      return "Smart Retry Payment";
    case "RETRY_LATER":
      return "Cooldown Retry (Deferred)";
    case "REQUEST_PAYMENT_METHOD_UPDATE":
      return "Payment Method Update Link";
    case "SUBSCRIPTION_RECOVERY_WORKFLOW":
      return "Subscription Recovery Workflow";
    case "HUMAN_REVIEW":
      return "Escalate to Human Review";
    case "NO_ACTION":
      return "No Action (Safety Blocked)";
    default:
      return action;
  }
}
