// Transactions resolve only after durable IndexedDB completion, before network I/O.
let database;
function open() {
  if (!database) database = new Promise((resolve, reject) => {
    const request = indexedDB.open('diary-outbox-v1', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('records');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => { database = null; reject(request.error); };
  });
  return database;
}
export async function localRecord(key, value) {
  const db = await open();
  const writing = arguments.length > 1;
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('records', writing ? 'readwrite' : 'readonly');
    const store = transaction.objectStore('records');
    const request = writing ? (value === null ? store.delete(key) : store.put(value, key)) : store.get(key);
    transaction.oncomplete = () => resolve(request.result);
    transaction.onabort = () => reject(transaction.error || new Error('端末に保存できませんでした'));
    transaction.onerror = () => reject(transaction.error);
  });
}
export async function listJobs() {
  const db = await open();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('records', 'readonly');
    const request = transaction.objectStore('records').getAll(IDBKeyRange.bound('job:', 'job:\uffff'));
    transaction.oncomplete = () => resolve(request.result);
    transaction.onabort = () => reject(transaction.error);
  });
}

export async function enqueueJob(job, emptyEditor) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('records', 'readwrite');
    const store = transaction.objectStore('records');
    store.put(job, `job:${job.payload.id}`);
    store.put(emptyEditor, 'editor');
    transaction.oncomplete = () => resolve();
    transaction.onabort = () => reject(transaction.error || new Error('投稿を端末に保存できませんでした'));
    transaction.onerror = () => reject(transaction.error);
  });
}
