// All inventory, accounts, runs, and results now come from the backend.
export function formatDate(value) {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  }).format(new Date(value)).replace('am', 'AM').replace('pm', 'PM');
}
