'use client';

import { useState, useCallback } from 'react';

interface RateLimitBlockedProps {
  message: string;
  resetInSeconds?: number;
  isServiceUnavailable?: boolean;
  onRetry?: () => void;
}

/**
 * Форматирует время сброса лимита в локальное время пользователя.
 * - Сегодня: "сегодня в 23:10"
 * - Другой день: "25 янв., 10:30"
 *
 * Округляет вверх до следующей минуты + добавляет буфер для компенсации
 * задержки сети между получением TTL на бэкенде и отображением на фронте.
 */
function formatResetTime(resetInSeconds: number): string {
  const NETWORK_BUFFER_SECONDS = 5; // Буфер на задержку сети
  const resetMs = Date.now() + (resetInSeconds + NETWORK_BUFFER_SECONDS) * 1000;

  // Округляем вверх до следующей целой минуты
  const resetDate = new Date(Math.ceil(resetMs / 60000) * 60000);
  const now = new Date();

  const isToday = resetDate.toDateString() === now.toDateString();

  const timeStr = resetDate.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  });

  if (isToday) {
    return `сегодня в ${timeStr}`;
  }

  const dateStr = resetDate.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
  });

  return `${dateStr}, ${timeStr}`;
}

export function RateLimitBlocked({
  message,
  resetInSeconds,
  isServiceUnavailable,
  onRetry
}: RateLimitBlockedProps) {
  const [checking, setChecking] = useState(false);

  const handleRetry = useCallback(async () => {
    if (!onRetry || checking) return;
    setChecking(true);
    try {
      await onRetry();
    } finally {
      setChecking(false);
    }
  }, [onRetry, checking]);

  const borderColor = isServiceUnavailable
    ? 'border-red-500/40'
    : 'border-orange-500/40';
  const bgColor = isServiceUnavailable
    ? 'bg-red-500/10'
    : 'bg-orange-500/10';
  const textColor = isServiceUnavailable
    ? 'text-red-300'
    : 'text-orange-300';
  const iconColor = isServiceUnavailable
    ? 'text-red-400'
    : 'text-orange-400';

  return (
    <div className={`mx-3 mb-3 px-4 py-3 rounded-lg border ${borderColor} ${bgColor}`}>
      <div className="flex items-start gap-3">
        {isServiceUnavailable ? (
          // Иконка "сервер недоступен"
          <svg
            className={`w-5 h-5 flex-shrink-0 mt-0.5 ${iconColor}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
            />
          </svg>
        ) : (
          // Иконка "часы/лимит"
          <svg
            className={`w-5 h-5 flex-shrink-0 mt-0.5 ${iconColor}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )}
        <div className="flex-1">
          <p className={`text-sm ${textColor}`}>{message}</p>

          {/* Время сброса для rate limit (не для SERVICE_UNAVAILABLE) */}
          {resetInSeconds && resetInSeconds > 0 && !isServiceUnavailable && (
            <p className={`text-xs ${textColor} opacity-70 mt-1`}>
              Обновится {formatResetTime(resetInSeconds)}
            </p>
          )}

          {/* Кнопка проверки */}
          {onRetry && (
            <button
              onClick={handleRetry}
              disabled={checking}
              className={`mt-2 px-3 py-1 text-xs rounded border transition-colors
                ${isServiceUnavailable
                  ? 'border-red-500/40 text-red-300 hover:bg-red-500/20'
                  : 'border-orange-500/40 text-orange-300 hover:bg-orange-500/20'
                }
                disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {checking ? 'Проверяю...' : 'Проверить доступность'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
