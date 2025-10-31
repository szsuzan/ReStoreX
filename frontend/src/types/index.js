// Type definitions converted to JSDoc comments for better IDE support

/**
 * @typedef {Object} RecoveredFile
 * @property {string} id
 * @property {string} name
 * @property {string} type
 * @property {string} size
 * @property {number} sizeBytes
 * @property {string} dateModified
 * @property {string} path
 * @property {'High' | 'Average' | 'Low' | 'Unknown'} recoveryChance
 * @property {string} [thumbnail]
 * @property {boolean} isSelected
 * @property {number} [sector]
 * @property {number} [cluster]
 * @property {number} [inode]
 * @property {'found' | 'recovering' | 'recovered' | 'failed'} status
 */

/**
 * @typedef {Object} ScanResult
 * @property {string} name
 * @property {number} count
 * @property {string} icon
 * @property {boolean} [isExpanded]
 * @property {ScanResult[]} [children]
 */

/**
 * @typedef {Object} FilterOptions
 * @property {string} fileType
 * @property {string[]} recoveryChances
 * @property {'name' | 'size' | 'date' | 'recovery'} sortBy
 * @property {'asc' | 'desc'} sortOrder
 * @property {string} searchQuery
 */

/**
 * @typedef {Object} DriveInfo
 * @property {string} id
 * @property {string} name
 * @property {string} size
 * @property {string} fileSystem
 * @property {'healthy' | 'damaged' | 'scanning' | 'error'} status
 */

/**
 * @typedef {Object} ScanProgress
 * @property {boolean} isScanning
 * @property {number} progress
 * @property {number} currentSector
 * @property {number} totalSectors
 * @property {number} filesFound
 * @property {string} estimatedTimeRemaining
 */

/**
 * @typedef {Object} RecoveryProgress
 * @property {boolean} isRecovering
 * @property {number} progress
 * @property {string} currentFile
 * @property {number} filesRecovered
 * @property {number} totalFiles
 * @property {string} estimatedTimeRemaining
 */

export {};