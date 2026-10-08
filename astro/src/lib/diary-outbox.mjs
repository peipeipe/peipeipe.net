// Transactions resolve only after IndexedDB completion, before network I/O.
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

async function transaction(mode, action) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('records', mode);
    let request;
    tx.oncomplete = () => resolve(request?.result);
    tx.onabort = () => reject(tx.error || new Error('端末の保存データを処理できませんでした'));
    tx.onerror = () => reject(tx.error);
    try {
      request = action(tx.objectStore('records'));
    } catch (error) {
      // Do not commit the first write if a subsequent operation throws.
      tx.abort();
      reject(error);
    }
  });
}

export function localRecord(key, value) {
  if (arguments.length === 1) return transaction('readonly', store => store.get(key));
  return transaction('readwrite', store => value === null ? store.delete(key) : store.put(value, key));
}

export function listJobs() {
  return transaction('readonly', store => store.getAll(IDBKeyRange.bound('job:', 'job:\uffff')));
}

export function enqueueJob(job, emptyEditor) {
  return transaction('readwrite', store => {
    store.put(job, `job:${job.payload.id}`);
    store.put(emptyEditor, 'editor');
  });
}
