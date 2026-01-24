'use client';

import { RateLimitInfo } from '@/lib/types';

interface RateLimitWarningProps {
  info: RateLimitInfo;
}

function formatWindowDuration(seconds: number): string {
  const minutes = Math.ceil(seconds / 60);
  if (minutes === 1) return '1 минуту';
  if (minutes < 5) return `${minutes} минуты`;
  return `${minutes} минут`;
}

export function RateLimitWarning({ info }: RateLimitWarningProps) {
  const percent = info.ip.limit > 0
    ? Math.round((info.ip.used / info.ip.limit) * 100)
    : 0;

  return (
    <div className="mx-3 mb-2 px-3 py-2 rounded-lg border border-yellow-500/40 bg-yellow-500/10">
      <div className="flex items-center gap-2 text-yellow-300 text-sm">
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <span>
          Использовано {percent}% лимита. После достижения агент будет недоступен {formatWindowDuration(info.window_seconds)}
        </span>
      </div>
    </div>
  );
}
