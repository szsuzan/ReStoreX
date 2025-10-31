import React from 'react';
import { CheckCircle, Info, AlertTriangle, X } from 'lucide-react';

/**
 * Simple notification box component for displaying messages
 * @param {Object} props
 * @param {string} props.type - Type of notification: 'success', 'info', 'warning', 'error'
 * @param {string} props.title - Title of the notification
 * @param {string} props.message - Message content
 * @param {Function} props.onClose - Callback when close is clicked
 */
export function NotificationBox({ type = 'info', title, message, onClose }) {
  const typeStyles = {
    success: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: 'text-green-600',
      title: 'text-green-900',
      message: 'text-green-700',
      IconComponent: CheckCircle
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-600',
      title: 'text-blue-900',
      message: 'text-blue-700',
      IconComponent: Info
    },
    warning: {
      bg: 'bg-orange-50',
      border: 'border-orange-200',
      icon: 'text-orange-600',
      title: 'text-orange-900',
      message: 'text-orange-700',
      IconComponent: AlertTriangle
    },
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: 'text-red-600',
      title: 'text-red-900',
      message: 'text-red-700',
      IconComponent: AlertTriangle
    }
  };

  const style = typeStyles[type] || typeStyles.info;
  const IconComponent = style.IconComponent;

  return (
    <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 animate-slide-down">
      <div className={`${style.bg} ${style.border} border-2 rounded-lg shadow-lg max-w-md w-full`}>
        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <IconComponent className={`w-6 h-6 ${style.icon}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className={`text-sm font-semibold ${style.title} mb-1`}>
                {title}
              </h3>
              <p className={`text-sm ${style.message} whitespace-pre-line`}>
                {message}
              </p>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
