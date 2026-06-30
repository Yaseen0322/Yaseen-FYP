import React from 'react';

function PaginationControls({ total, limit, offset, onPageChange, label = 'items' }) {
  if (!total || total <= limit) {
    return null;
  }

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const start = offset + 1;
  const end = Math.min(offset + limit, total);

  return (
    <div className="flex items-center justify-between gap-4 border-t border-slate-200 px-6 py-4">
      <p className="text-sm text-slate-500">
        Showing {start}-{end} of {total} {label}
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={offset === 0}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-700 disabled:cursor-not-allowed disabled:opacity-50 hover:bg-slate-50"
        >
          Previous
        </button>
        <span className="text-sm text-slate-600">
          Page {currentPage} of {totalPages}
        </span>
        <button
          onClick={() => onPageChange(offset + limit)}
          disabled={offset + limit >= total}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-700 disabled:cursor-not-allowed disabled:opacity-50 hover:bg-slate-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}

export default PaginationControls;
