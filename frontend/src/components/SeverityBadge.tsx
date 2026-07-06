import { severityBadgeClass } from '@/utils/format';
import type { Severity } from '@/types';

export default function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`badge ${severityBadgeClass[severity]}`}>
      {severity.toUpperCase()}
    </span>
  );
}
