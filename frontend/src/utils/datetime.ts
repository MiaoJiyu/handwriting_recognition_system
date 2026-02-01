/**
 * DateTime utilities for consistent timezone handling across the frontend
 */

import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc.js';
import timezone from 'dayjs/plugin/timezone.js';
import relativeTime from 'dayjs/plugin/relativeTime.js';

// Load dayjs plugins for timezone support
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(relativeTime);

// Set default timezone to local browser timezone
const userTimezone = dayjs.tz.guess();

/**
 * Format date string from API to local timezone display
 * API returns ISO format with timezone (e.g., "2026-01-31T10:00:00Z" or "2026-01-31T10:00:00+08:00")
 * This function converts it to the user's local timezone for display
 *
 * @param dateString - ISO format datetime string from API
 * @returns Formatted date string in local timezone, or null if dateString is null/undefined
 */
export const formatDateToLocal = (dateString: string | null | undefined): string | null => {
  if (!dateString) return null;

  // Parse the date string and convert to user's local timezone
  return dayjs(dateString).tz(userTimezone).format('YYYY-MM-DD HH:mm:ss');
};

/**
 * Format date string with detailed local timezone display (includes date and time)
 *
 * @param dateString - ISO format datetime string from API
 * @returns Formatted date string with full details
 */
export const formatDateToLocalFull = (dateString: string | null | undefined): string | null => {
  if (!dateString) return null;

  return dayjs(dateString).tz(userTimezone).format('YYYY-MM-DD HH:mm:ss (Z)');
};

/**
 * Format date string for display in Chinese locale
 *
 * @param dateString - ISO format datetime string from API
 * @returns Formatted date string in Chinese locale, or null if dateString is null/undefined
 */
export const formatDateToLocalZh = (dateString: string | null | undefined): string | null => {
  if (!dateString) return null;

  return dayjs(dateString).tz(userTimezone).format('YYYY年MM月DD日 HH:mm:ss');
};

/**
 * Format date string to relative time (e.g., "3 days ago")
 *
 * @param dateString - ISO format datetime string from API
 * @returns Relative time string, or null if dateString is null/undefined
 */
export const formatRelativeTime = (dateString: string | null | undefined): string | null => {
  if (!dateString) return null;

  return dayjs(dateString).tz(userTimezone).fromNow();
};

/**
 * Calculate days until expiration
 * Returns negative number if already expired
 *
 * @param dateString - ISO format datetime string from API (UTC)
 * @returns Number of days until expiration (can be negative)
 */
export const getDaysUntilExpiration = (dateString: string): number => {
  // Parse as UTC first, then convert to local timezone for comparison
  const expiryDate = dayjs.utc(dateString);
  const now = dayjs().utc();

  // Calculate difference in days (using UTC times)
  return expiryDate.diff(now, 'days');
};

/**
 * Check if a date is expired
 *
 * @param dateString - ISO format datetime string from API
 * @returns True if the date is in the past, false otherwise
 */
export const isExpired = (dateString: string | null): boolean => {
  if (!dateString) return false;
  return getDaysUntilExpiration(dateString) < 0;
};

/**
 * Get current time in ISO format with UTC timezone
 * Useful for sending timestamps to API
 *
 * @returns Current datetime in ISO format (UTC)
 */
export const getCurrentTimeUTC = (): string => {
  return dayjs.utc().toISOString();
};

/**
 * Format date for display in operations timeline
 *
 * @param dateString - ISO format datetime string from API
 * @returns Formatted date string suitable for timeline display
 */
export const formatTimelineDate = (dateString: string | null | undefined): string | null => {
  if (!dateString) return null;

  return dayjs(dateString).tz(userTimezone).format('YYYY-MM-DD HH:mm');
};

export default {
  formatDateToLocal,
  formatDateToLocalFull,
  formatDateToLocalZh,
  formatRelativeTime,
  getDaysUntilExpiration,
  isExpired,
  getCurrentTimeUTC,
  formatTimelineDate
};
