import React, { useState } from 'react';
import { ChevronDown, X, Filter, Calendar, BarChart3, Grid3X3, List, SortAsc, SortDesc } from 'lucide-react';

/**
 * @param {Object} props
 * @param {import('../types/index.js').FilterOptions} props.filterOptions
 * @param {(options: import('../types/index.js').FilterOptions) => void} props.onFilterChange
 * @param {number} props.fileCount
 * @param {string} props.totalSize
 * @param {'grid' | 'list'} props.viewMode
 * @param {(mode: 'grid' | 'list') => void} props.onViewModeChange
 */
export function FilterBar({ 
  filterOptions, 
  onFilterChange, 
  fileCount, 
  totalSize,
  viewMode,
  onViewModeChange 
}) {
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [showRecoveryFilter, setShowRecoveryFilter] = useState(false);

  const handleRemoveFileTypeFilter = () => {
    onFilterChange({
      ...filterOptions,
      fileType: '',
    });
  };

  const handleRecoveryChancesChange = (chances) => {
    onFilterChange({
      ...filterOptions,
      recoveryChances: chances,
    });
  };

  const handleSortChange = (sortBy) => {
    const newSortOrder = filterOptions.sortBy === sortBy && filterOptions.sortOrder === 'asc' ? 'desc' : 'asc';
    onFilterChange({
      ...filterOptions,
      sortBy: sortBy,
      sortOrder: newSortOrder,
    });
    setShowSortMenu(false);
  };

  const handleResetFilters = () => {
    onFilterChange({
      fileType: '',
      recoveryChances: ['High', 'Average', 'Low', 'Unknown'],
      sortBy: 'name',
      sortOrder: 'asc',
      searchQuery: '',
    });
  };

  const sortOptions = [
    { id: 'name', label: 'Name' },
    { id: 'size', label: 'Size' },
    { id: 'date', label: 'Date Modified' },
    { id: 'recovery', label: 'Recovery Chance' },
  ];

  return (
    <>
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {filterOptions.fileType || 'All Files'}
            </h1>
            <p className="text-sm text-gray-600">
              {fileCount.toLocaleString()} files • {totalSize}
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => onViewModeChange('grid')}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'grid' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-800'
              }`}
              title="Grid view"
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => onViewModeChange('list')}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'list' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-800'
              }`}
              title="List view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          {/* Show Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-700 font-medium">Filters:</span>
          </div>

          {/* File Type Filter Chip */}
          {filterOptions.fileType && (
            <div className="flex items-center gap-2 bg-blue-100 text-blue-800 px-3 py-1.5 rounded-full text-sm font-medium">
              <span>{filterOptions.fileType}</span>
              <button
                onClick={handleRemoveFileTypeFilter}
                className="hover:bg-blue-200 rounded-full p-0.5 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Recovery Chances Filter */}
          {filterOptions.recoveryChances.length < 4 && (
            <div className="flex items-center gap-2 bg-green-100 text-green-800 px-3 py-1.5 rounded-full text-sm font-medium">
              <span>{filterOptions.recoveryChances.length} recovery types</span>
              <button
                onClick={() => onFilterChange({
                  ...filterOptions,
                  recoveryChances: ['High', 'Average', 'Low', 'Unknown']
                })}
                className="hover:bg-green-200 rounded-full p-0.5 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Sort */}
          <div className="relative">
            <button 
              onClick={() => setShowSortMenu(!showSortMenu)}
              className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors px-3 py-1.5 hover:bg-gray-100 rounded-lg"
            >
              {filterOptions.sortOrder === 'asc' ? 
                <SortAsc className="w-4 h-4" /> : 
                <SortDesc className="w-4 h-4" />
              }
              Sort by {sortOptions.find(opt => opt.id === filterOptions.sortBy)?.label}
              <ChevronDown className="w-4 h-4" />
            </button>

            {showSortMenu && (
              <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-48">
                {sortOptions.map(option => (
                  <button
                    key={option.id}
                    onClick={() => handleSortChange(option.id)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 transition-colors first:rounded-t-lg last:rounded-b-lg ${
                      filterOptions.sortBy === option.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* File Size */}
          <button className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors px-3 py-1.5 hover:bg-gray-100 rounded-lg">
            <BarChart3 className="w-4 h-4" />
            File size
          </button>

          {/* Date Modified */}
          <button className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors px-3 py-1.5 hover:bg-gray-100 rounded-lg">
            <Calendar className="w-4 h-4" />
            Date modified
          </button>

          {/* Recovery Chances */}
          <button 
            onClick={() => setShowRecoveryFilter(!showRecoveryFilter)}
            className={`flex items-center gap-2 text-sm transition-colors px-3 py-1.5 hover:bg-gray-100 rounded-lg ${
              filterOptions.recoveryChances.length < 4 
                ? 'text-blue-600 hover:text-blue-700' 
                : 'text-gray-700 hover:text-gray-900'
            }`}
          >
            Recovery chances
            {filterOptions.recoveryChances.length < 4 && (
              <span className="ml-1 text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full">
                {filterOptions.recoveryChances.length}
              </span>
            )}
          </button>

          {/* Recovery Chances Dropdown */}
          {showRecoveryFilter && (
            <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-64 p-4">
              <h4 className="text-sm font-semibold text-gray-800 mb-3">Recovery Chances</h4>
              <div className="space-y-2">
                {['High', 'Average', 'Low', 'Unknown'].map(chance => (
                  <label key={chance} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filterOptions.recoveryChances.includes(chance)}
                      onChange={(e) => {
                        const newChances = e.target.checked
                          ? [...filterOptions.recoveryChances, chance]
                          : filterOptions.recoveryChances.filter(c => c !== chance);
                        handleRecoveryChancesChange(newChances);
                      }}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">{chance}</span>
                  </label>
                ))}
              </div>
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => handleRecoveryChancesChange(['High', 'Average', 'Low', 'Unknown'])}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  Select All
                </button>
                <button
                  onClick={() => handleRecoveryChancesChange([])}
                  className="text-xs text-gray-600 hover:text-gray-700"
                >
                  Clear All
                </button>
              </div>
            </div>
          )}

          {/* Reset All */}
          <button 
            onClick={handleResetFilters}
            className="text-sm text-blue-600 hover:text-blue-700 transition-colors ml-auto px-3 py-1.5 hover:bg-blue-50 rounded-lg"
          >
            Reset all
          </button>
        </div>
      </div>
    </>
  );
}