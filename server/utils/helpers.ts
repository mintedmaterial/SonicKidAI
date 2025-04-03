/**
 * Utility functions for SonicKid AI
 */

/**
 * Sanitize a filename to be safe for the filesystem
 * @param filename Filename to sanitize
 * @returns Sanitized filename
 */
export function sanitizeFilename(filename: string): string {
  // Replace unsafe characters with underscores
  return filename
    .replace(/[/\\?%*:|"<>]/g, '_') // Replace unsafe characters
    .replace(/\s+/g, '-')           // Replace spaces with hyphens
    .toLowerCase();                  // Convert to lowercase
}

/**
 * Truncate Ethereum/Sonic address for display
 * @param address Full address to truncate
 * @returns Truncated address (e.g., 0x1234...5678)
 */
export function truncateAddress(address: string): string {
  if (!address || address === 'Unknown') return 'Unknown';
  
  // If address is shorter than 10 characters, just return it
  if (address.length < 10) return address;
  
  // Otherwise truncate with ellipsis
  return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
}