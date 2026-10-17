// Date/time alone is not recoverable work. Keep an empty record in IndexedDB
// so an older localStorage fallback cannot resurrect submitted content.
export function hasEditorWork(saved) {
  return Boolean(saved && (saved.text || saved.images?.length || saved.editing || saved.draft));
}

export function readEditorRecord(saved) {
  if (!saved || typeof saved.text !== 'string'
    || typeof saved.date !== 'string' || !/^(?:\d{4}-\d{2}-\d{2})?$/.test(saved.date)
    || typeof saved.time !== 'string' || !/^(?:(?:[01]\d|2[0-3]):[0-5]\d)?$/.test(saved.time)
    || (saved.images !== undefined && !Array.isArray(saved.images))) return null;
  return { date: saved.date, time: saved.time, text: saved.text,
    editing: saved.editing || null, draft: saved.draft || null,
    savedText: typeof saved.savedText === 'string' ? saved.savedText : '',
    images: saved.images || [] };
}

export function selectEditorRecord(primary, fallback) {
  // A valid empty primary record supersedes stale fallback content as well.
  const saved = readEditorRecord(primary) || readEditorRecord(fallback);
  return hasEditorWork(saved) ? saved : null;
}

export function editorTextBackup(snapshot) {
  const { images, ...text } = snapshot;
  return { version: 1, ...text };
}
