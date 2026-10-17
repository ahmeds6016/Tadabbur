'use client';

import { forwardRef } from 'react';

/**
 * The one way the app tells a reader that something went wrong.
 * Pass messages from lib/errors.js, never raw error text.
 */
const ErrorNotice = forwardRef(function ErrorNotice(
  { message, actionLabel, onAction, compact = false, className = '', ...rest },
  ref,
) {
  if (!message) return null;
  return (
    <div
      ref={ref}
      role="alert"
      className={`error-notice${compact ? ' error-notice-compact' : ''}${className ? ` ${className}` : ''}`}
      {...rest}
    >
      <p className="error-notice-text">{message}</p>
      {actionLabel && onAction && (
        <button type="button" className="error-notice-action" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
});

export default ErrorNotice;
